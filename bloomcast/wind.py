"""Wind forcing data processing module for SoG-bloomcast project.

Monitor Sandheads wind data on Environment Canada site to determine
what the lag is between the current date and the most recent full
day's data.
"""
from __future__ import absolute_import
# Standard library:
import logging
from math import cos
from math import radians
from math import sin
import sys
# Bloomcast:
from utils import ClimateDataProcessor
from utils import Config


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)


class WindProcessor(ClimateDataProcessor):
    """Wind forcing data processor.
    """
    def __init__(self, config):
        data_readers = {'wind': self.read_wind_velocity}
        super(WindProcessor, self).__init__(config, data_readers)


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


    def write_line(self, record, data_day, hourlies, file_obj):
        """
        """
        line = (
            '{day} {month} {year}'
            .format(
                day=data_day,
                month=record.get('month'),
                year=record.get('year'),
        ))
        print >> file_obj, line


def run(config_file):
    """
    """
    config = Config()
    config.load_config(config_file)
    wind = WindProcessor(config)
    wind.get_climate_data('wind')
    wind.process_data('wind')
    config.run_date = wind.hourlies['wind'][-1][0].date()
    log.debug('wind {0}'.format(wind.hourlies['wind'][-1]))


if __name__ == '__main__':
    run(sys.argv[1])
