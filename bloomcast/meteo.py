"""Meteorolgical forcing data processing module for SoG-bloomcast project.
"""
from __future__ import absolute_import
# Standard library:
import logging
import sys
# Bloomcast:
from utils import ClimateDataProcessor
from utils import Config


### TODO: Configure email logger for unrecognized weather descriptions
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)


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


    def write_line(self, record, data_day, hourlies, file_obj):
        """Write a line of data to the specified forcing data file object
        in the format expected by SOG.

        Each line starts with 5 integers:

        * Station ID (not used by SOG; set to EC web site station id)
        * Year
        * Month
        * Day
        * Quantity ID (not used by SOG; set to 42)

        24 hourly values for the data quanity follow expressed as floats
        with 1 decimal place.
        """
        line = (
            '{station_id} {year} {month} {day} 42'
            .format(
                station_id=self.config.climate.meteo.station_id,
                year=record.get('year'),
                month=record.get('month'),
                day=data_day,
            ))
        for value in hourlies:
            line += ' {0:.1f}'.format(value)
        print >> file_obj, line


def run(config_file):
    """
    """
    config = Config()
    config.load_config(config_file)
    meteo = MeteoProcessor(config)
    file_objs = {}
    contexts = []
    for qty in config.climate.meteo.quantities:
        file_objs[qty] = open(config.climate.meteo.output_files[qty], 'wt')
        contexts.append(file_objs[qty])
    meteo.get_climate_data('meteo')
    for qty in config.climate.meteo.quantities:
        meteo.process_data(qty)
        log.debug('{0} {1}'.format(qty, meteo.hourlies[qty][-1]))


if __name__ == '__main__':
    run(sys.argv[1])
