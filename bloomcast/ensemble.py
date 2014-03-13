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

import arrow
import cliff.command

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
        configure_logging(self.config, self.log, self.bloom_date_log)
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


def configure_logging(config, log, bloom_date_log):
    """Configure logging of debug & warning messages to console
    and email, and bloom date evolution to disk file.

    Debug logging on/off & email recipient(s) for warning messages
    are set in config file.
    """
    log.setLevel(logging.DEBUG)

    def patched_data_filter(record):
        if (record.funcName == 'patch_data'
                and 'data patched' in record.msg):
            return 0
        return 1

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    console.setLevel(logging.INFO)
    if config.logging.debug:
        console.setLevel(logging.DEBUG)
    console.addFilter(patched_data_filter)
    log.addHandler(console)

    disk = logging.handlers.RotatingFileHandler(
        config.logging.bloomcast_log_filename, maxBytes=1024 * 1024)
    disk.setFormatter(
        logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M'))
    disk.setLevel(logging.DEBUG)
    log.addHandler(disk)

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
    log.addHandler(email)

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
