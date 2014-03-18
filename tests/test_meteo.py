# Copyright 2011-2014 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for SoG-bloomcast meteo module.
"""
import datetime

from unittest.mock import Mock
import pytest


@pytest.fixture
def meteo():
    from bloomcast.meteo import MeteoProcessor
    return MeteoProcessor(Mock(name='config'))


@pytest.mark.usefixture('meteo')
class TestMeteoProcessor():
    """Unit tests for MeteoProcessor object.
    """
    def test_read_cloud_fraction_single_avg(self, meteo):
        """read_cloud_fraction returns expected value for single avg CF list
        """
        meteo.config.climate.meteo.cloud_fraction_mapping = {
            'Drizzle': [9.9675925925925934],
        }
        record = Mock(name='record')
        record.find().text = 'Drizzle'
        cloud_faction = meteo.read_cloud_fraction(record)
        assert cloud_faction == 9.9675925925925934

    def test_read_cloud_fraction_monthly_avg(self, meteo):
        """read_cloud_fraction returns expected value for monthly avg CF list
        """
        meteo.config.climate.meteo.cloud_fraction_mapping = {
            'Fog': [
                9.6210045662100452, 9.3069767441860467, 9.5945945945945947,
                9.5, 9.931034482758621, 10.0, 9.7777777777777786,
                9.6999999999999993, 7.8518518518518521, 8.9701492537313428,
                9.2686980609418281, 9.0742358078602621]
        }
        record = Mock(name='record')
        record.find().text = 'Fog'

        def mock_timestamp_data(part):
            parts = {'year': 2012, 'month': 4, 'day': 1, 'hour': 12}
            return parts[part]
        record.get = mock_timestamp_data
        cloud_faction = meteo.read_cloud_fraction(record)
        assert cloud_faction == 9.5

    def test_format_data(self, meteo):
        """format_data generator returns formatted forcing data file line
        """
        meteo.config.climate.meteo.station_id = '889'
        meteo.data['air_temperature'] = [
            (datetime.datetime(2011, 9, 25, i, 0, 0), 215.0)
            for i in range(24)]
        line = next(meteo.format_data('air_temperature'))
        assert line == '889 2011 09 25 42' + ' 215.00' * 24 + '\n'
