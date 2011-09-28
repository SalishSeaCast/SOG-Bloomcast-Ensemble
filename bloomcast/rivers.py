"""Rivers flows forcing data processing module for SoG-bloomcast project.
"""
from __future__ import absolute_import
# Standard library:
from datetime import date
from datetime import datetime
from itertools import izip
import logging
import sys
# HTTP Requests library:
import requests
# BeautifulSoup:
from BeautifulSoup import BeautifulSoup
# Bloomcast:
from utils import Config
from utils import ForcingDataProcessor


log = logging.getLogger(__name__)


class RiversProcessor(ForcingDataProcessor):
    """River flows forcing data processor.
    """
    def __init__(self, config):
        super(RiversProcessor, self).__init__(config)


    def make_forcing_data_files(self):
        """
        """
        self.get_river_data()
        self.process_data()


    def get_river_data(self):
        """Return a BeautifulSoup parser object containing the
        river flow data table Environment Canada WaterOffice page.
        """
        params = self.config.rivers.params
        river = 'major'
        params['stn'] = getattr(self.config.rivers, river).station_id
        params.update(self._date_params())
        with requests.session() as s:
            s.post(self.config.rivers.disclaimer_url,
                   data=self.config.rivers.accept_disclaimer)
            response = s.get(self.config.rivers.data_url, params=params)
        soup = BeautifulSoup(response)
        self.data = soup.find('table', id='dataTable')


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
            'eday': 2,
        }
        return params


    def process_data(self, end_date=date.today()):
        """Process data from BeautifulSoup parser object to a list of
        hourly timestamps and data values.
        """
        tds = self.data.findAll('td')
        timestamps = (td.string for td in tds[::2])
        flows = (td.string for td in tds[1::2])
        data_day = self.read_datestamp(tds[0].string)
        flow_sum = count = 0
        self.dailies = []
        for timestamp, flow in izip(timestamps, flows):
            datestamp = self.read_datestamp(timestamp)
            if datestamp == data_day:
                flow_sum += float(flow)
                count += 1
            else:
                self.dailies.append((data_day, flow_sum / count))
                data_day = datestamp
                flow_sum = float(flow)
                count = 1
        else:
            self.dailies.append((data_day, flow_sum / count))


    def read_datestamp(self, string):
        """
        """
        return datetime.strptime(string, '%Y-%m-%d %H:%M:%S').date()


    def format_data(self):
        """Generate lines of river flow forcing data in the format
        expected by SOG.

        Each line starts with 3 integers:

        * Year
        * Month
        * Day

        That is followed by a float in scientific notation:

        * average flow for the day
        """
        for data in self.dailies:
            datestamp = data[0]
            flow = data[1]
            line = '{0:%Y %m %d} {1:e}\n'.format(datestamp, flow)
            yield line


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
