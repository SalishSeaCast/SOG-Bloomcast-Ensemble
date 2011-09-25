"""Wind forcing data processing module for SoG-bloomcast project.
"""
from __future__ import absolute_import
from __future__ import print_function
# Standard library:
import logging
from math import cos
from math import radians
from math import sin
import sys
# Bloomcast:
from utils import ClimateDataProcessor
from utils import Config


log = logging.getLogger(__file__)


class WindProcessor(ClimateDataProcessor):
    """Wind forcing data processor.
    """
    def __init__(self, config):
        data_readers = {'wind': self.read_wind_velocity}
        super(WindProcessor, self).__init__(config, data_readers)


    def make_forcing_data_file(self):
        """Get the wind forcing data from the Environment Canada web
        service, process it to extract it from the XML download, trim
        incomplete days from the end, patch missing values, and write
        the data to a file in the format that SOG expects.

        Return the date of the last day for which data was obtained.
        """
        self.get_climate_data('wind')
        self.process_data('wind')
        log.debug('latest wind {0}'.format(self.hourlies['wind'][-1]))
        data_date = self.hourlies['wind'][-1][0].date()
        output_file = self.config.climate.wind.output_files['wind']
        with open(output_file, 'wt') as file_obj:
            for data in self.hourlies['wind']:
                self.write_line(data, file_obj)
        return data_date


    def read_wind_velocity(self, record):
        """Read wind velocity from XML data object and transform it to
        along- and cross-strait components.
        """
        speed = record.find('windspd').text
        direction = record.find('winddir').text
        try:
            # Convert from km/hr to m/s
            speed = float(speed) * 1000 / (60 * 60)
            # Convert from 10s of degrees to degrees
            direction = float(direction) * 10
        except TypeError:
            # None indicates missing data
            return None, None
        # Convert speed and direction to u and v components
        radian_direction = radians(direction)
        u_wind = speed * sin(radian_direction)
        v_wind = speed * cos(radian_direction)
        # Rotate components to align u direction with Strait
        strait_heading = radians(305)
        cross_wind = u_wind * cos(strait_heading) - v_wind * sin(strait_heading)
        along_wind = u_wind * sin(strait_heading) + v_wind * cos(strait_heading)
        # Resolve atmosphere/ocean direction difference in favour of
        # oceanography
        cross_wind = -cross_wind
        along_wind = -along_wind
        return cross_wind, along_wind


    def _valuegetter(self, data_item):
        """Return the along-strait wind velocity component.
        """
        return data_item[0]


    def write_line(self, data, file_obj):
        """Write a line of data to the specified wind forcing data
        file object in the format expected by SOG.

        Each line starts with 3 integers:

        * Day
        * Month
        * Year

        That is followed by 3 floats:

        * Hour
        * Cross-strait wind component
        * Along-strait wind component
        """
        timestamp = data[0]
        wind = data[1]
        line = '{0:%Y %m %d} {1:.1f} {2:f} {3:f}'.format(
            timestamp, timestamp.hour, wind[0], wind[1])
        print(line, file=file_obj)


def run(config_file):
    """Process meteorological forcing data into SOG forcing data
    files by running the MeteoProcessor independent of bloomcast.
    """
    logging.basicConfig(level=logging.DEBUG)
    config = Config()
    config.load_config(config_file)
    wind = WindProcessor(config)
    wind.make_forcing_data_file()


if __name__ == '__main__':
    run(sys.argv[1])
