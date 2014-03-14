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
import logging
import os

import arrow
import cliff.command
import yaml

from . import utils
from .meteo import MeteoProcessor
from .rivers import RiversProcessor
from .wind import WindProcessor


__all__ = ['Ensemble']


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
                'Wind data date {0.data_date:%Y-%m-%d} '
                'is unchanged since last run'
                .format(self.config))
            return
        self._create_infile_edits()

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
            self.log.debug('wrote infile edit file {}'.format(filename))


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
    wind = WindProcessor(config)
    config.data_date = wind.make_forcing_data_file()
    log.info('based on wind data forcing data date is {0:%Y-%m-%d}'
             .format(config.data_date))
    try:
        with open('wind_data_date', 'rt') as f:
            last_data_date = arrow.get(f.readline().strip()).date()
    except IOError:
        # Fake a wind data date to get things rolling
        last_data_date = config.run_start_date.date()
    if config.data_date == last_data_date:
        raise ValueError
    else:
        with open('wind_data_date', 'wt') as file_obj:
            file_obj.write('{0:%Y-%m-%d}\n'.format(config.data_date))
    meteo = MeteoProcessor(config)
    meteo.make_forcing_data_files()
    rivers = RiversProcessor(config)
    rivers.make_forcing_data_files()


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
