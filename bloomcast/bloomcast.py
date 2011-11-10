"""Driver module for SoG-bloomcast project
"""
from __future__ import absolute_import
from __future__ import division
# Standard library:
from datetime import datetime
import logging
import logging.handlers
from subprocess import Popen
from subprocess import STDOUT
import sys
# Bloomcast:
from meteo import MeteoProcessor
from rivers import RiversProcessor
from utils import Config
from utils import SOG_Timeseries
from wind import WindProcessor


log = logging.getLogger('bloomcast')


def run(config_file):
    """Run the bloomcast process.

    * Load the process configuration data.

    * Get the wind forcing data.

    * Get the meteorological and river flow forcing data.

    * Run the SOG code.
    """
    config = Config()
    config.load_config(config_file)
    configure_logging(config)
    log.debug('run start date is {0:%Y-%m-%d}'.format(config.run_start_date))
    get_forcing_data(config)
    run_SOG(config)
    calc_bloom_date(config)


def get_forcing_data(config):
    """Collect and process forcing data.
    """
    if  not config.get_forcing_data:
        log.info('Skipped collection and processing of forcing data')
        return
    wind = WindProcessor(config)
    config.data_date = wind.make_forcing_data_file()
    log.info('based on wind data run data date is {0:%Y-%m-%d}'
              .format(config.data_date))
    meteo = MeteoProcessor(config)
    meteo.make_forcing_data_files()
    rivers = RiversProcessor(config)
    rivers.make_forcing_data_files()


def run_SOG(config):
    """Run SOG.
    """
    if not config.run_SOG:
        log.info('Skipped running SOG')
        return
    log.info('SOG run started at {0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))
    with open(config.infile, 'rt') as infile_obj:
        with open(config.infile + '.stdout', 'wt') as stdout_obj:
            SOG = Popen('nice -19 ../SOG-code-ocean/SOG'.split(),
                        stdin=infile_obj, stdout=stdout_obj, stderr=STDOUT)
            SOG.wait()
    log.info(
        'SOG run finished at {0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))


def calc_bloom_date(config):
    """
    """
    nitrate = SOG_Timeseries(config.std_bio_ts_outfile)
    nitrate.read_data('time', '3 m avg nitrate concentration')
    micro_phyto = SOG_Timeseries(config.std_bio_ts_outfile)
    micro_phyto.read_data('time', '3 m avg micro phytoplankton biomass')
    jan1 = datetime(config.run_start_date.year + 1, 1, 1)
    discard_hours = (jan1 - config.run_start_date)
    discard_hours = discard_hours.days * 24 + discard_hours.seconds / 3600
    selector = nitrate.indep_data >= discard_hours
    nitrate.indep_data = nitrate.indep_data[selector]
    nitrate.dep_data = nitrate.dep_data[selector]
    micro_phyto.indep_data = micro_phyto.indep_data[selector]
    micro_phyto.dep_data = micro_phyto.dep_data[selector]


def configure_logging(config):
    """Configure logging of debug & warning messages to console and email.

    Debug logging on/off & email recipient(s) for warning messages are
    set in config file.
    """
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    if config.logging.debug:
        console.setLevel(logging.DEBUG)
    log.addHandler(console)
    mailhost = (('localhost', 1025) if config.logging.use_test_smtpd
                else 'localhost')
    email = logging.handlers.SMTPHandler(
        mailhost, fromaddr='SoG-bloomcast@eos.ubc.ca',
        toaddrs=config.logging.toaddrs,
        subject='Warning Message from SoG-bloomcast')
    email.setFormatter(formatter)
    email.setLevel(logging.WARNING)
    log.addHandler(email)


if __name__ == '__main__':
    run(sys.argv[1])
