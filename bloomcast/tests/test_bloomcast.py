"""Unit tests for bloomcast modules.
"""
from __future__ import absolute_import
from mock import Mock
from mock import DEFAULT
import unittest2 as unittest


class TestConfig(unittest.TestCase):
    """Unit tests for Config object.
    """
    def _get_target_class(self):
        from utils import Config
        return Config


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def _make_mock_config_dict(self):
        mock_config_dict = {
            'infile': None,
            'climate': {
                'url': None,
                'params': None,
                'meteo': {
                    'station_id': None,
                    'quantities': [],
                    'cloud_fraction_mapping': None,
                },
                'wind': {
                    'station_id': None
                },
        }}
        return mock_config_dict


    def _make_mock_infile_dict(self):
        mock_infile_dict = {
            'forcing_data_files': {
                'air_temperature': None,
                'relative_humidity': None,
                'cloud_fraction': None,
                'wind': None,
            },
        }
        return mock_infile_dict


    def test_load_config_climate_url(self):
        """load_config puts expected value in config.climate.url
        """
        test_url = 'http://example.com/climateData/bulkdata_e.html'
        mock_config_dict = self._make_mock_config_dict()
        mock_config_dict['climate']['url'] = test_url
        config = self._make_one()
        config._read_yaml_file = Mock(return_value=mock_config_dict)
        config.load_config('config_file')
        self.assertEqual(config.climate.url, test_url)


    def test_load_config_climate_params(self):
        """load_config puts expected value in config.climate.params
        """
        test_params = {
            'timeframe': 1,
            'Prov': 'BC',
            'format': 'xml',
        }
        mock_config_dict = self._make_mock_config_dict()
        mock_config_dict['climate']['params'] = test_params
        config = self._make_one()
        config._read_yaml_file = Mock(return_value=mock_config_dict)
        config.load_config('config_file')
        self.assertEqual(config.climate.params, test_params)


    def test_load_meteo_config_station_id(self):
        """_load_meteo_config puts expected value in config.climate.meteo.station_id
        """
        test_station_id = 889
        mock_config_dict = self._make_mock_config_dict()
        mock_config_dict['climate']['meteo']['station_id'] = test_station_id
        mock_infile_dict = self._make_mock_infile_dict()
        config = self._make_one()
        config.climate = Mock()
        config._read_yaml_file = Mock(return_value=mock_config_dict)
        config._load_meteo_config(mock_config_dict, mock_infile_dict)
        self.assertEqual(config.climate.meteo.station_id, test_station_id)


    def test_load_meteo_config_cloud_fraction_mapping(self):
        """_load_meteo_config puts expected value in cloud_fraction_mapping
        """
        test_cloud_fraction_mapping_file = 'cloud_fraction_mapping.yaml'
        mock_config_dict = self._make_mock_config_dict()
        mock_config_dict['climate']['meteo']['cloud_fraction_mapping'] = (
            test_cloud_fraction_mapping_file)
        mock_infile_dict = self._make_mock_infile_dict()
        test_cloud_fraction_mapping = {
            'Drizzle':   10,
            'Clear':  0,
        }
        config = self._make_one()
        config.climate = Mock()
        def side_effect(config_file):
            return (DEFAULT if config_file == 'config_file'
                    else test_cloud_fraction_mapping)
        config._read_yaml_file = Mock(
            return_value=mock_config_dict, side_effect=side_effect)
        config._load_meteo_config(mock_config_dict, mock_infile_dict)
        self.assertEqual(
            config.climate.meteo.cloud_fraction_mapping,
            test_cloud_fraction_mapping)


    def test_load_wind_config_station_id(self):
        """_load_wind_config puts expected value in config.climate.wind.station_id
        """
        test_station_id = 889
        mock_config_dict = self._make_mock_config_dict()
        mock_config_dict['climate']['wind']['station_id'] = test_station_id
        mock_infile_dict = self._make_mock_infile_dict()
        config = self._make_one()
        config.climate = Mock()
        config._read_yaml_file = Mock(return_value=mock_config_dict)
        config._load_wind_config(mock_config_dict, mock_infile_dict)
        self.assertEqual(config.climate.wind.station_id, test_station_id)
