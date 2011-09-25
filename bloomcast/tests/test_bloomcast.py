"""Unit tests for bloomcast modules.
"""
from __future__ import absolute_import
from datetime import datetime
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


class TestClimateDataProcessor(unittest.TestCase):
    """Unit tests for ClimateDataProcessor object.
    """
    def _get_target_class(self):
        from utils import ClimateDataProcessor
        return ClimateDataProcessor


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_patch_data_1_hour_gap(self):
        """patch_data correctly interpolates value for 1 hour gap in hourlies
        """
        meteo = self._make_one(Mock(name='config'), Mock(name='data_readers'))
        meteo.hourlies['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), 235.0),
        ]
        meteo.patch_data('air_temperature')
        self.assertEqual(
            meteo.hourlies['air_temperature'][1],
            (datetime(2011, 9, 25, 10, 0, 0), 225.0))


    def test_patch_data_2_hour_gap(self):
        """patch_data correctly interpolates value for 2 hour gap in hourlies
        """
        meteo = self._make_one(Mock(name='config'), Mock(name='data_readers'))
        meteo.hourlies['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime(2011, 9, 25, 12, 0, 0), 230.0),
        ]
        meteo.patch_data('air_temperature')
        self.assertEqual(
            meteo.hourlies['air_temperature'][1],
            (datetime(2011, 9, 25, 10, 0, 0), 220.0))
        self.assertEqual(
            meteo.hourlies['air_temperature'][2],
            (datetime(2011, 9, 25, 11, 0, 0), 225.0))


    def test_patch_data_2_gaps(self):
        """patch_data correctly interpolates value for 2 gaps in hourlies
        """
        meteo = self._make_one(Mock(name='config'), Mock(name='data_readers'))
        meteo.hourlies['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime(2011, 9, 25, 12, 0, 0), 230.0),
            (datetime(2011, 9, 25, 13, 0, 0), None),
            (datetime(2011, 9, 25, 14, 0, 0), 250.0),
        ]
        meteo.patch_data('air_temperature')
        self.assertEqual(
            meteo.hourlies['air_temperature'][1],
            (datetime(2011, 9, 25, 10, 0, 0), 220.0))
        self.assertEqual(
            meteo.hourlies['air_temperature'][2],
            (datetime(2011, 9, 25, 11, 0, 0), 225.0))
        self.assertEqual(
            meteo.hourlies['air_temperature'][4],
            (datetime(2011, 9, 25, 13, 0, 0), 240.0))


class TestWindProcessor(unittest.TestCase):
    """Unit tests for WindProcessor object.
    """
    def _get_target_class(self):
        from wind import WindProcessor
        return WindProcessor


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_format_data(self):
        """format_data generator returns correctly formatted forcing data file line
        """
        wind = self._make_one(Mock(name='config'))
        wind.hourlies['wind'] = [
            (datetime(2011, 9, 25, 9, 0, 0), (1.0, 2.0)),
        ]
        line = wind.format_data().next()
        self.assertEqual(line, '25 09 2011 9.0 1.000000 2.000000\n')


class TestMeteoProcessor(unittest.TestCase):
    """Unit tests for MeteoProcessor object.
    """
    def _get_target_class(self):
        from meteo import MeteoProcessor
        return MeteoProcessor


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_format_data(self):
        """format_data generator returns correctly formatted forcing data file line
        """
        meteo = self._make_one(Mock(name='config'))
        meteo.config.climate.meteo.station_id = '889'
        meteo.hourlies['air_temperature'] = [
            (datetime(2011, 9, 25, i, 0, 0), 215.0)
            for i in xrange(24)]
        line = meteo.format_data('air_temperature').next()
        self.assertEqual(line, '889 2011 09 25 42' + ' 215.0' * 24 + '\n')
