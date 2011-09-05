"""Utility classes and methods for SoG-bloomcast project.

A collection of classes and module that are used in other bloomcast
modules.
"""
from __future__ import absolute_import
# Standard library:
from datetime import date


class Config(object):
    """Placeholder for a config object that reads values from a file.
    """
    def __init__(self):
        class _Placeholder(object): pass
        self.climate = _Placeholder()
        self.climate.url = 'http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html'
        self.climate.wind = _Placeholder()
        self.climate.wind.station_id = 6831
        self.climate.wind.params = {
            'timeframe': 1,
            'Prov': 'BC',
            'format': 'xml',
        }


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
