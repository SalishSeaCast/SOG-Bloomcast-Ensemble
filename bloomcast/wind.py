"""Wind forcing data processing module for SoG-bloomcast project.

Monitor Sandheads wind data on Environment Canada site to determine
what the lag is between the current date and the most recent full
day's data.
"""
from __future__ import absolute_import
# Standard library:
from datetime import datetime
import logging
# Bloomcast:
from utils import Config
from utils import get_climate_data


log = logging.getLogger(__name__)


def run():
    """
    """
    config = Config()
    data = get_climate_data(config, 'wind')
    data.reverse()
    for record in data:
        if record.find('windspd').text:
            latest_data = '{year}-{month}-{day} {hour}:{minute} {speed}'.format(
                speed=record.find('windspd').text, **record.attrib)
            break
    print (
        'At {0:%Y-%m-%d %H:%M} the lastest available wind data was {1}'
        .format(datetime.now(), latest_data))


if __name__ == '__main__':
    run()
