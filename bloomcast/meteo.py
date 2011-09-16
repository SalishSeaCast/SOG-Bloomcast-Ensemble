"""Meteorolgical forcing data processing module for SoG-bloomcast project.
"""
from __future__ import absolute_import
# Standard library:
from contextlib import nested
import logging
import sys
# Bloomcast:
from utils import Config
from utils import get_climate_data


log = logging.getLogger(__name__)


def run(config_file):
    """
    """
    config = Config()
    config.load_config(config_file)
    data = get_climate_data(config, 'meteo')
    data_readers = (
        read_temperature,
        read_humidity,
    )
    context_mgr = nested(
        open('YVR_air_temperature', 'w'),
        open('YVR_relative_humidity', 'w'),
    )
    with context_mgr as file_objs:
        for reader, file_obj in zip(data_readers, file_objs):
            process_data(config, data, reader, file_obj)


def read_temperature(record):
    """Read air temperature from XML data object.

    SOG expects air temperature to be in 10ths of degrees Celcius due
    to legacy data formating of files from Environment Canada.
    """
    return float(record.find('temp').text) * 10


def read_humidity(record):
    """Read relative humidity from XML data object.
    """
    return float(record.find('relhum').text)


def process_data(config, data, reader, file_obj):
    """Process data from XML data records to a forcing data file in
    the format that SOG expects.
    """
    day = '1'
    hourlies = []
    data_day = '1'
    for record in data:
        if record.get('day') != day and hourlies:
            write_line(config, record, data_day, hourlies, file_obj)
            day = record.get('day')
            hourlies = [reader(record)]
        else:
            data_day = record.get('day')
            try:
                hourlies.append(reader(record))
            except TypeError:
                return


def write_line(config, record, data_day, hourlies, file_obj):
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
            station_id=config.climate.meteo.station_id,
            year=record.get('year'),
            month=record.get('month'),
            day=data_day,
        ))
    for value in hourlies:
        line += ' {0:.1f}'.format(value)
    print >> file_obj, line


if __name__ == '__main__':
    run(sys.argv[1])
