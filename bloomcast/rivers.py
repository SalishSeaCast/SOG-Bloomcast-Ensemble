"""Rivers flows forcing data processing module for SoG-bloomcast project.
"""
from __future__ import absolute_import
# Standard library:
from datetime import date
import logging
import sys
# HTTP Requests library:
import requests
# Bloomcast:
from utils import Config


log = logging.getLogger(__name__)


class RiversProcessor(object):
    """River flows forcing data processor.
    """
    def __init__(self, config):
        self.config = config
        self.data_readers = {'wind': self.read_river_flow}
        self.hourlies = {}


    def make_forcing_data_files(self):
        """
        """
        self.get_river_data()


    def get_river_data(self):
        """
        """
        params = self.config.rivers.params
        river = 'primary'
        params['stn'] = getattr(self.config.rivers, river).station_id
        params.update(self._date_params())
        with requests.session() as s:
            s.post(self.config.rivers.disclaimer_url,
                   data=self.config.rivers.accept_disclaimer)
            response = s.get(self.config.rivers.data_url, params=params)


    def _date_params(self):
        """
        """
        today = date.today()
        params = {
            'syr': today.year,
            'smo': today.month,
            'sday': 1,
            'eyr': today.year,
            'emo': today.month,
            'eday': today.day - 1,
        }
        return params


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
