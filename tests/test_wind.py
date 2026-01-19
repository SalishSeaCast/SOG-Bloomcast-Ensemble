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

"""Unit tests for SoG-bloomcast wind module."""

import datetime
from unittest.mock import (
    Mock,
    patch,
)

import pytest


@pytest.fixture
def wind():
    from bloomcast.wind import WindProcessor

    return WindProcessor(Mock(name="config"))


class TestWindProcessor:
    """Unit tests for WindProcessor object."""

    def test_interpolate_values_1_hour_gap(self, wind):
        """interpolate_values interpolates value for 1 hour gap in data"""
        wind.data["wind"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), (1.0, -2.0)),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), (None, None)),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), (2.0, -1.0)),
        ]
        wind.interpolate_values("wind", 1, 1)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), (1.5, -1.5))
        assert wind.data["wind"][1] == expected

    def test_interpolate_values_2_hour_gap(self, wind):
        """interpolate_values interpolates value for 2 hour gap in data"""
        wind.data["wind"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), (1.0, -2.0)),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), (None, None)),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), (None, None)),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), (2.5, -0.5)),
        ]
        wind.interpolate_values("wind", 1, 2)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), (1.5, -1.5))
        assert wind.data["wind"][1] == expected
        expected = (datetime.datetime(2011, 9, 25, 11, 0, 0), (2.0, -1.0))
        assert wind.data["wind"][2] == expected

    def test_interpolate_values_gap_gt_11_hr_logs_warning(self, wind):
        """wind data gap >11 hr generates warning log message"""
        wind.data["wind"] = [(datetime.datetime(2011, 9, 25, 0, 0, 0), (1.0, -2.0))]
        wind.data["wind"].extend(
            [
                (datetime.datetime(2011, 9, 25, 1 + i, 0, 0), (None, None))
                for i in range(15)
            ]
        )
        wind.data["wind"].append(
            (datetime.datetime(2011, 9, 25, 16, 0, 0), (1.0, -2.0))
        )
        with patch("bloomcast.wind.log", Mock()) as mock_log:
            wind.interpolate_values("wind", gap_start=1, gap_end=15)
            mock_log.warning.assert_called_once_with(
                "A wind forcing data gap > 11 hr starting at 2011-09-25 01:00 "
                "has been patched by linear interpolation"
            )

    def test_format_data(self, wind):
        """format_data generator returns formatted forcing data file line"""
        wind.data["wind"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), (1.0, 2.0)),
        ]
        line = next(wind.format_data())
        assert line == "25 09 2011 9.0 1.000000 2.000000\n"
