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

"""Special use script to help with cloud fraction algorithm improvement.

Code from other bloomcast modules is repeated here rather than implementing
an API in bloomcast to support this use.

* Retrieve hourly YVR meteo data for 1-Jan-2002 to 31-Dec-2011 (10 years)
  from EC web data service

* Parse weather description string from meteo data

* Parse corresponding hour's cloud fraction float value from
  SOG-forcing/met/YVRhistCF

* The result will be about 87,648 records of data, with 3 columns each::

    datetime, weather description, cloud fraction

  Hours for which there is no weather description in the EC data will be
  skipped.

  Write those data to a text file (manipulable with grep, uniq, etc.)

Susan analyzed samples of those data and found that there is variation
from month to month in the cloud fraction value for some of the
weather descriptions.
The algorithm she decided on is:

* If there are more than 500 observations for a given weather description,
  calculate the average cloud fraction value for each month

* If there are 500 or fewer observations,
  calculate a single average cloud fraction value.

* The resulting cloud fraction mapping YAML file will have:

  * weather description strings as keys
  * arrays of either 1 or 12 cloud fraction values as values
"""
import contextlib
from cStringIO import StringIO
from datetime import (
    date,
    datetime,
    )
import logging
from xml.etree import cElementTree as ElementTree
import requests
import yaml


EC_URL = 'http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html'
START_YEAR = 2002
END_YEAR = 2011
YVR_CF_FILE = '../../SOG-forcing/met/YVRhistCF'
DUMP_HOURLY_RESULTS = False
HOURLY_FILE = 'cf_analysis.txt'
# Threshold for number of observations of a given weather description
# at which to switch from averaging all values to averaging values for
# each month
AVERAGING_THRESHOLD = 500
MAPPING_FILE = 'cloud_fraction_mapping.yaml'


root_log = logging.getLogger()
log = logging.getLogger('cf_analysis')
logging.basicConfig(level=logging.DEBUG)
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)
log.addHandler(console)
disk = logging.FileHandler('cf_analysis.log', mode='w')
disk.setFormatter(formatter)
log.addHandler(disk)
root_log.addHandler(disk)
log.propagate = False


def run():
    data_months = (
        date(year, month, 1)
        for year in xrange(2002, 2012)
        for month in xrange(1, 13)
        )
    request_params = {
        'timeframe': 1,                 # Daily
        'Prov': 'BC',
        'format': 'xml',
        'StationID': 889,               # YVR
        'Day': 1,
        }
    mapping = {}
    yvr_file = open(YVR_CF_FILE, 'rt')
    context = contextlib.nested(yvr_file)
    if DUMP_HOURLY_RESULTS:
        hourly_file = open(HOURLY_FILE, 'wt')
        context = contextlib.nested(yvr_file, hourly_file)
    with context:
        for data_month in data_months:
            ec_data = get_EC_data(data_month, request_params)
            yvr_data = get_yvr_line(yvr_file, START_YEAR).next()
            for record in ec_data.findall('stationdata'):
                parts = [record.get(part)
                         for part in 'year month day hour'.split()]
                timestamp = datetime(*map(int, parts))
                weather_desc = record.find('weather').text
                if weather_desc is None:
                    log.info(
                        'Missing weather description at {0:%Y-%m-%d %H:%M} '
                        'skipped'.format(timestamp))
                    continue
                while timestamp.date() > yvr_data['date']:
                    yvr_data = get_yvr_line(yvr_file, START_YEAR).next()
                if DUMP_HOURLY_RESULTS:
                    write_hourly_line(
                        timestamp, weather_desc, yvr_data, hourly_file)
                build_raw_mapping(mapping, weather_desc, timestamp, yvr_data)
    calc_mapping_averages(mapping)
    with open(MAPPING_FILE, 'wt') as mapping_file:
        yaml.dump(mapping, mapping_file)


def get_EC_data(data_month, request_params):
    request_params.update({
        'Year': data_month.year,
        'Month': data_month.month,
        })
    response = requests.get(EC_URL, params=request_params)
    log.info('got meteo data for {0:%Y-%m}'.format(data_month))
    tree = ElementTree.parse(StringIO(response.content))
    ec_data = tree.getroot()
    return ec_data


def get_yvr_line(yvr_file, start_year):
    data_date = date(1867, 1, 1)
    while data_date < date(start_year, 1, 1):
        parts = yvr_file.next().split()
        data_date = date(*map(int, parts[1:4]))
    else:
        yvr_data = {
            'date': data_date,
            'hourly_cfs': map(float, parts[5:29]),
            }
        yield yvr_data


def write_hourly_line(timestamp, weather_desc, yvr_data, hourly_file):
    result_line = (
        '{0:%Y-%m-%d %H:%M:%S} {1} {2}\n'
        .format(timestamp, weather_desc,
                yvr_data['hourly_cfs'][timestamp.hour]))
    hourly_file.write(result_line)


def build_raw_mapping(mapping, weather_desc, timestamp, yvr_data):
    try:
        mapping[weather_desc][timestamp.month].append(
            yvr_data['hourly_cfs'][timestamp.hour])
    except KeyError:
        mapping[weather_desc] = [
            [], [], [], [], [], [], [], [], [], [], [], [], [],
            ]
        mapping[weather_desc][timestamp.month].append(
            yvr_data['hourly_cfs'][timestamp.hour])
        log.info('"{0}" added to mapping'.format(weather_desc))


def calc_mapping_averages(mapping):
    for weather_desc, months in mapping.iteritems():
        total_observations = sum(len(month) for month in months)
        if total_observations > AVERAGING_THRESHOLD:
            log.info(
                'using monthly averaging for {0} "{1}" observation(s)'
                .format(total_observations, weather_desc))
            for i, month in enumerate(months):
                try:
                    mapping[weather_desc][i] = sum(month) / len(month)
                except ZeroDivisionError:
                    mapping[weather_desc][i] = []
            mapping[weather_desc].pop(0)
        else:
            log.info(
                'using all value averaging for {0} "{1}" observation(s)'
                .format(total_observations, weather_desc))
            mapping[weather_desc] = [
                sum(sum(month) for month in months) / total_observations
                ]


if __name__ == '__main__':
    run()
