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
# YAML library:
import yaml


class _Container(object): pass


class Config(object):
    """Placeholder for a config object that reads values from a file.
    """
    def load_config(self, config_file):
        """Load values from the specified config file into the
        attributes of the Config object.
        """
        config_dict = self._read_yaml_file(config_file)
        self.infile = config_dict['infile']
        infile_dict = self._read_SOG_infile(self.infile)
        self.climate = _Container()
        for attr in 'url params'.split():
            setattr(self.climate, attr, config_dict['climate'][attr])
        self._load_meteo_config(config_dict, infile_dict)
        self._load_wind_config(config_dict, infile_dict)


    def _load_meteo_config(self, config_dict, infile_dict):
        """Load Config values for meteorological forcing data.
        """
        self.climate.meteo = _Container()
        meteo = config_dict['climate']['meteo']
        for attr in 'station_id quantities'.split():
            setattr(self.climate.meteo, attr, meteo[attr])
        self.climate.meteo.cloud_fraction_mapping = self._read_yaml_file(
            meteo['cloud_fraction_mapping'])
        forcing_data_files = infile_dict['forcing_data_files']
        self.climate.meteo.output_files = {}
        for qty in self.climate.meteo.quantities:
            self.climate.meteo.output_files[qty] = forcing_data_files[qty]


    def _load_wind_config(self, config_dict, infile_dict):
        """Load Config values for wind forcing data.
        """
        self.climate.wind = _Container()
        wind = config_dict['climate']['wind']
        self.climate.wind.station_id = wind['station_id']
        forcing_data_files = infile_dict['forcing_data_files']
        self.climate.wind.output_files = {}
        self.climate.wind.output_files['wind'] = forcing_data_files['wind']


    def _read_yaml_file(self, config_file):
        """Return the dict that results from loading the contents of
        the specified config file as YAML.
        """
        with open(config_file, 'rt') as file_obj:
            return yaml.load(file_obj.read())


    def _read_SOG_infile(self, infile):
        """Placeholder for method that will read data from SOG infile.
        """
        infile_dict = {
            'forcing_data_files': {
                'air_temperature': 'YVR_air_temperature',
                'relative_humidity': 'YVR_relative_humidity',
                'wind': 'Sandheads_wind',
            },
        }
        return infile_dict


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
