"""Utility classes for SoG-bloomcast project.

A collection of classes that are used in other bloomcast modules.
"""
from __future__ import absolute_import
# Standard library:
from datetime import date
from datetime import datetime
from datetime import timedelta
import logging
import re
from StringIO import StringIO
from xml.etree import cElementTree as ElementTree
# HTTP Requests library:
import requests
# YAML library:
import yaml


log = logging.getLogger('bloomcast.' + __name__)


class _Container(object): pass


class Config(object):
    """Placeholder for a config object that reads values from a file.
    """
    def load_config(self, config_file):
        """Load values from the specified config file into the
        attributes of the Config object.
        """
        config_dict = self._read_yaml_file(config_file)
        self._load_logging_config(config_dict)
        self.infile = config_dict['infile']
        infile_dict = self._read_SOG_infile()
        self.run_start_date = infile_dict['run_start_date']
        self.climate = _Container()
#         self.climate.__dict__.update(config_dict['climate'])
        for attr in 'url params'.split():
            setattr(self.climate, attr, config_dict['climate'][attr])
        self._load_meteo_config(config_dict, infile_dict)
        self._load_wind_config(config_dict, infile_dict)
        self.rivers = _Container()
#         self.rivers.__dict__.update(config_dict['rivers'])
        for attr in 'disclaimer_url accept_disclaimer data_url params'.split():
            setattr(self.rivers, attr, config_dict['rivers'][attr])
        self._load_rivers_config(config_dict, infile_dict)


    def _load_logging_config(self, config_dict):
        """Load Config values for logging.
        """
        self.logging = _Container()
#         self.logging.__dict__.update(config_dict['logging'])
        for attr in 'debug toaddrs use_test_smtpd'.split():
            setattr(self.logging, attr, config_dict['logging'][attr])


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
        self.rivers.major = _Container()
        major_river = config_dict['rivers']['major']
        self.rivers.major.station_id = major_river['station_id']
        self.rivers.minor = _Container()
        minor_river = config_dict['rivers']['minor']
        self.rivers.minor.station_id = minor_river['station_id']
        forcing_data_files = infile_dict['forcing_data_files']
        self.rivers.output_files = {}
        for river in 'major minor'.split():
            self.rivers.output_files[river] = forcing_data_files[river+'_river']


    def _read_yaml_file(self, config_file):
        """Return the dict that results from loading the contents of
        the specified config file as YAML.
        """
        with open(config_file, 'rt') as file_obj:
            return yaml.load(file_obj.read())


    def _read_SOG_infile(self):
        """Return a dict of selected values read from the SOG infile.
        """
        # Mapping between SOG infile keys and Config object attribute
        # names for forcing data files
        forcing_data_files = {
            'wind': 'wind',
            'air temp': 'air_temperature',
            'humidity': 'relative_humidity',
            'cloud': 'cloud_fraction',
            'major river': 'major_river',
            'minor river': 'minor_river',
        }
        infile_dict = {'forcing_data_files': {}}
        # Keys, values and comments are separated by "+whitespace
        sep = re.compile(r'"\s')
        with open(self.infile, 'rt') as infile:
            for i, line in enumerate(infile):
                if line.startswith('\n') or line.startswith('!'):
                    continue
                split_line = sep.split(line)
                infile_key = split_line[0].strip('"')
                if infile_key in forcing_data_files:
                    result_key = forcing_data_files[infile_key]
                    value = self._get_SOG_infile_value(
                        split_line, infile, sep, i)
                    infile_dict['forcing_data_files'][result_key] = value
                elif infile_key == 'init datetime':
                    result_key = 'run_start_date'
                    value = self._get_SOG_infile_value(
                        split_line, infile, sep, i)
                    infile_dict[result_key] = datetime.strptime(
                        value, '%Y-%m-%d %H:%M:%S')
        return infile_dict


    def _get_SOG_infile_value(self, split_line, infile, sep, i):
        """Return the value from a SOG infile key, value, comment
        triplet that may be split over multiple lines.
        """
        value = split_line[1].strip().strip('"').rstrip('\n')
        if not value:
            # Value on line after key
            value = sep.split(infile[i+1])[0].strip().strip('"')
        return value


