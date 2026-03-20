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

"""Unit tests for SoG-bloomcast rivers module."""

import datetime
from unittest.mock import (
    Mock,
    patch,
)

import arrow
import bs4
import pytest


@pytest.fixture
def processor():
    from bloomcast.rivers import RiversProcessor

    return RiversProcessor(Mock(name="config"))


class TestRiverProcessor:
    """Unit tests for RiverProcessor object."""

    def test_date_range(self, processor):
        """_date_range returns the expected date range"""
        processor.config.data_date = arrow.get(2026, 3, 15)
        expected = (
            arrow.get(2025, 1, 1),
            arrow.get(2026, 3, 15),
        )
        assert processor._date_range(2025) == expected

    def test_process_data_1_row(self, processor):
        """process_data produces expected result for 1 row of data"""
        processor.raw_data = ["2026 3 20 4.200000e+03"]
        processor.process_data("major")
        assert processor.data["major"] == [(datetime.date(2026, 3, 20), 4200.0)]

    def test_process_data_minor_river_scaling(self, processor):
        """process_data produces the expected result for scaled minor river
        re: 25-Sep-2020 failure of Englishman River gauge data stream and replacement of it
        with scaled Nanaimo River values for 2021 predictions
        """
        processor.raw_data = ["2026 3 20 9.959159e+00"]
        processor.process_data("minor", 0.351)
        assert processor.data["minor"] == [
            (datetime.date(2026, 3, 20), 3.4956648089999995)
        ]

    def test_process_data_2_rows_2_days(self, processor):
        """process_data produces the expected result for 2 rows of data from 2 days"""
        processor.raw_data = [
            "2026 3 19 4.200000e+03",
            "2026 3 20 4.400000e+03",
        ]
        processor.process_data("major")
        expected = [
            (datetime.date(2026, 3, 19), 4200.0),
            (datetime.date(2026, 3, 20), 4400.0),
        ]
        assert processor.data["major"] == expected

    def test_format_data(self, processor):
        """format_data generator returns formatted forcing data file line"""
        processor.data["major"] = [(datetime.date(2011, 9, 27), 4200.0)]
        line = next(processor.format_data("major"))
        assert line == "2011 09 27 4.200000e+03\n"

    def test_patch_data_1_day_gap(self, processor):
        """patch_data correctly flags 1 day gap in data for interpolation"""
        processor.data["major"] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 25), 4500.0),
        ]
        processor.interpolate_values = Mock(name="interpolate_values")
        with patch("bloomcast.rivers.log") as mock_log:
            processor.patch_data("major")
        expected = (datetime.date(2011, 10, 24), None)
        assert processor.data["major"][1] == expected
        expected = [
            (("major river data patched for 2011-10-24",),),
            (
                (
                    "1 major river data values patched; "
                    "see debug log on disk for details",
                ),
            ),
        ]
        assert mock_log.debug.call_args_list == expected
        processor.interpolate_values.assert_called_once_with("major", 1, 1)

    def test_patch_data_2_day_gap(self, processor):
        """patch_data correctly flags 2 day gap in data for interpolation"""
        processor.data["major"] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 26), 4600.0),
        ]
        processor.interpolate_values = Mock(name="interpolate_values")
        with patch("bloomcast.rivers.log") as mock_log:
            processor.patch_data("major")
        expected = [
            (datetime.date(2011, 10, 24), None),
            (datetime.date(2011, 10, 25), None),
        ]
        assert processor.data["major"][1:3] == expected
        expected = [
            (("major river data patched for 2011-10-24",),),
            (("major river data patched for 2011-10-25",),),
            (
                (
                    "2 major river data values patched; "
                    "see debug log on disk for details",
                ),
            ),
        ]
        assert mock_log.debug.call_args_list == expected
        processor.interpolate_values.assert_called_once_with("major", 1, 2)

    def test_patch_data_2_gaps(self, processor):
        """patch_data correctly flags 2 gaps in data for interpolation"""
        processor.data["major"] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 25), 4500.0),
            (datetime.date(2011, 10, 26), 4500.0),
            (datetime.date(2011, 10, 29), 4200.0),
        ]
        processor.interpolate_values = Mock(name="interpolate_values")
        with patch("bloomcast.rivers.log") as mock_log:
            processor.patch_data("major")
        expected = (datetime.date(2011, 10, 24), None)
        assert processor.data["major"][1] == expected
        expected = [
            (datetime.date(2011, 10, 27), None),
            (datetime.date(2011, 10, 28), None),
        ]
        assert processor.data["major"][4:6] == expected
        expected = [
            (("major river data patched for 2011-10-24",),),
            (("major river data patched for 2011-10-27",),),
            (("major river data patched for 2011-10-28",),),
            (
                (
                    "3 major river data values patched; "
                    "see debug log on disk for details",
                ),
            ),
        ]
        assert mock_log.debug.call_args_list == expected
        expected = [(("major", 1, 1),), (("major", 4, 5),)]
        assert processor.interpolate_values.call_args_list == expected

    def test_interpolate_values_1_day_gap(self, processor):
        """interpolate_values interpolates value for 1 day gap in data"""
        processor.data = {}
        processor.data["major"] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 24), None),
            (datetime.date(2011, 10, 25), 4500.0),
        ]
        processor.interpolate_values("major", 1, 1)
        expected = (datetime.date(2011, 10, 24), 4400.0)
        assert processor.data["major"][1] == expected

    def test_interpolate_values_2_day_gap(self, processor):
        """interpolate_values interpolates value for 2 day gap in data"""
        processor.data = {}
        processor.data["major"] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 24), None),
            (datetime.date(2011, 10, 25), None),
            (datetime.date(2011, 10, 26), 4600.0),
        ]
        processor.interpolate_values("major", 1, 2)
        expected = [
            (datetime.date(2011, 10, 24), 4400.0),
            (datetime.date(2011, 10, 25), 4500.0),
        ]
        assert processor.data["major"][1:3] == expected
