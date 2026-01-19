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

"""Unit tests for SoG-bloomcast utils module."""

import datetime
from unittest.mock import (
    DEFAULT,
    Mock,
    patch,
)

import pytest


@pytest.fixture
def config():
    from bloomcast.utils import Config

    return Config()


@pytest.fixture(scope="function")
def config_dict():
    config_dict = {
        "get_forcing_data": None,
        "run_SOG": None,
        "SOG_executable": None,
        "html_results": None,
        "ensemble": {
            "base_infile": None,
        },
        "climate": {
            "url": None,
            "params": None,
            "meteo": {
                "station_id": None,
                "quantities": [],
                "cloud_fraction_mapping": None,
            },
            "wind": {"station_id": None},
        },
        "rivers": {
            "disclaimer_url": None,
            "accept_disclaimer": {
                "disclaimer_action": None,
            },
            "data_url": None,
            "params": {
                "mode": None,
                "prm1": None,
            },
            "major": {
                "station_id": None,
            },
            "minor": {"station_id": None, "scale_factor": None},
        },
        "logging": {
            "debug": None,
            "toaddrs": [],
            "use_test_smtpd": None,
        },
        "results": {},
    }
    return config_dict


@pytest.fixture(scope="function")
def infile_dict():
    infile_dict = {
        "run_start_date": datetime.datetime(2011, 11, 11, 12, 33, 42),
        "SOG_timestep": "900",
        "std_phys_ts_outfile": None,
        "user_phys_ts_outfile": None,
        "std_bio_ts_outfile": None,
        "user_bio_ts_outfile": None,
        "std_chem_ts_outfile": None,
        "user_chem_ts_outfile": None,
        "profiles_outfile_base": None,
        "user_profiles_outfile_base": None,
        "halocline_outfile": None,
        "Hoffmueller_profiles_outfile": None,
        "user_Hoffmueller_profiles_outfile": None,
        "forcing_data_files": {
            "air_temperature": None,
            "relative_humidity": None,
            "cloud_fraction": None,
            "wind": None,
            "major_river": None,
            "minor_river": None,
        },
    }
    return infile_dict


@pytest.fixture
def forcing_processor():
    from bloomcast.utils import ForcingDataProcessor

    return ForcingDataProcessor(Mock(name="config"))


@pytest.fixture
def climate_processor():
    from bloomcast.utils import ClimateDataProcessor

    mock_config = Mock(name="config")
    mock_config.climate.params = {}
    mock_config.run_start_date = datetime.date(2011, 9, 19)
    mock_data_readers = Mock(name="data_readers")
    return ClimateDataProcessor(mock_config, mock_data_readers)


