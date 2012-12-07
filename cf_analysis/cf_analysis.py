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
from datetime import date
import logging
from xml.etree import cElementTree as ElementTree
import requests

from pprint import pprint


EC_URL = 'http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html'


log = logging.getLogger('cf_analysis')


def run():
    logging.basicConfig(level=logging.DEBUG)
    data_months = [
        date(year, month, 1)
        for year in xrange(2002, 2012)
        for month in xrange(1, 13)
        ]
    for data_month in data_months:
        params = {
            'timeframe': 1,                 # Daily
            'Prov': 'BC',
            'format': 'xml',
            'StationID': 889,               # YVR
            'Year': data_month.year,
            'Month': data_month.month,
            'Day': 1,
            }
        # response = requests.get(EC_URL, params=params)
        # log.debug('got meteo data for {0:%Y-%m}'.format(data_month))

        # pprint(params)


if __name__ == '__main__':
    run()
