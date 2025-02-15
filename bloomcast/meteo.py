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

"""Meteorolgical forcing data processing module for SoG-bloomcast project."""
import logging
import sys
import contextlib

import arrow

from .utils import (
    ClimateDataProcessor,
    Config,
)


log = logging.getLogger("bloomcast.meteo")


class MeteoProcessor(ClimateDataProcessor):
    """Meteorological forcing data processor."""

    def __init__(self, config):
        data_readers = {
            "air_temperature": self.read_temperature,
            "relative_humidity": self.read_humidity,
            "cloud_fraction": self.read_cloud_fraction,
        }
        super(MeteoProcessor, self).__init__(config, data_readers)

    def make_forcing_data_files(self):
        """Get the meteorological forcing data from the Environment
        Canada web service, process it to extract quantity values from
        the XML download, trim incomplete days from the end, patch
        missing values, and write the data to files in the format that
        SOG expects.
        """
        file_objs = {}
        contexts = []
        for qty in self.config.climate.meteo.quantities:
            output_file = self.config.climate.meteo.output_files[qty]
            file_objs[qty] = open(output_file, "wt")
            contexts.append(file_objs[qty])
        self.raw_data = []
        for data_month in self._get_data_months():
            self.get_climate_data("meteo", data_month)
            log.debug("got meteo data for {0:%Y-%m}".format(data_month))
        with contextlib.ExitStack() as stack:
            files = dict(
                [
                    (
                        qty,
                        stack.enter_context(
                            open(self.config.climate.meteo.output_files[qty], "wt")
                        ),
                    )
                    for qty in self.config.climate.meteo.quantities
                ]
            )
            for qty in self.config.climate.meteo.quantities:
                self.process_data(qty, end_date=self.config.data_date)
                log.debug("latest {0} {1}".format(qty, self.data[qty][-1]))
                files[qty].writelines(self.format_data(qty))

    def read_temperature(self, record):
        """Read air temperature from XML data object.

        SOG expects air temperature to be in 10ths of degrees Celcius due
        to legacy data formating of files from Environment Canada.
        """
        temperature = record.find("temp").text
        try:
            temperature = float(temperature) * 10
        except TypeError:
            # None indicates missing data
            pass
        return temperature

    def read_humidity(self, record):
        """Read relative humidity from XML data object."""
        humidity = record.find("relhum").text
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
        weather_desc = record.find("weather").text
        mapping = self.config.climate.meteo.cloud_fraction_mapping
        try:
            cloud_fraction = mapping[weather_desc]
        except KeyError:
            if weather_desc is None or weather_desc == "NA":
                # None indicates missing data
                cloud_fraction = [None]
            else:
                log.warning(
                    "Unrecognized weather description: {0} at {1}; "
                    "cloud fraction set to 10".format(
                        weather_desc, self.read_timestamp(record)
                    )
                )
                cloud_fraction = [10]
        if len(cloud_fraction) == 1:
            cloud_fraction = cloud_fraction[0]
        else:
            timestamp = self.read_timestamp(record)
            cloud_fraction = cloud_fraction[timestamp.month - 1]
        return cloud_fraction

    def format_data(self, qty):
        """Generate lines of metorological forcing data in the format
        expected by SOG.

        Each line starts with 5 integers:

        * Station ID (not used by SOG; set to EC web site station id)
        * Year
        * Month
        * Day
        * Quantity ID (not used by SOG; set to 42)

        That is followed by 24 hourly values for the data quanity
        follow expressed as floats with 2 decimal place.
        """
        for i in range(len(self.data[qty]) // 24):
            data = self.data[qty][i * 24 : (i + 1) * 24]
            timestamp = data[0][0]
            line = "{0} {1:%Y %m %d} 42".format(
                self.config.climate.meteo.station_id, timestamp
            )
            for j, hour in enumerate(data):
                try:
                    line += " {0:.2f}".format(hour[1])
                    if qty == "cloud_fraction":
                        last_cf = hour[1] or data[j - 1][1]
                except TypeError:
                    # This is a hack to work around NavCanada not reporting
                    # a YVR weather description (from which we get cloud
                    # fraction) at 23:00 when there is no precipitation
                    # happening. The upshot is that the final few values
                    # in the dataset can be None, so we persist the last valid
                    # value for that very special case, and log a warning.
                    if qty == "cloud_fraction":
                        line += " {0:.2f}".format(last_cf)
                        log.warning(
                            f"missing cloud fraction value {hour} "
                            f"filled with {last_cf}"
                        )
                    else:
                        raise
            line += "\n"
            yield line


def run(config_file):
    """Process meteorological forcing data into SOG forcing data
    files by running the MeteoProcessor independent of bloomcast.
    """
    logging.basicConfig(level=logging.DEBUG)
    config = Config()
    config.load_config(config_file)
    config.data_date = arrow.now().floor("day")
    meteo = MeteoProcessor(config)
    meteo.make_forcing_data_files()


if __name__ == "__main__":
    run(sys.argv[1])