class TestConfig:
    """Unit tests for Config object."""

    def test_load_config_climate_url(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """load_config puts expected value in config.climate.url"""
        test_url = "https://example.com/climateData/bulkdata_e.html"
        monkeypatch.setitem(config_dict["climate"], "url", test_url)
        config._read_yaml_file = Mock(return_value=config_dict)
        config._read_SOG_infile = Mock(return_value=infile_dict)
        config.load_config("config_file")
        assert config.climate.url == test_url

    def test_load_config_climate_params(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """load_config puts expected value in config.climate.params"""
        test_params = {
            "timeframe": 1,
            "Prov": "BC",
            "format": "xml",
        }
        monkeypatch.setitem(config_dict["climate"], "params", test_params)
        config._read_yaml_file = Mock(return_value=config_dict)
        config._read_SOG_infile = Mock(return_value=infile_dict)
        config.load_config("config_file")
        assert config.climate.params == test_params

    def test_load_meteo_config_station_id(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_meteo_config puts exp value in config.climate.meteo.station_id"""
        test_station_id = 889
        monkeypatch.setitem(
            config_dict["climate"]["meteo"], "station_id", test_station_id
        )
        config.climate = Mock()
        config._read_yaml_file = Mock(return_value=config_dict)
        config._load_meteo_config(config_dict, infile_dict)
        assert config.climate.meteo.station_id == test_station_id

    def test_load_meteo_config_cloud_fraction_mapping(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_meteo_config puts expected value in cloud_fraction_mapping"""
        test_cloud_fraction_mapping_file = "cloud_fraction_mapping.yaml"
        monkeypatch.setitem(
            config_dict["climate"]["meteo"],
            "cloud_fraction_mapping",
            test_cloud_fraction_mapping_file,
        )
        test_cloud_fraction_mapping = {
            "Drizzle": [9.9675925925925934],
            "Clear": [0.0] * 12,
        }
        config.climate = Mock()

        def side_effect(config_file):  # NOQA
            return (
                DEFAULT if config_file == "config_file" else test_cloud_fraction_mapping
            )

        config._read_yaml_file = Mock(return_value=config_dict, side_effect=side_effect)
        config._load_meteo_config(config_dict, infile_dict)
        expected = test_cloud_fraction_mapping
        assert config.climate.meteo.cloud_fraction_mapping == expected

    def test_load_wind_config_station_id(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_wind_config puts value in config.climate.wind.station_id"""
        test_station_id = 889
        monkeypatch.setitem(
            config_dict["climate"]["wind"], "station_id", test_station_id
        )
        config.climate = Mock()
        config._read_yaml_file = Mock(return_value=config_dict)
        config._load_wind_config(config_dict, infile_dict)
        assert config.climate.wind.station_id == test_station_id

    def test_load_rivers_config_major_station_id(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_rivers_config puts value in config.rivers.major.station_id"""
        test_station_id = "08MF005"
        monkeypatch.setitem(
            config_dict["rivers"]["major"], "station_id", test_station_id
        )
        config.rivers = Mock()
        config._read_yaml_file = Mock(return_value=config_dict)
        config._load_rivers_config(config_dict, infile_dict)
        assert config.rivers.major.station_id == test_station_id

    def test_load_rivers_config_minor_station_id(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_rivers_config puts value in config.rivers.minor.station_id"""
        test_station_id = "08HB002"
        monkeypatch.setitem(
            config_dict["rivers"]["minor"], "station_id", test_station_id
        )
        config.rivers = Mock()
        config._read_yaml_file = Mock(return_value=config_dict)
        config._load_rivers_config(config_dict, infile_dict)
        assert config.rivers.minor.station_id == test_station_id

    def test_load_rivers_config_minor_scale_factor(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_rivers_config puts value in config.rivers.minor.scale_factor"""
        test_scale_factor = 0.351
        monkeypatch.setitem(
            config_dict["rivers"]["minor"], "scale_factor", test_scale_factor
        )
        config.rivers = Mock()
        config._read_yaml_file = Mock(return_value=config_dict)
        config._load_rivers_config(config_dict, infile_dict)
        assert config.rivers.minor.scale_factor == test_scale_factor

    def test_load_rivers_config_major_forcing_data_file(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_rivers_config puts value in config.rivers.output_file.major"""
        test_output_file = "Fraser_flow"
        monkeypatch.setitem(
            infile_dict["forcing_data_files"], "major_river", test_output_file
        )
        config.rivers = Mock()
        config._read_yaml_file = Mock(return_value=config_dict)
        config._load_rivers_config(config_dict, infile_dict)
        assert config.rivers.output_files["major"] == test_output_file

    def test_load_rivers_config_minor_forcing_data_file(
        self, config, config_dict, infile_dict, monkeypatch
    ):
        """_load_rivers_config puts value in config.rivers.output_file.minor"""
        test_output_file = "Englishman_flow"
        monkeypatch.setitem(
            infile_dict["forcing_data_files"], "minor_river", test_output_file
        )
        config.rivers = Mock()
        config._read_yaml_file = Mock(return_value=config_dict)
        config._load_rivers_config(config_dict, infile_dict)
        assert config.rivers.output_files["minor"] == test_output_file


class TestForcingDataProcessor:
    """Unit tests for ForcingDataProcessor object."""

    def test_patch_data_1_hour_gap(self, forcing_processor):
        """patch_data correctly flags 1 hour gap in data for interpolation"""
        forcing_processor.data["air_temperature"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), 235.0),
        ]
        forcing_processor.interpolate_values = Mock(name="interpolate_values")
        with patch("bloomcast.utils.log") as mock_log:
            forcing_processor.patch_data("air_temperature")
        expected = [
            (("air_temperature data patched for 2011-09-25 10:00:00",),),
            (
                (
                    "1 air_temperature data values patched; "
                    "see debug log on disk for details",
                ),
            ),
        ]
        assert mock_log.debug.call_args_list == expected
        forcing_processor.interpolate_values.assert_called_once_with(
            "air_temperature", 1, 1
        )

    def test_patch_data_2_hour_gap(self, forcing_processor):
        """patch_data correctly flags 2 hour gap in data for interpolation"""
        forcing_processor.data = {}
        forcing_processor.data["air_temperature"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), 230.0),
        ]
        forcing_processor.interpolate_values = Mock()
        with patch("bloomcast.utils.log") as mock_log:
            forcing_processor.patch_data("air_temperature")
        expected = [
            (("air_temperature data patched for 2011-09-25 10:00:00",),),
            (("air_temperature data patched for 2011-09-25 11:00:00",),),
            (
                (
                    "2 air_temperature data values patched; "
                    "see debug log on disk for details",
                ),
            ),
        ]
        assert mock_log.debug.call_args_list == expected
        forcing_processor.interpolate_values.assert_called_once_with(
            "air_temperature", 1, 2
        )

    def test_patch_data_2_gaps(self, forcing_processor):
        """patch_data correctly flags 2 gaps in data for interpolation"""
        forcing_processor.data["air_temperature"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), 230.0),
            (datetime.datetime(2011, 9, 25, 13, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 14, 0, 0), 250.0),
        ]
        forcing_processor.interpolate_values = Mock()
        with patch("bloomcast.utils.log") as mock_log:
            forcing_processor.patch_data("air_temperature")
        expected = [
            (("air_temperature data patched for 2011-09-25 10:00:00",),),
            (("air_temperature data patched for 2011-09-25 11:00:00",),),
            (("air_temperature data patched for 2011-09-25 13:00:00",),),
            (
                (
                    "3 air_temperature data values patched; "
                    "see debug log on disk for details",
                ),
            ),
        ]
        assert mock_log.debug.call_args_list == expected
        expected = [(("air_temperature", 1, 2),), (("air_temperature", 4, 4),)]
        assert forcing_processor.interpolate_values.call_args_list == expected

    def test_interpolate_values_1_hour_gap(self, forcing_processor):
        """interpolate_values interpolates value for 1 hour gap in data"""
        forcing_processor.data = {}
        forcing_processor.data["air_temperature"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), 235.0),
        ]
        forcing_processor.interpolate_values("air_temperature", 1, 1)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), 225.0)
        assert forcing_processor.data["air_temperature"][1] == expected

    def test_interpolate_values_2_hour_gap(self, forcing_processor):
        """interpolate_values interpolates value for 2 hour gap in data"""
        forcing_processor.data = {}
        forcing_processor.data["air_temperature"] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), 230.0),
        ]
        forcing_processor.interpolate_values("air_temperature", 1, 2)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), 220.0)
        assert forcing_processor.data["air_temperature"][1] == expected
        expected = (datetime.datetime(2011, 9, 25, 11, 0, 0), 225.0)
        assert forcing_processor.data["air_temperature"][2] == expected

    def test_interpolate_values_gap_gt_11_hr_logs_warning(
        self,
        forcing_processor,
    ):
        """data gap >11 hr generates warning log message"""
        forcing_processor.data["air_temperature"] = [
            (datetime.datetime(2014, 2, 11, 0, 0, 0), 15.0)
        ]
        forcing_processor.data["air_temperature"].extend(
            [(datetime.datetime(2014, 2, 11, 1 + i, 0, 0), None) for i in range(15)]
        )
        forcing_processor.data["air_temperature"].append(
            (datetime.datetime(2014, 2, 11, 16, 0, 0), 30.0)
        )
        with patch("bloomcast.utils.log", Mock()) as mock_log:
            forcing_processor.interpolate_values(
                "air_temperature", gap_start=1, gap_end=15
            )
            mock_log.warning.assert_called_once_with(
                "A air_temperature forcing data gap > 11 hr starting at "
                "2014-02-11 01:00 has been patched by linear interpolation"
            )


class TestClimateDataProcessor:
    """Unit tests for ClimateDataProcessor object."""

    def test_get_data_months_run_start_date_same_year(self, climate_processor):
        """_get_data_months returns data months for run start date in same year"""
        with patch("bloomcast.utils.datetime") as mock_datetime:
            mock_datetime.date.today.return_value = datetime.date(2011, 9, 1)
            mock_datetime.date.side_effect = datetime.date
            data_months = climate_processor._get_data_months()
        assert data_months[0] == datetime.date(2011, 1, 1)
        assert data_months[-1] == datetime.date(2011, 9, 1)

    def test_get_data_months_run_start_date_prev_year(self, climate_processor):
        """_get_data_months returns data months for run start date in prev yr"""
        with patch("bloomcast.utils.datetime") as mock_datetime:
            mock_datetime.date.today.return_value = datetime.date(2012, 2, 1)
            mock_datetime.date.side_effect = datetime.date
            data_months = climate_processor._get_data_months()
        assert data_months[0] == datetime.date(2011, 1, 1)
        assert data_months[11] == datetime.date(2011, 12, 1)
        assert data_months[-1] == datetime.date(2012, 2, 1)
