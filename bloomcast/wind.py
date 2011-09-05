"""Wind forcing data processing module for SoG-bloomcast project.

Monitor Sandheads wind data on Environment Canada site to determine
what the lag is between the current date and the most recent full
day's data.
"""
from __future__ import absolute_import
# Standard library:
from datetime import datetime
from StringIO import StringIO
from xml.etree import ElementTree
# HTTP Requests library:
import requests
# Bloomcast:
from utils import date_params
from utils import Config


def get_climate_data(config):
    """
    """
    params = config.climate.wind.params
    params['StationID'] = config.climate.wind.station_id
    for key, value in date_params():
        params[key] = value
    r = requests.get(config.climate.url, params=params)
    tree = ElementTree.parse(StringIO(r.content))
    root = tree.getroot()
    data = root.findall('stationdata')
    return data


def run():
    """
    """
    config = Config()
    data = get_climate_data(config)
    data.reverse()
    for record in data:
        if record.find('windspd').text:
            latest_data = '{year}-{month}-{day} {hour}:{minute} {speed}'.format(
                speed=record.find('windspd').text, **record.attrib)
            break
    print 'At {0} the lastest available wind data was for {1}'.format(
        datetime.now().strftime('%Y-%m-%d %H:%M'), latest_data)


if __name__ == '__main__':
    run()
