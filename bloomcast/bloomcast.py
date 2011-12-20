"""Driver module for SoG-bloomcast project
"""
from __future__ import absolute_import
from __future__ import division
# Standard library:
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
import logging
import logging.handlers
from math import ceil
import os
from subprocess import Popen
from subprocess import STDOUT
import sys
# NumPy:
import numpy as np
# Mako:
from mako.template import Template
# Matplotlib:
from matplotlib.axes import Axes
from matplotlib.dates import date2num
from matplotlib.dates import DateFormatter
from matplotlib.dates import DayLocator
from matplotlib.dates import HourLocator
from matplotlib.dates import MonthLocator
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
# Bloomcast:
from meteo import MeteoProcessor
from rivers import RiversProcessor
from utils import Config
from utils import SOG_HoffmuellerProfile
from utils import SOG_Timeseries
from wind import WindProcessor


log = logging.getLogger('bloomcast')
bloom_date_log = logging.getLogger('bloomcast.bloom_date')


class NoNewWindData(Exception): pass


class Bloomcast(object):
    """Strait of Georgia spring diatom bloom predictor.

    :arg config_file: Path for the bloomcast configuration file.
    :type config_file: string
    """
    def __init__(self, config_file, data_date):
        self.config = Config()
        self.config.load_config(config_file)
        # Wind data date for development and debugging; overwritten if
        # wind forcing data is collected and processed
        self.config.data_date = data_date


    def run(self):
        """Execute the bloomcast prediction and report its results.

        * Load the process configuration data.

        * Get the wind forcing data.

        * Get the meteorological and river flow forcing data.

        * Run the SOG code.

        * Calculate the spring diatom bloom date.
        """
        self._configure_logging()
        log.debug('run start date/time is {0:%Y-%m-%d %H:%M:%S}'
                  .format(self.config.run_start_date))
        try:
            self._get_forcing_data()
        except NoNewWindData:
            log.info('Wind data date {0:%Y-%m-%d} is unchanged since last run'
                     .format(self.config.data_date))
            return
        self._run_SOG()
        self._get_results_timeseries()
        self._create_timeseries_graphs()
        self._get_results_profiles()
        self._create_profile_graphs()
        self._calc_bloom_date()
        self._render_results()
        self._push_results_to_web()


    def _configure_logging(self):
        """Configure logging of debug & warning messages to console
        and email.

        Debug logging on/off & email recipient(s) for warning messages
        are set in config file.
        """
        log.setLevel(logging.DEBUG)

        console = logging.StreamHandler()
        console.setFormatter(
            logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
        console.setLevel(logging.INFO)
        if self.config.logging.debug:
            console.setLevel(logging.DEBUG)
        log.addHandler(console)

        disk = logging.handlers.RotatingFileHandler(
            self.config.logging.bloomcast_log_filename, maxBytes=1024 * 1024)
        disk.setFormatter(
            logging.Formatter(
                '%(asctime)s %(levelname)s [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M'))
        disk.setLevel(logging.DEBUG)
        log.addHandler(disk)

        mailhost = (('localhost', 1025) if self.config.logging.use_test_smtpd
                    else 'localhost')
        email = logging.handlers.SMTPHandler(
            mailhost, fromaddr='SoG-bloomcast@eos.ubc.ca',
            toaddrs=self.config.logging.toaddrs,
            subject='Warning Message from SoG-bloomcast')
        email.setFormatter(
            logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
        email.setLevel(logging.WARNING)
        log.addHandler(email)

        bloom_date_evolution = logging.FileHandler(
            self.config.logging.bloom_date_log_filename)
        bloom_date_evolution.setFormatter(logging.Formatter('%(message)s'))
        bloom_date_evolution.setLevel(logging.INFO)
        bloom_date_log.addHandler(bloom_date_evolution)
        bloom_date_log.propagate = False


    def _get_forcing_data(self):
        """Collect and process forcing data.
        """
        if  not self.config.get_forcing_data:
            log.info('Skipped collection and processing of forcing data')
            return
        wind = WindProcessor(self.config)
        self.config.data_date = wind.make_forcing_data_file()
        log.info('based on wind data run data date is {0:%Y-%m-%d}'
                  .format(self.config.data_date))
        try:
            with open('wind_data_date', 'rt') as file_obj:
                last_data_date = datetime.strptime(
                    file_obj.readline().strip(), '%Y-%m-%d').date()
        except IOError:
            # Fake a wind data date to get things rolling
            last_data_date = self.config.run_start_date.date()
        if self.config.data_date == last_data_date:
            raise NoNewWindData
        else:
            with open('wind_data_date', 'wt') as file_obj:
                file_obj.write('{0:%Y-%m-%d}\n'.format(self.config.data_date))
        meteo = MeteoProcessor(self.config)
        meteo.make_forcing_data_files()
        rivers = RiversProcessor(self.config)
        rivers.make_forcing_data_files()


    def _run_SOG(self):
        """Run SOG.
        """
        if not self.config.run_SOG:
            log.info('Skipped running SOG')
            return
        log.info('SOG run started at {0:%Y-%m-%d %H:%M:%S}'
                 .format(datetime.now()))
        with open(self.config.infile, 'rt') as infile_obj:
            with open(self.config.infile + '.stdout', 'wt') as stdout_obj:
                SOG = Popen('nice -19 ../SOG-code-bloomcast/SOG'.split(),
                            stdin=infile_obj, stdout=stdout_obj, stderr=STDOUT)
                SOG.wait()
        log.info(
            'SOG run finished at {0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))


    def _get_results_timeseries(self):
        """Read SOG results time series of interest and create
        SOG_Timeseries objects from them.
        """
        self.nitrate = SOG_Timeseries(self.config.std_bio_ts_outfile)
        self.nitrate.read_data('time', '3 m avg nitrate concentration')
        self.nitrate.calc_mpl_dates(self.config.run_start_date)
        self.diatoms = SOG_Timeseries(self.config.std_bio_ts_outfile)
        self.diatoms.read_data('time', '3 m avg micro phytoplankton biomass')
        self.diatoms.calc_mpl_dates(self.config.run_start_date)
        self.temperature = SOG_Timeseries(self.config.std_phys_ts_outfile)
        self.temperature.read_data('time', '3 m avg temperature')
        self.temperature.calc_mpl_dates(self.config.run_start_date)
        self.salinity = SOG_Timeseries(self.config.std_phys_ts_outfile)
        self.salinity.read_data('time', '3 m avg salinity')
        self.salinity.calc_mpl_dates(self.config.run_start_date)
        self.mixing_layer_depth = SOG_Timeseries(
            self.config.std_phys_ts_outfile)
        self.mixing_layer_depth.read_data('time', 'mixing layer depth')
        self.mixing_layer_depth.calc_mpl_dates(self.config.run_start_date)


    def _create_timeseries_graphs(self):
        """Create time series graph objects.
        """
        self.fig_nitrate_diatoms_ts = self._two_axis_timeseries(
            self.nitrate, self.diatoms,
            titles=('3 m Avg Nitrate Concentration [uM N]',
                    '3 m Avg Diatom Biomass [uM N]'),
            colors=('#30b8b8', 'green'))
        self.fig_temperature_salinity_ts = self._two_axis_timeseries(
            self.temperature, self.salinity,
            titles=('3 m Avg Temperature [deg C]',
                   '3 m Avg Salinity [-]'),
            colors=('red', 'blue'))
        self.fig_mixing_layer_depth_ts = self._mixing_layer_depth_timeseries()


    def _two_axis_timeseries(self, left_ts, right_ts, titles, colors):
        """Create a time series graph figure object with 2 time series
        plotted on the left and right y axes.
        """
        fig = Figure((8, 3), facecolor='white')
        ax_left = fig.add_subplot(1, 1, 1)
        ax_left.set_position((0.125, 0.1, 0.775, 0.75))
        fig.ax_left = ax_left
        ax_right = ax_left.twinx()
        Axes(fig, ax_left.get_position(), sharex=ax_right)
        ax_left.plot(left_ts.mpl_dates, left_ts.dep_data, color=colors[0])
        ax_left.set_ylabel(titles[0], color=colors[0], size='x-small')
        ax_right.plot(right_ts.mpl_dates, right_ts.dep_data, color=colors[1])
        ax_right.set_ylabel(titles[1], color=colors[1], size='x-small')
        # Add line to mark switch from actual to averaged forcing data
        fig.data_date_line = ax_left.axvline(
            date2num(self.config.data_date), color='black')
        # Format x-axis
        ax_left.xaxis.set_major_locator(MonthLocator())
        ax_left.xaxis.set_major_formatter(DateFormatter('%j\n%b'))
        for axis in (ax_left, ax_right):
            for label in axis.get_xticklabels() + axis.get_yticklabels():
                label.set_size('x-small')
        ax_left.set_xlim(
            (int(left_ts.mpl_dates[0]), ceil(left_ts.mpl_dates[-1])))
        ax_left.set_xlabel(
            'Year-days in {0} and {1}'
            .format(self.config.run_start_date.year,
                    self.config.run_start_date.year + 1),
            size='x-small')
        return fig


    def _mixing_layer_depth_timeseries(self):
        """Create a time series graph figure object of the mixing
        layer depth on the wind data date and the 6 days preceding it.
        """
        fig = Figure((8, 3), facecolor='white')
        ax = fig.add_subplot(1, 1, 1)
        ax.set_position((0.125, 0.1, 0.775, 0.75))
        predicate = np.logical_and(
            self.mixing_layer_depth.mpl_dates
            > date2num(self.config.data_date - timedelta(days=6)),
            self.mixing_layer_depth.mpl_dates
            <= date2num(self.config.data_date + timedelta(days=1)))
        mpl_dates = self.mixing_layer_depth.mpl_dates[predicate]
        dep_data = self.mixing_layer_depth.dep_data[predicate]
        ax.plot(mpl_dates, dep_data, color='magenta')
        ax.set_ylabel('Mixing Layer Depth [m]', color='magenta', size='x-small')
        ax.xaxis.set_major_locator(DayLocator())
        ax.xaxis.set_major_formatter(DateFormatter('%j\n%d-%b'))
        ax.xaxis.set_minor_locator(HourLocator(interval=6))
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_size('x-small')
        ax.set_xlim((int(mpl_dates[0]), ceil(mpl_dates[-1])))
        return fig


    def _get_results_profiles(self):
        """Read SOG results profiles of interest and create
        SOG_HoffmuellerProfile objects from them.
        """
        profile_number = (
            self.config.data_date - self.config.run_start_date.date()).days
        self.nitrate_profile = SOG_HoffmuellerProfile(
            self.config.Hoffmueller_profiles_outfile)
        self.nitrate_profile.read_data('depth', 'nitrate', profile_number)
        self.diatoms_profile = SOG_HoffmuellerProfile(
            self.config.Hoffmueller_profiles_outfile)
        self.diatoms_profile.read_data(
            'depth', 'micro phytoplankton', profile_number)
        self.temperature_profile = SOG_HoffmuellerProfile(
            self.config.Hoffmueller_profiles_outfile)
        self.temperature_profile.read_data(
            'depth', 'temperature', profile_number)
        self.salinity_profile = SOG_HoffmuellerProfile(
            self.config.Hoffmueller_profiles_outfile)
        self.salinity_profile.read_data('depth', 'salinity', profile_number)


    def _create_profile_graphs(self):
        """Create profile graph objects.
        """
        profile_datetime = datetime.combine(self.config.data_date, time(12))
        profile_dt = profile_datetime - self.config.run_start_date
        profile_hour = profile_dt.days * 24 + profile_dt.seconds / 3600
        self.mixing_layer_depth.boolean_slice(
            self.mixing_layer_depth.indep_data >= profile_hour)
        mixing_layer_depth = self.mixing_layer_depth.dep_data[0]
        self.fig_temperature_salinity_profile = self._two_axis_profile(
            self.temperature_profile, self.salinity_profile, mixing_layer_depth,
            titles=('Temperature [deg C]', 'Salinity [-]'),
            colors=('red', 'blue'), limits=((4, 10), (20, 30)))
        self.fig_nitrate_diatoms_profile = self._two_axis_profile(
            self.nitrate_profile, self.diatoms_profile, mixing_layer_depth,
            titles=('Nitrate Concentration [uM N]', 'Diatom Biomass [uM N]'),
            colors=('#30b8b8', 'green'))


    def _two_axis_profile(self, top_profile, bottom_profile, mixing_layer_depth,
                          titles, colors, limits=None):
        """Create a profile graph figure object with 2 profiles
        plotted on the top and bottom x axes.
        """
        fig = Figure((4, 8), facecolor='white')
        ax_bottom = fig.add_subplot(1, 1, 1)
        ax_bottom.set_position((0.2, 0.1, 0.5, 0.8))
        fig.ax_bottom = ax_bottom
        ax_top = ax_bottom.twiny()
        Axes(fig, ax_bottom.get_position(), sharex=ax_top)
        ax_top.plot(
            top_profile.dep_data, top_profile.indep_data, color=colors[0])
        ax_top.set_xlabel(titles[0], color=colors[0], size='small')
        ax_bottom.plot(bottom_profile.dep_data, bottom_profile.indep_data,
                       color=colors[1])
        ax_bottom.set_xlabel(titles[1], color=colors[1], size='small')
        for axis in (ax_bottom, ax_top):
            for label in axis.get_xticklabels() + axis.get_yticklabels():
                label.set_size('x-small')
        if limits is not None:
            ax_top.set_xlim(limits[0])
            ax_bottom.set_xlim(limits[1])
        ax_bottom.axhline(mixing_layer_depth, color='black')
        ax_bottom.text(
            x=ax_bottom.get_xlim()[1]  + 0.05, y=mixing_layer_depth,
            s='Mixing Layer\nDepth = {0:.2f} m'.format(mixing_layer_depth),
            verticalalignment='center', size='small')
        ax_bottom.set_ylim(
            (bottom_profile.indep_data[-1], bottom_profile.indep_data[0]))
        ax_bottom.set_ylabel('Depth [m]', size='small')
        return fig


    def _calc_bloom_date(self):
        """Calculate the predicted spring bloom date.

        From Allen & Wolfe, in preparation:

        "Although the idea of a spring bloom is well-defined, the exact
        timing of a real spring bloom is not.  In C09 the peak of the
        bloom was defined as the highest concentration of phytoplankton
        unless an earlier bloom (more than 5 days earlier) was associated
        with nitrate going to zero.  J.Gower using satellite data chooses
        a measure of the start of the bloom as the time when the whole
        Strait of Georgia has high chlorophyll.  The nutritional quality
        of the phytoplankton appears to change when they become nutrient
        limited \citep{SastriDower2009}.  Thus here we use a definition
        that should delineate between nutrient replete spring conditions
        and nutrient stressed summer conditions.  We use the peak
        phytoplankton concentration (averaged from the surface to 3 m
        depth) within four days of the average 0-3~m nitrate concentration
        going below 0.5 uM (the half-saturation concentration) for two
        consecutive days."
        """
        NITRATE_HALF_SATURATION_CONCENTRATION = 0.5  # uM
        PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH = 4     # days
        self._clip_results_to_jan1()
        self._reduce_results_to_daily()
        first_low_nitrate_days = self._find_low_nitrate_days(
            NITRATE_HALF_SATURATION_CONCENTRATION)
        self._find_phytoplankton_peak(
            first_low_nitrate_days, PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH)
        if self.config.get_forcing_data or self.config.run_SOG:
            bloom_date_log.info('  {0}      {1}  {2}'
                                .format(self.config.data_date, self.bloom_date,
                                        self.bloom_biomass))


    def _clip_results_to_jan1(self):
        """Clip the nitrate concentration and diatom biomass results
        so that they start on 1-Jan of the bloom year.
        """
        jan1 = datetime(self.config.run_start_date.year + 1, 1, 1)
        discard_hours = jan1 - self.config.run_start_date
        discard_hours = discard_hours.days * 24 + discard_hours.seconds / 3600
        predicate = self.nitrate.indep_data >= discard_hours
        self.nitrate.boolean_slice(predicate)
        self.diatoms.boolean_slice(predicate)


    def _reduce_results_to_daily(self):
        """Reduce the nitrate concentration and diatom biomass results
        to daily values.

        Nitrate concentrations are daily minimum values.

        Diatom biomasses are daily maximum values.

        Independent data values are dates.
        """
        # Assume that there are an integral nummber of SOG time steps in a
        # day
        day_slice = 86400 // self.config.SOG_timestep
        day_iterator = xrange(
            0, self.nitrate.dep_data.shape[0] - day_slice, day_slice)
        jan1 = date(self.config.run_start_date.year + 1, 1, 1)
        self.nitrate.dep_data = np.array(
            [self.nitrate.dep_data[i:i+day_slice].min() for i in day_iterator])
        self.nitrate.indep_data = np.array(
            [jan1 + timedelta(days=i)
             for i in xrange(self.nitrate.dep_data.size)])
        day_iterator = xrange(
            0, self.diatoms.dep_data.shape[0] - day_slice, day_slice)
        self.diatoms.dep_data = np.array(
            [self.diatoms.dep_data[i:i+day_slice].max() for i in day_iterator])
        self.diatoms.indep_data = np.array(
            [jan1 + timedelta(days=i)
             for i in xrange(self.diatoms.dep_data.size)])


    def _find_low_nitrate_days(self, threshold):
        """Return the start and end dates of the first 2 day period in
        which the nitrate concentration is below the ``threshold``.
        """
        self.nitrate.boolean_slice(self.nitrate.dep_data <= threshold)
        log.debug('Dates on which nitrate was <= {0} uM N:\n{1}'
                  .format(threshold, self.nitrate.indep_data))
        log.debug('Nitrate <= {0} uM N:\n{1}'
                  .format(threshold, self.nitrate.dep_data))
        for i in xrange(self.nitrate.dep_data.shape[0]):
            low_nitrate_day_1 = self.nitrate.indep_data[i]
            days = self.nitrate.indep_data[i+1] - low_nitrate_day_1
            if days == timedelta(days=1):
                low_nitrate_day_2 = self.nitrate.indep_data[i+1]
                break
        return low_nitrate_day_1, low_nitrate_day_2


    def _find_phytoplankton_peak(self, first_low_nitrate_days, peak_half_width):
        """Return the date with ``peak_half_width`` of the
        ``first_low_nitrate_days`` on which the diatoms biomass is the
        greatest.
        """
        half_width_days = timedelta(days=peak_half_width)
        early_bloom_date = first_low_nitrate_days[0] - half_width_days
        late_bloom_date = first_low_nitrate_days[1] + half_width_days
        log.debug('Bloom window is between {0} and {1}'
                  .format(early_bloom_date, late_bloom_date))
        self.diatoms.boolean_slice(self.diatoms.indep_data >= early_bloom_date)
        self.diatoms.boolean_slice(self.diatoms.indep_data <= late_bloom_date)
        log.debug('Dates in bloom window:\n{0}'.format(self.diatoms.indep_data))
        log.debug('Micro phytoplankton biomass values in bloom window:\n{0}'
                  .format(self.diatoms.dep_data))
        bloom_date_index = self.diatoms.dep_data.argmax()
        self.bloom_date = self.diatoms.indep_data[bloom_date_index]
        self.bloom_biomass = self.diatoms.dep_data[bloom_date_index]
        log.info('Predicted bloom date is {0}'.format(self.bloom_date))
        log.debug(
            'Phytoplankton biomass on bloom date is {0} uM N'
            .format(self.bloom_biomass))


    def _render_results(self):
        """Render bloomcast results page and graphs to files.
        """
        template = Template(filename='bloomcast/html/results.mako')
        with open(
            self.config.logging.bloom_date_log_filename, 'rt') as file_obj:
            bloom_date_log = [line.split() for line in file_obj
                              if not line.startswith('#')]
        context = {
            'run_start_date': self.config.run_start_date,
            'data_date': self.config.data_date,
            'bloom_date': self.bloom_date,
            'bloom_date_log': bloom_date_log,
        }
        with open('bloomcast/html/results.html', 'wt') as file_obj:
            file_obj.write(template.render(**context))
        graphs = [
            (self.fig_nitrate_diatoms_profile, 'nitrate_diatoms_profiles.svg'),
            (self.fig_temperature_salinity_profile,
             'temperature_salinity_profiles.svg'),
            (self.fig_nitrate_diatoms_ts, 'nitrate_diatoms_timeseries.svg'),
            (self.fig_temperature_salinity_ts,
             'temperature_salinity_timeseries.svg'),
            (self.fig_mixing_layer_depth_ts,
             'mixing_layer_depth_timeseries.svg'),
        ]
        for fig, filename in graphs:
            try:
                bloom_date_line = fig.ax_left.axvline(
                    date2num(datetime.combine(self.bloom_date, time(12))),
                    color='green')
                fig.legend(
                    [fig.data_date_line, bloom_date_line],
                    ['Actual to Avg', 'Diatom Bloom'],
                    loc='upper right', prop={'size': 'xx-small'})
                for label in fig.ax_left.get_xticklabels():
                    label.set_size('x-small')
            except AttributeError:
                pass
            canvas = FigureCanvasAgg(fig)
            canvas.print_svg(os.path.join('bloomcast/html', filename))


    def _push_results_to_web(self):
        """Push results page, graphs, styles, etc. to web server directory
        via rsync.
        """
        if os.access(self.config.results_dir, os.F_OK):
            Popen(
                'rsync -rq --exclude=results.mako {0}/ {1}'
                .format(os.path.abspath('bloomcast/html'),
                        self.config.results_dir).split())


if __name__ == '__main__':
    config_file = sys.argv[1]
    try:
        data_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
    except ValueError:
        print 'Expected %Y-%m-%d for data date, got: {0[2]}'.format(sys.argv)
    except IndexError:
        data_date = None
    bloomcast = Bloomcast(config_file, data_date)
    bloomcast.run()
