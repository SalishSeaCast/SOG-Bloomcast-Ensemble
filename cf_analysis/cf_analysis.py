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

  Write those data to 1 or more repositories, perhaps:

  * a text file (manipulable with grep, uniq, etc.)
  * a sqlite database file (manipulable with SQLAlchemy)
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


EC_URL = 'http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html'
START_YEAR = 2002
END_YEAR = 2011
YVR_CF_FILE = '../../SOG-forcing/met/YVRhistCF'
RESULTS_FILE = 'cf_analysis.txt'


log = logging.getLogger('cf_analysis')


def run():
    logging.basicConfig(level=logging.DEBUG)
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
    yvr_file = open(YVR_CF_FILE, 'rt')
    results_file = open(RESULTS_FILE, 'wt')
    with contextlib.nested(yvr_file, results_file):
        for data_month in data_months:
            request_params.update({
                'Year': data_month.year,
                'Month': data_month.month,
                })
            response = requests.get(EC_URL, params=request_params)
            log.debug('got meteo data for {0:%Y-%m}'.format(data_month))
            tree = ElementTree.parse(StringIO(response.content))
            root = tree.getroot()
            yvr_data = get_yvr_line(yvr_file, START_YEAR).next()
            for record in root.findall('stationdata'):
                parts = [record.get(part)
                         for part in 'year month day hour'.split()]
                timestamp = datetime(*map(int, parts))
                weather_desc = record.find('weather').text
                while timestamp.date() > yvr_data['date']:
                    yvr_data = get_yvr_line(yvr_file, START_YEAR).next()
                result_line = (
                    '{0:%Y-%m-%d %H:%M:%S} {1} {2}\n'
                    .format(timestamp, weather_desc,
                            yvr_data['hourly_cfs'][timestamp.hour]))
                results_file.write(result_line)


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


if __name__ == '__main__':
    run()
