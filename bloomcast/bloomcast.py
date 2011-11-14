"""Driver module for SoG-bloomcast project
"""
from __future__ import absolute_import
from __future__ import division
# Standard library:
from datetime import date
from datetime import datetime
from datetime import timedelta
import logging
import logging.handlers
import os
import shutil
from subprocess import Popen
from subprocess import STDOUT
import sys
# NumPy:
import numpy as np
# Mako:
from mako.template import Template
# Bloomcast:
from meteo import MeteoProcessor
from rivers import RiversProcessor
from utils import Config
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
    def __init__(self, config_file):
        self.config = Config()
        self.config.load_config(config_file)


    def run(self):
        """Execute the bloomcast prediction and report its results.

        * Load the process configuration data.

        * Get the wind forcing data.

        * Get the meteorological and river flow forcing data.

        * Run the SOG code.

        * Calculate the spring diatom bloom date.
        """
        self._configure_logging()
        log.debug('run start date is {0:%Y-%m-%d}'
                  .format(self.config.run_start_date))
        try:
            self._get_forcing_data()
        except NoNewWindData:
            log.info('Wind data date {0:%Y-%m-%d} is unchanged since last run'
                     .format(self.config.data_date))
            return
        self._run_SOG()
        self._calc_bloom_date()
        self._render_results()


    def _render_results(self):
        """Render bloomcast results as HTML and write them to a file.
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
        if os.access(self.config.results_dir, os.F_OK):
            shutil.copy('bloomcast/html/results.html', self.config.results_dir)
            shutil.copy(
                'bloomcast/html/css/style.css',
                os.path.join(self.config.results_dir, 'css'))
            shutil.copy(
                'bloomcast/html/js/libs/modernizr-2.0.min.js',
                os.path.join(self.config.results_dir, 'js/libs'))


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
            self.config.data_date = None
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
            # Don't worry if there is no stored data date
            pass
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
                SOG = Popen('nice -19 ../SOG-code-ocean/SOG'.split(),
                            stdin=infile_obj, stdout=stdout_obj, stderr=STDOUT)
                SOG.wait()
        log.info(
            'SOG run finished at {0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))


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
        self.nitrate = SOG_Timeseries(self.config.std_bio_ts_outfile)
        self.nitrate.read_data('time', '3 m avg nitrate concentration')
        self.diatoms = SOG_Timeseries(self.config.std_bio_ts_outfile)
        self.diatoms.read_data('time', '3 m avg micro phytoplankton biomass')
        self._clip_results_to_jan1()
        self._reduce_results_to_daily()
        first_low_nitrate_days = self._find_low_nitrate_days(
            NITRATE_HALF_SATURATION_CONCENTRATION)
        self._find_phytoplankton_peak(
            first_low_nitrate_days, PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH)
        if self.config.data_date is not None:
            bloom_date_log.info('  {0}      {1}  {2}'
                                .format(self.config.data_date, self.bloom_date,
                                        self.bloom_biomass))


    def _clip_results_to_jan1(self):
        """Clip the nitrate concentration and diatom biomass results
        so that they start on 1-Jan of the bloom year.
        """
        jan1 = datetime(self.config.run_start_date.year + 1, 1, 1)
        discard_hours = (jan1 - self.config.run_start_date)
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
        year = self.config.run_start_date.year + 1
        day_slice = 86400 // self.config.SOG_timestep
        day_iterator = xrange(
            0, self.nitrate.dep_data.shape[0] - day_slice, day_slice)
        self.nitrate.dep_data = np.array(
            [self.nitrate.dep_data[i:i+day_slice].min() for i in day_iterator])
        self.nitrate.indep_data = np.array(
            [date.fromordinal(i+1).replace(year=year)
             for i in xrange(self.nitrate.dep_data.shape[0])])
        day_iterator = xrange(
            0, self.diatoms.dep_data.shape[0] - day_slice, day_slice)
        self.diatoms.dep_data = np.array(
            [self.diatoms.dep_data[i:i+day_slice].max() for i in day_iterator])
        self.diatoms.indep_data = np.array(
            [date.fromordinal(i+1).replace(year=year)
             for i in xrange(self.diatoms.dep_data.shape[0])])


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


if __name__ == '__main__':
    bloomcast = Bloomcast(sys.argv[1])
    bloomcast.run()
