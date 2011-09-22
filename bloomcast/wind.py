"""Wind forcing data processing module for SoG-bloomcast project.

Monitor Sandheads wind data on Environment Canada site to determine
what the lag is between the current date and the most recent full
day's data.
"""
from __future__ import absolute_import
# Standard library:
import logging
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


    def read_wind_velocity(self, record):
        """Read wind velocity from XML data object and transform it to
        along- and cross-strait components.
        """
        speed = record.find('windspd').text
        direction = record.find('winddir').text
        try:
            speed = float(speed)
        except TypeError:
            # None indicates missing data
            pass
        try:
            direction = float(direction) * 10
        except TypeError:
            # None indicates missing data
            pass
        return speed, direction


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
    print 'wind', wind.hourlies['wind'][-1]


if __name__ == '__main__':
    run(sys.argv[1])
