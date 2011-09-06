"""Meteorolgical forcing data processing module for SoG-bloomcast project.
"""
from __future__ import absolute_import
# Standard library:
from contextlib import nested
import logging
# Bloomcast:
from utils import Config
from utils import get_climate_data


log = logging.getLogger(__name__)


def run():
    """
    """
    config = Config()
    data = get_climate_data(config, 'meteo')
    context_mgr = nested(
        open('YVR_air_temperature', 'w'),
        open('YVR_relative_humidity', 'w'),
    )
    with context_mgr as file_objs:
        files = {
            'temperature': file_objs[0],
            'humidity': file_objs[1],
        }
        process_data(config, data, files)


def process_data(config, data, files):
    """Process data from XML data records to forcing data files in the
    format that SOG expects.
    """
    data_readers = {
        'temperature': read_temperature,
        'humidity': read_humidity,
    }
    day = '1'
    hourlies = {}
    data_day = {}
    for qty in data_readers.keys():
        hourlies[qty] = []
        data_day[qty] = '1'
    for record in data:
        for qty in data_readers.keys():
            reader = data_readers[qty]
            if record.get('day') != day and hourlies[qty]:
                write_line(config, record, data_day[qty], hourlies[qty], files[qty])
                day = record.get('day')
                hourlies[qty] = [reader(record)]
            else:
                data_day[qty] = record.get('day')
                try:
                    hourlies[qty].append(reader(record))
                except TypeError:
                    return


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


def write_line(config, record, data_day, hourlies, file_obj):
    """
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
    run()
