"""Driver module for SoG-bloomcast project
"""
from __future__ import absolute_import
# Standard library:
import logging
import sys
# Bloomcast:
from utils import Config
from wind import WindProcessor
from meteo import MeteoProcessor
from rivers import RiversProcessor


log = logging.getLogger('bloomcast')


def run(config_file):
    """
    """
    config = Config()
    config.load_config(config_file)
    configure_logging(config_file)
    wind = WindProcessor(config)
    config.data_date = wind.make_forcing_data_file()
    log.debug('based on wind data run data date is {0:%Y-%m-%d}'
              .format(config.data_date))
    meteo = MeteoProcessor(config)
    meteo.make_forcing_data_files()
    rivers = RiversProcessor(config)
    rivers.make_forcing_data_files()


def configure_logging(config_file):
    """
    """
    ### TODO: Configure email logger for unrecognized weather descriptions
    logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':
    run(sys.argv[1])
