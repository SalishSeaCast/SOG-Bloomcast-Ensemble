# Copyright 2011-2014 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SoG-bloomcast command plug-in to run an ensemble forecast to predict
the first spring diatom phytoplankon bloom in the Strait of Georgia.
"""
from collections import OrderedDict
import copy
import logging
import os

import arrow
import cliff.command
import numpy as np
import yaml

import SOGcommand
from . import (
    bloomcast,
    meteo,
    rivers,
    utils,
    visualization,
    wind,
)


__all__ = ['Ensemble']


# Colours for plots
COLORS = {
    'axes': '#ebebeb',     # bootswatch superhero theme text
    'bg': '#2B3E50',       # bootswatch superhero theme background
    'diatoms': '#7CC643',
    'nitrate': '#82AFDC',
    'temperature': '#D83F83',
    'salinity': '#82DCDC',
    'temperature_lines': {
        'early': '#F00C27',
        'median': '#D83F83',
        'late': '#BD9122',
    },
    'salinity_lines': {
        'early': '#0EB256',
        'median': '#82DCDC',
        'late': '#224EBD',
    },
    'mld': '#df691a',
    'wind_speed': '#ebebeb',
}


class Ensemble(cliff.command.Command):
    """run the ensemble bloomcast
    """
    log = logging.getLogger('bloomcast.ensemble')
    bloom_date_log = logging.getLogger('bloomcast.ensemble.bloom_date')

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.description = '''
            Run an ensemble forecast to predict  the first spring diatom
            phytoplanton bloom in the Strait of Georgia.
        '''
        parser.add_argument(
            'config_file',
            help='path and name of configuration file',
        )
        parser.add_argument(
            '--data-date',
            type=arrow.get,
            help='data date for development and debugging; overridden if '
                 'wind forcing data is collected and processed',
        )
        return parser

    def take_action(self, parsed_args):
        self.config = utils.Config()
        self.config.load_config(parsed_args.config_file)
        configure_logging(self.config, self.bloom_date_log)
        # Wind data date for development and debugging; overwritten if
        # wind forcing data is collected and processed
        self.config.data_date = parsed_args.data_date
        if not self.config.get_forcing_data and self.config.data_date is None:
            self.log.debug(
                'This will not end well: '
                'get_forcing_data={0.get_forcing_data} '
                'and data_date={0.data_date}'.format(self.config))
            return
        self.log.debug('run start date/time is {0:%Y-%m-%d %H:%M:%S}'
                       .format(self.config.run_start_date))
        # Check run start date and current date to ensure that
        # river flow data are available.
        # River flow data are only available in a rolling 18-month window.
        run_start_yr_jan1 = (
            arrow.get(self.config.run_start_date).replace(month=1, day=1))
        river_date_limit = arrow.now().replace(months=-18)
        if run_start_yr_jan1 < river_date_limit:
            self.log.error(
                'A bloomcast run starting {0.run_start_date:%Y-%m-%d} cannot '
                'be done today because there are no river flow data available '
                'prior to {1}'
                .format(self.config, river_date_limit.format('YYYY-MM-DD')))
            return
        try:
            get_forcing_data(self.config, self.log)
        except ValueError:
            self.log.info(
                'Wind data date {} is unchanged since last run'
                .format(self.config.data_date.format('YYYY-MM-DD')))
            return
        self._create_infile_edits()
        self._create_batch_description()
        self._run_SOG_batch()
        self._load_biology_timeseries()
        prediction, bloom_dates = self._calc_bloom_dates()
        self._load_physics_timeseries(prediction)
        timeseries_plots = self._create_timeseries_graphs(
            COLORS, prediction, bloom_dates)
        render_results(timeseries_plots, self.log)

    def _create_infile_edits(self):
        """Create YAML infile edit files for each ensemble member SOG run.
        """
        ensemble_config = self.config.ensemble
        start_year = ensemble_config.start_year
        end_year = ensemble_config.end_year + 1
        forcing_data_file_roots = ensemble_config.forcing_data_file_roots
        forcing_data_key_pairs = (
            ('wind', 'avg_historical_wind_file'),
            ('air_temperature', 'avg_historical_air_temperature_file'),
            ('cloud_fraction', 'avg_historical_cloud_file'),
            ('relative_humidity', 'avg_historical_humidity_file'),
            ('major_river', 'avg_historical_major_river_file'),
            ('minor_river', 'avg_historical_minor_river_file'),
        )
        timeseries_key_pairs = (
            ('std_phys_ts_outfile', 'std_physics'),
            ('user_phys_ts_outfile', 'user_physics'),
            ('std_bio_ts_outfile', 'std_biology'),
            ('user_bio_ts_outfile', 'user_biology'),
            ('std_chem_ts_outfile', 'std_chemistry'),
            ('user_chem_ts_outfile', 'user_chemistry'),
        )
        profiles_key_pairs = (
            ('profiles_outfile_base', 'profile_file_base'),
            ('user_profiles_outfile_base', 'user_profile_file_base'),
            ('halocline_outfile', 'halocline_file'),
            ('Hoffmueller_profiles_outfile', 'hoffmueller_file'),
            ('user_Hoffmueller_profiles_outfile', 'user_hoffmueller_file'),
        )
        self.edit_files = []
        for year in range(start_year, end_year):
            suffix = two_yr_suffix(year)
            member_infile_edits = infile_edits_template.copy()
            forcing_data = member_infile_edits['forcing_data']
            timeseries_results = member_infile_edits['timeseries_results']
            profiles_results = member_infile_edits['profiles_results']
            for config_key, infile_key in forcing_data_key_pairs:
                filename = ''.join(
                    (forcing_data_file_roots[config_key], suffix))
                forcing_data[infile_key]['value'] = filename
            for config_key, infile_key in timeseries_key_pairs:
                filename = ''.join((getattr(self.config, config_key), suffix))
                timeseries_results[infile_key]['value'] = filename
            for config_key, infile_key in profiles_key_pairs:
                filename = ''.join((getattr(self.config, config_key), suffix))
                profiles_results[infile_key]['value'] = filename
            name, ext = os.path.splitext(ensemble_config.base_infile)
            filename = ''.join((name, suffix, ext))
            with open(filename, 'wt') as f:
                yaml.dump(member_infile_edits, f)
            self.edit_files.append((year, filename, suffix))
            self.log.debug('wrote infile edit file {}'.format(filename))

    def _create_batch_description(self):
        """Create the YAML batch description file for the ensemble runs.
        """
        batch_description = {
            'max_concurrent_jobs': self.config.ensemble.max_concurrent_jobs,
            'SOG_executable': self.config.SOG_executable,
            'base_infile': self.config.ensemble.base_infile,
            'jobs': [],
        }
        for year, edit_file, suffix in self.edit_files:
            job = {
                ''.join(('bloomcast', suffix)): {
                    'edit_files': [edit_file],
                }
            }
            batch_description['jobs'].append(job)
        filename = 'bloomcast_ensemble_jobs.yaml'
        with open(filename, 'wt') as f:
            yaml.dump(batch_description, f)
        self.log.debug(
            'wrote ensemble batch description file: {}'.format(filename))

    def _run_SOG_batch(self):
        """Run the ensemble of SOG runs at a batch job.
        """
        if not self.config.run_SOG:
            self.log.info('Skipped running SOG')
            return
        returncode = SOGcommand.api.batch('bloomcast_ensemble_jobs.yaml')
        self.log.info(
            'ensemble batch SOG runs completed with return code {}'
            .format(returncode))

    def _load_biology_timeseries(self):
        """Load biological timeseries results from all ensemble SOG runs.
        """
        self.nitrate_ts, self.diatoms_ts = {}, {}
        for member, edit_file, suffix in self.edit_files:
            filename = ''.join((self.config.std_bio_ts_outfile, suffix))
            self.nitrate_ts[member] = utils.SOG_Timeseries(filename)
            self.nitrate_ts[member].read_data(
                'time', '3 m avg nitrate concentration')
            self.nitrate_ts[member].calc_mpl_dates(self.config.run_start_date)
            self.diatoms_ts[member] = utils.SOG_Timeseries(filename)
            self.diatoms_ts[member].read_data(
                'time', '3 m avg micro phytoplankton biomass')
            self.diatoms_ts[member].calc_mpl_dates(self.config.run_start_date)
            self.log.debug(
                'read nitrate & diatoms timeseries from {}'.format(filename))
        self.nitrate = copy.deepcopy(self.nitrate_ts)
        self.diatoms = copy.deepcopy(self.diatoms_ts)

    def _calc_bloom_dates(self):
        """Calculate the predicted spring bloom date.
        """
        run_start_date = self.config.run_start_date
        bloomcast.clip_results_to_jan1(
            self.nitrate, self.diatoms, run_start_date)
        bloomcast.reduce_results_to_daily(
            self.nitrate, self.diatoms, run_start_date,
            self.config.SOG_timestep)
        first_low_nitrate_days = bloomcast.find_low_nitrate_days(
            self.nitrate, bloomcast.NITRATE_HALF_SATURATION_CONCENTRATION)
        bloom_dates, bloom_biomasses = bloomcast.find_phytoplankton_peak(
            self.diatoms, first_low_nitrate_days,
            bloomcast.PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH)
        ord_days = np.array(
            [bloom_date.toordinal() for bloom_date in bloom_dates.values()])
        median = np.rint(np.median(ord_days))
        early_bound, late_bound = np.percentile(ord_days, (5, 95))
        prediction = OrderedDict([
            ('early', find_member(bloom_dates, np.trunc(early_bound))),
            ('median', find_member(bloom_dates, median)),
            ('late', find_member(bloom_dates, np.ceil(late_bound))),
        ])
        min_bound, max_bound = np.percentile(ord_days, (0, 100))
        extremes = OrderedDict([
            ('min', find_member(bloom_dates, np.trunc(min_bound))),
            ('max', find_member(bloom_dates, np.ceil(max_bound))),
        ])
        self.log.debug(
            'Predicted earliest bloom date is {}'
            .format(bloom_dates[extremes['min']]))
        self.log.debug(
            'Earliest bloom date is based on forcing from {}/{}'
            .format(extremes['min'] - 1, extremes['min']))
        self.log.info(
            'Predicted early bound bloom date is {}'
            .format(bloom_dates[prediction['early']]))
        self.log.debug(
            'Early bound bloom date is based on forcing from {}/{}'
            .format(prediction['early'] - 1, prediction['early']))
        self.log.info(
            'Predicted median bloom date is {}'
            .format(bloom_dates[prediction['median']]))
        self.log.debug(
            'Median bloom date is based on forcing from {}/{}'
            .format(prediction['median'] - 1, prediction['median']))
        self.log.info(
            'Predicted late bloom date is {}'
            .format(bloom_dates[prediction['late']]))
        self.log.debug(
            'Late bloom date is based on forcing from {}/{}'
            .format(prediction['late'] - 1, prediction['late']))
        self.log.debug(
            'Predicted latest bloom date is {}'
            .format(bloom_dates[extremes['max']]))
        self.log.debug(
            'Latest bloom date is based on forcing from {}/{}'
            .format(extremes['max'] - 1, extremes['max']))
        line = (
            '  {data_date}'
            .format(data_date=self.config.data_date.format('YYYY-MM-DD')))
        for member in 'median early late'.split():
            line += (
                '      {bloom_date}  {forcing_year}'
                .format(
                    bloom_date=bloom_dates[prediction[member]],
                    forcing_year=prediction[member]))
        for member in extremes.values():
            line += (
                '      {bloom_date}  {forcing_year}'
                .format(
                    bloom_date=bloom_dates[member],
                    forcing_year=member))
        self.bloom_date_log.info(line)
        return prediction, bloom_dates

    def _load_physics_timeseries(self, prediction):
        """Load physics timeseries results from SOG ensemble members that
        show median and bounding bloom dates.

        :arg prediction: Ensemble member identifiers for predicted bloom dates.
        :type prediction: dict
        """
        self.temperature, self.salinity = {}, {}
        self.mixing_layer_depth = {}
        for member in prediction.values():
            suffix = two_yr_suffix(member)
            filename = ''.join((self.config.std_phys_ts_outfile, suffix))
            self.temperature[member] = utils.SOG_Timeseries(filename)
            self.temperature[member].read_data('time', '3 m avg temperature')
            self.temperature[member].calc_mpl_dates(self.config.run_start_date)
            self.salinity[member] = utils.SOG_Timeseries(filename)
            self.salinity[member].read_data('time', '3 m avg salinity')
            self.salinity[member].calc_mpl_dates(self.config.run_start_date)
            self.log.debug(
                'read temperature and salinity timeseries from {}'
                .format(filename))
        suffix = two_yr_suffix(prediction['median'])
        filename = ''.join((self.config.std_phys_ts_outfile, suffix))
        self.mixing_layer_depth = utils.SOG_Timeseries(filename)
        self.mixing_layer_depth.read_data(
            'time', 'mixing layer depth')
        self.mixing_layer_depth.calc_mpl_dates(
            self.config.run_start_date)
        self.log.debug(
            'read mixing layer depth timeseries from {}'.format(filename))
        filename = 'Sandheads_wind'
        self.wind = wind.WindTimeseries(filename)
        self.wind.read_data(self.config.run_start_date)
        self.wind.calc_mpl_dates(self.config.run_start_date)
        self.log.debug(
            'read wind speed forcing timeseries from {}'.format(filename))

    def _create_timeseries_graphs(self, colors, prediction, bloom_dates):
        """Create time series plot figure objects.
        """
        timeseries_plots = {
            'nitrate_diatoms': visualization.nitrate_diatoms_timeseries(
                self.nitrate_ts,
                self.diatoms_ts,
                colors,
                self.config.data_date,
                prediction,
                bloom_dates,
                titles=('3 m Avg Nitrate Concentration [uM N]',
                        '3 m Avg Diatom Biomass [uM N]'),
            ),
            'temperature_salinity': visualization.temperature_salinity_timeseries(
                self.temperature,
                self.salinity,
                colors,
                self.config.data_date,
                prediction,
                bloom_dates,
                titles=('3 m Avg Temperature [deg C]',
                        '3 m Avg Salinity [-]'),
            ),
            'mld_wind': visualization.mixing_layer_depth_wind_timeseries(
                self.mixing_layer_depth,
                self.wind,
                colors,
                self.config.data_date,
                titles=('Mixing Layer Depth [m]',
                        'Wind Speed [m/s]'),
            ),
        }
        return timeseries_plots


def configure_logging(config, bloom_date_log):
    """Configure logging of debug & warning messages to console
    and email, and bloom date evolution to disk file.

    Debug logging on/off & email recipient(s) for warning messages
    are set in config file.
    """
    root_logger = logging.getLogger('')
    console_handler = root_logger.handlers[0]

    def patched_data_filter(record):
        if (record.funcName == 'patch_data'
                and 'data patched' in record.msg):
            return 0
        return 1
    console_handler.addFilter(patched_data_filter)

    def requests_info_debug_filter(record):
        if (record.name.startswith('requests.')
                and record.levelname in {'INFO', 'DEBUG'}):
            return 0
        return 1
    console_handler.addFilter(requests_info_debug_filter)

    disk = logging.handlers.RotatingFileHandler(
        config.logging.bloomcast_log_filename, maxBytes=1024 * 1024)
    disk.setFormatter(
        logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M'))
    disk.setLevel(logging.DEBUG)
    disk.addFilter(requests_info_debug_filter)
    root_logger.addHandler(disk)

    mailhost = (('localhost', 1025) if config.logging.use_test_smtpd
                else 'smtp.eos.ubc.ca')
    email = logging.handlers.SMTPHandler(
        mailhost, fromaddr='SoG-bloomcast@eos.ubc.ca',
        toaddrs=config.logging.toaddrs,
        subject='Warning Message from SoG-bloomcast',
        timeout=10.0,
    )
    email.setFormatter(
        logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    email.setLevel(logging.WARNING)
    root_logger.addHandler(email)

    bloom_date_evolution = logging.FileHandler(
        config.logging.bloom_date_log_filename)
    bloom_date_evolution.setFormatter(logging.Formatter('%(message)s'))
    bloom_date_evolution.setLevel(logging.INFO)
    bloom_date_log.addHandler(bloom_date_evolution)
    bloom_date_log.propagate = False


def get_forcing_data(config, log):
    """Collect and process forcing data.
    """
    if not config.get_forcing_data:
        log.info('Skipped collection and processing of forcing data')
        return
    wind_processor = wind.WindProcessor(config)
    config.data_date = wind_processor.make_forcing_data_file()
    log.info('based on wind data forcing data date is {}'
             .format(config.data_date.format('YYYY-MM-DD')))
    try:
        with open('wind_data_date', 'rt') as f:
            last_data_date = arrow.get(f.readline().strip()).date()
    except IOError:
        # Fake a wind data date to get things rolling
        last_data_date = config.run_start_date.date()
    if config.data_date == last_data_date:
        raise ValueError
    else:
        with open('wind_data_date', 'wt') as f:
            f.write('{}\n'.format(config.data_date.format('YYYY-MM-DD')))
    meteo_processor = meteo.MeteoProcessor(config)
    meteo_processor.make_forcing_data_files()
    rivers_processor = rivers.RiversProcessor(config)
    rivers_processor.make_forcing_data_files()


def two_yr_suffix(year):
    """Return a suffix string of the form ``_XXYY`` based on year,
    where XX = the last 2 digits of year - 1,
    and YY = the last 2 digits of year

    :arg year: Year from which to build the suffix;
               2nd year in suffix;
               e.g. 1891 produces ``_8081``
    :type year: int

    :returns: String of the form ``_XXYY`` like ``_8081`` for 1981
    """
    return ('_{year_m1}{year}'
            .format(
                year_m1=str(year - 1)[-2:],
                year=str(year)[-2:]))


def find_member(bloom_dates, ord_day):
    """Find the ensemble member whose bloom date is ord_day.

    If more than one member has ord_day as its bloom date,
    choose the member with the most recent year's forcing.

    If there is no member with ord_day as its bloom date look at
    adjacent days and choose the member with the most recent year's
    forcing.

    :arg bloom_dates: Predicted bloom dates.
    :type bloom_dates: dict keyed by ensemble member identifier

    :arg ord_day: Bloom date expressed as an ordinal day.
    :type ord_day: int

    :returns: Ensemble member identifier
    :rtype: str
    """
    def find_matches(day):
        return [
            member for member, bloom_date in bloom_dates.items()
            if bloom_date.toordinal() == day
        ]
    matches = find_matches(ord_day)
    if not matches:
        for i in range(1, 11):
            matches.extend(find_matches(ord_day + i))
            matches.extend(find_matches(ord_day - i))
            if matches:
                break
    return max(matches)


def render_results(timeseries_plots, log):
    """Render bloomcast results and plots to files.
    """
    for key, fig in timeseries_plots.items():
        filename = '{}_timeseries.svg'.format(key)
        visualization.save_as_svg(fig, filename)
        log.debug('saved {} time series figure as {}'.format(key, filename))


infile_edits_template = {   # pragma: no cover
    'forcing_data': {
        'use_average_forcing_data': {
            'description': 'yes=avg only; no=fail if data runs out; fill=historic then avg',
            'value': 'histfill',
            'variable_name': 'use_average_forcing_data'
        },
        'avg_historical_wind_file': {
            'description': 'average/historical wind forcing data path/filename',
            'value': None,
            'variable_name': 'n/a',
        },
        'avg_historical_air_temperature_file': {
            'description': 'average/historical air temperature forcing data path/filename',
            'value': None,
            'variable_name': 'n/a',
        },
        'avg_historical_cloud_file': {
            'description': 'average/historical cloud fraction forcing data path/filename',
            'value': None,
            'variable_name': 'n/a'
        },
        'avg_historical_humidity_file': {
            'description': 'average/historical humidity forcing data path/filename',
            'value': None,
            'variable_name': 'n/a',
        },
        'avg_historical_major_river_file': {
            'description': 'average/historical major river forcing data path/filename',
            'value': None,
            'variable_name': 'n/a',
        },
        'avg_historical_minor_river_file': {
            'description': 'average/historical minor river forcing data path/filename',
            'value': None,
            'variable_name': 'n/a',
        },
    },

    'timeseries_results': {
        'std_physics': {
            'description': 'path/filename for standard physics time series output',
            'value': None,
            'variable_name': 'std_phys_ts_out',
        },
        'user_physics': {
            'description': 'path/filename for user physics time series output',
            'value': None,
            'variable_name': 'user_phys_ts_out',
        },
        'std_biology': {
            'description': 'path/filename for standard biology time series output',
            'value': None,
            'variable_name': 'std_bio_ts_out',
        },
        'user_biology': {
            'description': 'path/filename for user biology time series output',
            'value': None,
            'variable_name': 'user_bio_ts_out',
        },
        'std_chemistry': {
            'description': 'path/filename for standard chemistry time series output',
            'value': None,
            'variable_name': 'std_chem_ts_out',
        },
        'user_chemistry': {
            'description': 'path/filename for user chemistry time series output',
            'value': None,
            'variable_name': 'user_chem_ts_out',
        },
    },

    'profiles_results': {
        'profile_file_base': {
            'description': 'path/filename base for profiles (datetime will be appended)',
            'value': None,
            'variable_name': 'profilesBase_fn',
        },
        'user_profile_file_base': {
            'description': 'path/filename base for user profiles (datetime appended)',
            'value': None,
            'variable_name': 'userprofilesBase_fn',
        },
        'halocline_file': {
            'description': 'path/filename for halocline results',
            'value': None,
            'variable_name': 'haloclines_fn',
        },
        'hoffmueller_file': {
            'description': 'path/filename for Hoffmueller results',
            'value': None,
            'variable_name': 'Hoffmueller_fn',
        },
        'user_hoffmueller_file': {
            'description': 'path/filename for user Hoffmueller results',
            'value': None,
            'variable_name': 'userHoffmueller_fn',
        },
    },
}
