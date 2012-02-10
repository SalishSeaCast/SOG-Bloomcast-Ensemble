"""Meteorolgical forcing data processing module for SoG-bloomcast project.
"""
# Standard library:
from contextlib import nested
from datetime import date
import logging
import sys
# Bloomcast:
from utils import ClimateDataProcessor
from utils import Config


log = logging.getLogger('bloomcast.meteo')


class MeteoProcessor(ClimateDataProcessor):
    """Meteorological forcing data processor.
    """
    def __init__(self, config):
        data_readers = {
            'air_temperature': self.read_temperature,
            'relative_humidity': self.read_humidity,
            'cloud_fraction': self.read_cloud_fraction,
        }
        super(MeteoProcessor, self).__init__(config, data_readers)

    def make_forcing_data_files(self):
        """Get the meteorological forcing data from the Environment
        Canada web service, process it to extract quantity values from
        the XML download, trim incomplete days from the end, patch
        missing values, and write the data to files in the format that
        SOG expects.
        """
        file_objs = {}
        contexts = []
        for qty in self.config.climate.meteo.quantities:
            output_file = self.config.climate.meteo.output_files[qty]
            file_objs[qty] = open(output_file, 'wt')
            contexts.append(file_objs[qty])
        self.raw_data = []
        for data_month in self._get_data_months():
            self.get_climate_data('meteo', data_month)
            log.debug('got meteo data for {0:%Y-%m}'.format(data_month))
        with nested(*contexts):
            for qty in self.config.climate.meteo.quantities:
                self.process_data(qty, end_date=self.config.data_date)
                log.debug('latest {0} {1}'.format(qty, self.data[qty][-1]))
                file_objs[qty].writelines(self.format_data(qty))

    def read_temperature(self, record):
        """Read air temperature from XML data object.

        SOG expects air temperature to be in 10ths of degrees Celcius due
        to legacy data formating of files from Environment Canada.
        """
        temperature = record.find('temp').text
        try:
            temperature = float(temperature) * 10
        except TypeError:
            # None indicates missing data
            pass
        return temperature

    def read_humidity(self, record):
        """Read relative humidity from XML data object.
        """
        humidity = record.find('relhum').text
        try:
            humidity = float(humidity)
        except TypeError:
            # None indicates missing data
            pass
        return humidity

    def read_cloud_fraction(self, record):
        """Read weather description from XML data object and transform
        it to cloud fraction via Susan's heuristic mapping.
        """
        weather_desc = record.find('weather').text
        mapping = self.config.climate.meteo.cloud_fraction_mapping
        try:
            cloud_fraction = mapping[weather_desc]
        except KeyError:
            if weather_desc is None:
                # None indicates missing data
                cloud_fraction = None
            else:
                log.warning(
                    'Unrecognized weather description: {0}; '
                    'cloud fraction set to 10'.format(weather_desc))
                cloud_fraction = 10
        return cloud_fraction

    def format_data(self, qty):
        """Generate lines of metorological forcing data in the format
        expected by SOG.

        Each line starts with 5 integers:

        * Station ID (not used by SOG; set to EC web site station id)
        * Year
        * Month
        * Day
        * Quantity ID (not used by SOG; set to 42)

        That is followed by 24 hourly values for the data quanity
        follow expressed as floats with 1 decimal place.
        """
        for i in xrange(len(self.data[qty]) / 24):
            data = self.data[qty][i * 24:(i + 1) * 24]
            timestamp = data[0][0]
            line = '{0} {1:%Y %m %d} 42'.format(
                self.config.climate.meteo.station_id, timestamp)
            for hour in data:
                line += ' {0:.1f}'.format(hour[1])
            line += '\n'
            yield line


def run(config_file):
    """Process meteorological forcing data into SOG forcing data
    files by running the MeteoProcessor independent of bloomcast.
    """
    logging.basicConfig(level=logging.DEBUG)
    config = Config()
    config.load_config(config_file)
    config.data_date = date.today()
    meteo = MeteoProcessor(config)
    meteo.make_forcing_data_files()


if __name__ == '__main__':
    run(sys.argv[1])
