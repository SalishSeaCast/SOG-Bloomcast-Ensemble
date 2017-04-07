# Copyright 2011-2015 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Rivers flows forcing data processing module for SoG-bloomcast project.
"""
import datetime
import logging
import sys
import time

import arrow
import requests
import bs4

from .utils import (
    Config,
    ForcingDataProcessor,
)


log = logging.getLogger('bloomcast.rivers')


class RiversProcessor(ForcingDataProcessor):
    """River flows forcing data processor.
    """
    def __init__(self, config):
        super(RiversProcessor, self).__init__(config)

    def make_forcing_data_files(self):
        """Get the river flows forcing data from the Environment
        Canada WaterOffice website, process it to extract average
        daily flow values from the HTML table, trim incomplete days
        from the end, patch missing values, and write the data to
        files in the format that SOG expects.
        """
        for river in 'major minor'.split():
            self.get_river_data(river)
            self.process_data(river, end_date=self.config.data_date)
            output_file = self.config.rivers.output_files[river]
            with open(output_file, 'wt') as file_obj:
                file_obj.writelines(self.format_data(river))
            log.debug(
                'latest {0} river flow {1}'
                .format(river, self.data[river][-1]))

    def get_river_data(self, river):
        """Return a BeautifulSoup parser object containing the river
        flow data table scraped from the Environment Canada
        WaterOffice page.
        """
        params = self.config.rivers.params
        params['stn'] = getattr(self.config.rivers, river).station_id
        today = arrow.now().date()
        start_year = (self.config.run_start_date.year
                      if self.config.run_start_date.year != today.year
                      else today.year)
        params.update(self._date_params(start_year))
        response = requests.get(
            self.config.rivers.data_url,
            params=params,
            cookies=self.config.rivers.disclaimer_cookie)
        log.debug(
            'got {0} river data for {1}-01-01 to {2}'
            .format(
                river, start_year,
                self.config.data_date.format('YYYY-MM-DD')))
        soup = bs4.BeautifulSoup(response.content, 'html.parser')
        self.raw_data = soup.find('table')

    def _date_params(self, start_year):
        """Return a dict of the components of start and end dates for
        river flow data based on the specified start year.

        The keys are the component names in the format required for
        requests to the :kbd:`wateroffice.gc.ca` site.

        The values are date components as integers.
        """
        end_date = self.config.data_date.replace(days=+1)
        params = {
            'startDate': arrow.get(start_year, 1, 1).format('YYYY-MM-DD'),
            'endDate': end_date.format('YYYY-MM-DD')
        }
        return params

    def process_data(self, qty, end_date=arrow.now().floor('day')):
        """Process data from BeautifulSoup parser object to a list of
        hourly timestamps and data values.
        """
        tds = self.raw_data.findAll('td')
        timestamps = (td.string for td in tds[::2])
        flows = (td.text for td in tds[1::2])
        data_day = self.read_datestamp(tds[0].string)
        flow_sum = count = 0
        self.data[qty] = []
        for timestamp, flow in zip(timestamps, flows):
            datestamp = self.read_datestamp(timestamp)
            if datestamp > end_date.date():
                break
            if datestamp == data_day:
                flow_sum += self._convert_flow(flow)
                count += 1
            else:
                self.data[qty].append((data_day, flow_sum / count))
                data_day = datestamp
                flow_sum = self._convert_flow(flow)
                count = 1
        self.data[qty].append((data_day, flow_sum / count))
        self.patch_data(qty)

    def _convert_flow(self, flow_string):
        """Convert a flow data value from a string to a float.

        Handles 'provisional values' which are marked with a `*` at
        the end of the string.
        """
        try:
            return float(flow_string.replace(',', ''))
        except ValueError:
            # Ignore training `*`
            return float(flow_string[:-1].replace(',', ''))

    def read_datestamp(self, string):
        """Read datestamp from BeautifulSoup parser object and return
        it as a date instance.
        """
        return datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S').date()

    def patch_data(self, qty):
        """Patch missing data values by interpolation.
        """
        i = 0
        data = self.data[qty]
        gap_count = 0
        while True:
            try:
                delta = (data[i + 1][0] - data[i][0]).days
            except IndexError:
                break
            if delta > 1:
                gap_start = i + 1
                for j in range(1, delta):
                    missing_date = data[i][0] + j * datetime.timedelta(days=1)
                    data.insert(i + j, (missing_date, None))
                    log.debug(
                        '{qty} river data patched for {date}'
                        .format(qty=qty, date=missing_date))
                    gap_count += 1
                gap_end = i + delta - 1
                self.interpolate_values(qty, gap_start, gap_end)
            i += delta
        if gap_count:
            log.debug(
                '{count} {qty} river data values patched; '
                'see debug log on disk for details'
                .format(count=gap_count, qty=qty))

    def format_data(self, qty):
        """Generate lines of river flow forcing data in the format
        expected by SOG.

        Each line starts with 3 integers:

        * Year
        * Month
        * Day

        That is followed by a float in scientific notation:

        * average flow for the day
        """
        for data in self.data[qty]:
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
    config.data_date = arrow.now().floor('day')
    rivers = RiversProcessor(config)
    rivers.make_forcing_data_files()


if __name__ == '__main__':
    run(sys.argv[1])
