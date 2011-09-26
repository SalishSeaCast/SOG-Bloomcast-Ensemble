"""Rivers flows forcing data processing module for SoG-bloomcast project.
"""
from __future__ import absolute_import
# Standard library:
import logging
import sys
# Bloomcast:
from utils import Config


log = logging.getLogger(__name__)


class RiversProcessor(object):
    """River flows forcing data processor.
    """
    def __init__(self, config):
        data_readers = {'wind': self.read_river_flow}


    def make_forcing_data_file(self):
        """
        """
        self.get_river_data()


    def get_river_data(self):
        """
        """


    def read_river_flow(self):
        """
        """


def run(config_file):
    """Process river flows forcing data into SOG forcing data files by
    running the RiversProcessor object independent of bloomcast.
    """
    logging.basicConfig(level=logging.DEBUG)
    config = Config()
    config.load_config(config_file)
    rivers = RiversProcessor(config)
    rivers.make_forcing_data_files()


if __name__ == '__main__':
    run(sys.argv[1])
