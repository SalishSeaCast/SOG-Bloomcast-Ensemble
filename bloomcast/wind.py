"""Wind forcing data processing module for SoG-bloomcast project.

Copyright 2011-2014 Doug Latornell and The University of British Columbia

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging
import math
import sys
from .utils import (
    ClimateDataProcessor,
    Config,
)


log = logging.getLogger('bloomcast.wind')


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
        self.raw_data = []
        for data_month in self._get_data_months():
            self.get_climate_data('wind', data_month)
            log.debug('got wind data for {0:%Y-%m}'.format(data_month))
        self.process_data('wind')
        log.debug('latest wind {0}'.format(self.data['wind'][-1]))
        data_date = self.data['wind'][-1][0].date()
        output_file = self.config.climate.wind.output_files['wind']
        with open(output_file, 'wt') as file_obj:
            file_obj.writelines(self.format_data())
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
        except ValueError:
            if speed == 0:
                return 0, 0
            else:
                raise
        # Convert speed and direction to u and v components
        radian_direction = math.radians(direction)
        u_wind = speed * math.sin(radian_direction)
        v_wind = speed * math.cos(radian_direction)
        # Rotate components to align u direction with Strait
        strait_heading = math.radians(305)
        cross_wind = (
            u_wind * math.cos(strait_heading)
            - v_wind * math.sin(strait_heading))
        along_wind = (
            u_wind * math.sin(strait_heading)
            + v_wind * math.cos(strait_heading))
        # Resolve atmosphere/ocean direction difference in favour of
        # oceanography
        cross_wind = -cross_wind
        along_wind = -along_wind
        return cross_wind, along_wind

    def _valuegetter(self, data_item):
        """Return the along-strait wind velocity component.
        """
        return data_item[0]

    def interpolate_values(self, qty, gap_start, gap_end):
        """Calculate values for missing data via linear interpolation.

        Data gaps that exceed 11 hours are to be patched but also
        reported via email.
        """
        gap_hours = gap_end - gap_start + 1
        if gap_hours > 11:
            log.warning(
                'A wind forcing data gap > 11 hr starting at '
                '{0:%Y-%m-%d %H:00} has been patched by linear interpolation'
                .format(self.data[qty][gap_start][0]))
        last_cross_wind, last_along_wind = self.data[qty][gap_start - 1][1]
        next_cross_wind, next_along_wind = self.data[qty][gap_end + 1][1]
        delta_cross_wind = (
            (next_cross_wind - last_cross_wind) / (gap_hours + 1))
        delta_along_wind = (
            (next_along_wind - last_along_wind) / (gap_hours + 1))
        for i in range(gap_end - gap_start + 1):
            timestamp = self.data[qty][gap_start + i][0]
            cross_wind = last_cross_wind + delta_cross_wind * (i + 1)
            along_wind = last_along_wind + delta_along_wind * (i + 1)
            self.data[qty][gap_start + i] = (
                timestamp, (cross_wind, along_wind))

    def format_data(self):
        """Generate lines of wind forcing data in the format expected
        by SOG.

        Each line starts with 3 integers:

        * Day
        * Month
        * Year

        That is followed by 3 floats:

        * Hour
        * Cross-strait wind component
        * Along-strait wind component
        """
        for data in self.data['wind']:
            timestamp = data[0]
            wind = data[1]
            line = '{0:%d %m %Y} {1:.1f} {2:f} {3:f}\n'.format(
                timestamp, timestamp.hour, wind[0], wind[1])
            yield line


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
