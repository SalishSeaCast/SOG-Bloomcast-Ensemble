# Copyright 2011-2021 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Special use script to generate an hourly cloud fraction forcing data file
that is readable by SOG-code/forcing.f90 for a range of years.

Code from other bloomcast modules is repeated here rather than implementing
an API in bloomcast to support this use.

.. note::

   This script requires a cloud fraction mapping file as generated by
   cf_analysis.py.
"""
from cStringIO import StringIO
from datetime import (
    date,
    datetime,
)
import logging
from xml.etree import cElementTree as ElementTree
import requests
import yaml


EC_URL = "http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html"
START_YEAR = 2002
END_YEAR = 2012
STATION_ID = 889  # YVR
MAPPING_FILE = "cloud_fraction_mapping.yaml"
HOURLY_FILE_ROOT = "cf_hourly_yvr"


root_log = logging.getLogger()
log = logging.getLogger("cf_hourlies")
logging.basicConfig(level=logging.DEBUG)
formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
console = logging.StreamHandler()
console.setFormatter(formatter)
log.addHandler(console)
disk = logging.FileHandler("cf_hourlies.log", mode="w")
disk.setFormatter(formatter)
log.addHandler(disk)
root_log.addHandler(disk)
log.propagate = False


with open(MAPPING_FILE, "rt") as f:
    mapping = yaml.safe_load(f.read())


def run():
    data_months = (
        date(year, month, 1)
        for year in range(START_YEAR, END_YEAR + 1)
        for month in range(1, 13)
    )
    request_params = {
        "timeframe": 1,  # Daily
        "Prov": "BC",
        "format": "xml",
        "StationID": 889,  # YVR
        "Day": 1,
    }
    data = []
    for data_month in data_months:
        ec_data = get_EC_data(data_month, request_params)
        for record in ec_data.findall("stationdata"):
            parts = [record.get(part) for part in "year month day hour".split()]
            timestamp = datetime(*map(int, parts))
            data.append((timestamp, read_cloud_fraction(timestamp, record)))
        patch_data(data)
    hourly_file_name = "{0}_{1}_{2}".format(HOURLY_FILE_ROOT, START_YEAR, END_YEAR)
    with open(hourly_file_name, "wt") as hourly_file:
        hourly_file.writelines(format_data(data))


def get_EC_data(data_month, request_params):
    request_params.update(
        {
            "Year": data_month.year,
            "Month": data_month.month,
        }
    )
    response = requests.get(EC_URL, params=request_params)
    log.info("got meteo data for {0:%Y-%m}".format(data_month))
    tree = ElementTree.parse(StringIO(response.content))
    ec_data = tree.getroot()
    return ec_data


def read_cloud_fraction(timestamp, record):
    weather_desc = record.find("weather").text
    try:
        cloud_fraction = mapping[weather_desc]
    except KeyError:
        if weather_desc is None:
            # None indicates missing data
            cloud_fraction = [None]
        else:
            log.warning(
                "Unrecognized weather description: {0} at {1}; "
                "cloud fraction set to 10".format(weather_desc, timestamp)
            )
            cloud_fraction = [10]
    if len(cloud_fraction) == 1:
        cloud_fraction = cloud_fraction[0]
    else:
        cloud_fraction = cloud_fraction[timestamp.month - 1]
    return cloud_fraction


def patch_data(data):
    """Patch missing data values by interpolation."""
    gap_start = gap_end = None
    for i, value in enumerate(data):
        if value[1] is None:
            gap_start = i if gap_start is None else gap_start
            gap_end = i
            log.debug("data patched for {0[0]}".format(value))
        elif gap_start is not None:
            interpolate_values(data, gap_start, gap_end)
            gap_start = gap_end = None


def interpolate_values(data, gap_start, gap_end):
    """Calculate values for missing data via linear interpolation."""
    last_value = data[gap_start - 1][1]
    next_value = data[gap_end + 1][1]
    delta = (next_value - last_value) / (gap_end - gap_start + 2)
    for i in range(gap_end - gap_start + 1):
        timestamp = data[gap_start + i][0]
        value = last_value + delta * (i + 1)
        data[gap_start + i] = (timestamp, value)


def format_data(data):
    """Generate lines of metorological forcing data in the format
    expected by SOG.

    Each line starts with 5 integers:

    * Station ID (not used by SOG; set to EC web site station id)
    * Year
    * Month
    * Day
    * Quantity ID (not used by SOG; set to 42)

    That is followed by 24 hourly cloud fraction values
    expressed as floats with 2 decimal place.
    """
    for i in range(len(data) / 24):
        item = data[i * 24 : (i + 1) * 24]
        timestamp = item[0][0]
        line = "{0} {1:%Y %m %d} 42".format(STATION_ID, timestamp)
        for hour in item:
            line += " {0:.2f}".format(hour[1])
        line += "\n"
        yield line


if __name__ == "__main__":
    run()
