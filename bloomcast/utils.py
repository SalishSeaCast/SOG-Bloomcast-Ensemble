"""Utility classes and methods for SoG-bloomcast project.

A collection of classes and module that are used in other bloomcast
modules.
"""
from __future__ import absolute_import
# Standard library:
from datetime import date
from datetime import datetime
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
        self.rivers = _Container()
        for attr in 'url porams'.split():
            setattr(self.rivers, attr, config_dict['rivers'][attr])
        self._load_rivers_config(config_dict, infile_dict)


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


    def _load_rivers_config(self, config_dict, infile_dict):
        """Load Config values for river flows forcing data.
        """
        self.rivers.primary = _Container()
        primary_river = config_dict['rivers']['primary']
        self.rivers.primary.station_id = primary_river['station_id']
        secondary_river = config_dict['rivers']['secondary']
        self.rivers.secondary.station_id = secondary_river['station_id']
        forcing_data_files = infile_dict['forcing_data_files']
        self.rivers.output_files = {}
        for river in 'primary secondary'.split():
            self.rivers.output_files[river] = forcing_data_files[river]


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
                'cloud_fraction': 'YVR_cloud_fraction',
                'wind': 'Sandheads_wind',
            },
        }
        return infile_dict


class ClimateDataProcessor(object):
    """Climate forcing data processor base class.
    """
    def __init__(self, config, data_readers):
        self.config = config
        self.data_readers = data_readers
        self.hourlies = {}


    def get_climate_data(self, data_type):
        """Return a list of XML objects containing the specified type of
        climate data.

        The XML objects are :class:`ElementTree` subelement instances.
        """
        params = self.config.climate.params
        params['StationID'] = getattr(self.config.climate, data_type).station_id
        for key, value in self._date_params():
            params[key] = value
        response = requests.get(self.config.climate.url, params=params)
        tree = ElementTree.parse(StringIO(response.content))
        root = tree.getroot()
        self.data = root.findall('stationdata')


    def _date_params(self):
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


    def process_data(self, qty, end_date=date.today()):
        """Process data from XML data records to a forcing data file in
        the format that SOG expects.
        """
        reader = self.data_readers[qty]
        self.hourlies[qty] = []
        for record in self.data:
            timestamp = self.read_timestamp(record)
            if timestamp.date() > end_date:
                break
            self.hourlies[qty].append((timestamp, reader(record)))
        self._trim_data(qty)
        self.patch_data(qty)


    def read_timestamp(self, record):
        """Read timestamp from XML data object and return it as a
        datetime instance.
        """
        timestamp = datetime(
            int(record.get('year')),
            int(record.get('month')),
            int(record.get('day')),
            int(record.get('hour')),
        )
        return timestamp


    def _valuegetter(self, data_item):
        """Return a data value.

        Override this method if data is stored in hourlies list in a
        type or data structure other than a simple value; e.g. wind
        data is stored as a tuple of components.
        """
        return data_item


    def _trim_data(self, qty):
        """Trim empty and incomplete days from the end of the hourlies
        data list.

        Days without any data are deleted first, then days without
        data at 23:00 are deleted.
        """
        while True:
            if any([self._valuegetter(data[1])
                    for data in self.hourlies[qty][-24:]]):
                break
            else:
                del self.hourlies[qty][-24:]
        while True:
            if self._valuegetter(self.hourlies[qty][-1][1]) is None:
                del self.hourlies[qty][-24:]
            else:
                break


    def patch_data(self, qty):
        """Patch missing data values by interpolation.
        """
        gap_start = gap_end = None
        for i, data in enumerate(self.hourlies[qty]):
            if self._valuegetter(data[1]) is None:
                gap_start = i if gap_start is None else gap_start
                gap_end = i
            elif gap_start is not None:
                self.interpolate_values(qty, gap_start, gap_end)
                gap_start = gap_end = None


    def interpolate_values(self, qty, gap_start, gap_end):
        """Calculate values for missing data via linear interpolation.

        Override this method if:

        * Data is stored in hourlies list in a type or data structure
          other than a simple value; e.g. wind data is stored as a
          tuple of components.

        * Data requires special handling for interpolation; e.g. wind
          data gaps that exceed 11 hours are to be patched but also
          reported via email.
        """
        last_value = self.hourlies[qty][gap_start - 1][1]
        next_value = self.hourlies[qty][gap_end + 1][1]
        delta = (next_value - last_value) / (gap_end - gap_start + 2)
        for i in xrange(gap_end - gap_start + 1):
            timestamp = self.hourlies[qty][gap_start + i][0]
            value = last_value + delta * (i + 1)
            self.hourlies[qty][gap_start + i] = (timestamp, value)