class ForcingDataProcessor(object):
    """Base class for forcing data processors.
    """
    def __init__(self, config):
        self.config = config
        self.data = {}


    def _valuegetter(self, data_item):
        """Return a data value.

        Override this method if data is stored in hourlies list in a
        type or data structure other than a simple value; e.g. wind
        data is stored as a tuple of components.
        """
        return data_item


    def _trim_data(self, qty):
        """Trim empty and incomplete days from the end of the data
        data list.

        Days without any data are deleted first, then days without
        data at 23:00 are deleted.
        """
        while self.data[qty]:
            if any([self._valuegetter(data[1])
                    for data in self.data[qty][-24:]]):
                break
            else:
                del self.data[qty][-24:]
        else:
            raise ValueError('Forcing data list is empty')
        while self.data[qty]:
            if self._valuegetter(self.data[qty][-1][1]) is None:
                del self.data[qty][-24:]
            else:
                break
        else:
            raise ValueError('Forcing data list is empty')


    def patch_data(self, qty):
        """Patch missing data values by interpolation.
        """
        gap_start = gap_end = None
        for i, data in enumerate(self.data[qty]):
            if self._valuegetter(data[1]) is None:
                gap_start = i if gap_start is None else gap_start
                gap_end = i
            elif gap_start is not None:
                self.interpolate_values(qty, gap_start, gap_end)
                gap_start = gap_end = None


    def interpolate_values(self, qty, gap_start, gap_end):
        """Calculate values for missing data via linear interpolation.

        Override this method if:

        * Data is stored in data list in a type or data structure
          other than a simple value; e.g. wind data is stored as a
          tuple of components.

        * Data requires special handling for interpolation; e.g. wind
          data gaps that exceed 11 hours are to be patched but also
          reported via email.
        """
        last_value = self.data[qty][gap_start - 1][1]
        next_value = self.data[qty][gap_end + 1][1]
        delta = (next_value - last_value) / (gap_end - gap_start + 2)
        for i in xrange(gap_end - gap_start + 1):
            timestamp = self.data[qty][gap_start + i][0]
            value = last_value + delta * (i + 1)
            self.data[qty][gap_start + i] = (timestamp, value)


class ClimateDataProcessor(ForcingDataProcessor):
    """Climate forcing data processor base class.
    """
    def __init__(self, config, data_readers):
        self.data_readers = data_readers
        super(ClimateDataProcessor, self).__init__(config)


    def get_climate_data(self, data_type):
        """Return a list of XML objects containing the specified type of
        climate data.

        The XML objects are :class:`ElementTree` subelement instances.
        """
        params = self.config.climate.params
        params['StationID'] = getattr(self.config.climate, data_type).station_id
        params.update(self._date_params())
        response = requests.get(self.config.climate.url, params=params)
        tree = ElementTree.parse(StringIO(response.content))
        root = tree.getroot()
        self.raw_data = root.findall('stationdata')


    def _date_params(self, data_month=None):
        """Return a dict of the components of the specified data month
        date.

        The keys are the component names in the format required for
        requests to the :kbd:`climate.weatheroffice.gc.ca` site.

        The values are the data month date components as integers,
        with the day set to 1.

        The value of data_month defaults to yesterday's date.
        """
        if not data_month:
            data_month = date.today() - timedelta(days=1)
        params = {
            'Year': data_month.year,
            'Month': data_month.month,
            'Day': 1,
        }
        return params.iteritems()


    def process_data(self, qty, end_date=date.today()):
        """Process data from XML data records to a list of hourly
        timestamps and data values.
        """
        reader = self.data_readers[qty]
        self.data[qty] = []
        for record in self.raw_data:
            timestamp = self.read_timestamp(record)
            if timestamp.date() > end_date:
                break
            self.data[qty].append((timestamp, reader(record)))
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
