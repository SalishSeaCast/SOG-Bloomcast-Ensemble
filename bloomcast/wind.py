"""Wind forcing data processing module for SoG-bloomcast project.

Monitor Sandheads wind data on Environment Canada site to determine
what the lag is between the current date and the most recent full
day's data.
"""
from __future__ import absolute_import
# Standard library:
from datetime import datetime
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
    data = get_climate_data(config, 'wind')
    with open('Sandheads_wind', 'w') as file_obj:
        process_data(config, data, read_wind_velocity, write_line, file_obj)
    data.reverse()
    for record in data:
        if record.find('windspd').text:
            latest_data = '{year}-{month}-{day} {hour}:{minute} {speed}'.format(
                speed=record.find('windspd').text, **record.attrib)
            break
    print (
        'At {0:%Y-%m-%d %H:%M} the lastest available wind data was {1}'
        .format(datetime.now(), latest_data))


def read_wind_velocity(record):
    """
    """
    return float(record.find('windspd').text)


def process_data(config, data, reader, writer, file_obj):
    """Process data from XML data records to a forcing data file in
    the format that SOG expects.
    """
    day = '1'
    hourlies = []
    data_day = '1'
    for record in data:
        if record.get('day') != day and hourlies:
            writer(config, record, data_day, hourlies, file_obj)
            day = record.get('day')
            hourlies = [reader(record)]
        else:
            data_day = record.get('day')
            try:
                hourlies.append(reader(record))
            except TypeError:
                return


def write_line(config, record, data_day, hourlies, file_obj):
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


if __name__ == '__main__':
    run(sys.argv[1])
