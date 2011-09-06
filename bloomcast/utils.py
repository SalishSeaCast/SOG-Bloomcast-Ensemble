"""Utility classes and methods for SoG-bloomcast project.

A collection of classes and module that are used in other bloomcast
modules.
"""
from __future__ import absolute_import
# Standard library:
from datetime import date
from StringIO import StringIO
from xml.etree import cElementTree as ElementTree
# HTTP Requests library:
import requests


class Config(object):
    """Placeholder for a config object that reads values from a file.
    """
    def __init__(self):
        class _Placeholder(object): pass
        self.climate = _Placeholder()
        self.climate.url = 'http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html'
        self.climate.params = {
            'timeframe': 1,
            'Prov': 'BC',
            'format': 'xml',
        }
        self.climate.meteo = _Placeholder()
        self.climate.meteo.station_id = 889
        self.climate.wind = _Placeholder()
        self.climate.wind.station_id = 6831


def get_climate_data(config, data_type):
    """Return a list of XML objects containing the specified type of
    climate data.

    The XML objects are :class:`ElementTree` subelement instances.
    """
    params = config.climate.params
    params['StationID'] = getattr(config.climate, data_type).station_id
    for key, value in date_params():
        params[key] = value
    response = requests.get(config.climate.url, params=params)
    tree = ElementTree.parse(StringIO(response.content))
    root = tree.getroot()
    data = root.findall('stationdata')
    return data


def date_params():
    """Return an iterator of key/value pairs of the components of
    today's date.

    The keys are the component names in the format required for
    requests to the :kbd:`climate.weatheroffice.gc.ca` site.

    The values are today's date components as integers.
    """
    today = date.today()
    params = {
        'Year': today.year,
        'Month': today.month,
        'Day': today.day,
    }
    return params.iteritems()
