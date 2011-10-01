"""Unit tests for bloomcast modules.
"""
from __future__ import absolute_import
from BeautifulSoup import BeautifulSoup
from datetime import date
from datetime import datetime
from mock import DEFAULT
from mock import MagicMock
from mock import Mock
from mock import patch
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
            },
            'rivers': {
                'disclaimer_url': None,
                'accept_disclaimer': {
                    'disclaimer_action': None,
                },
                'data_url': None,
                'params': {
                    'mode': None,
                    'prm1': None,
                },
                'major': {
                    'station_id': None,
                },
                'minor': {
                    'station_id': None,
                },
            },
            'logging': {
                'debug': None,
                'toaddrs': [],
                'use_test_smtpd':  None,
            },
        }
        return mock_config_dict


    def _make_mock_infile_dict(self):
        mock_infile_dict = {
            'run_start_date': None,
            'forcing_data_files': {
                'air_temperature': None,
                'relative_humidity': None,
                'cloud_fraction': None,
                'wind': None,
                'major_river': None,
                'minor_river': None,
            },
        }
        return mock_infile_dict


    def test_load_config_climate_url(self):
        """load_config puts expected value in config.climate.url
        """
        test_url = 'http://example.com/climateData/bulkdata_e.html'
        mock_config_dict = self._make_mock_config_dict()
        mock_config_dict['climate']['url'] = test_url
        mock_infile_dict = self._make_mock_infile_dict()
        config = self._make_one()
        config._read_yaml_file = Mock(return_value=mock_config_dict)
        config._read_SOG_infile = Mock(return_value=mock_infile_dict)
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
        mock_infile_dict = self._make_mock_infile_dict()
        config = self._make_one()
        config._read_yaml_file = Mock(return_value=mock_config_dict)
        config._read_SOG_infile = Mock(return_value=mock_infile_dict)
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
        """_load_wind_config puts value in config.climate.wind.station_id
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


    def test_read_SOG_infile_multi_blanks(self):
        """_read_SOG_infile works for multiple blanks between key and filename
        """
        config = self._make_one()
        config.infile = 'foo'
        with patch('utils.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(name='magic mock', spec=file)
            mock_open.return_value.__enter__.return_value = [
                '"wind"  "Sandheads_wind"  "wind forcing data"\n',
            ]
            infile_dict = config._read_SOG_infile()
        self.assertEqual(
            infile_dict,
            {'forcing_data_files': {
                'wind': 'Sandheads_wind'
            }})


    def test_read_SOG_infile_newlines(self):
        """_read_SOG_infile works for newline between key and filename
        """
        config = self._make_one()
        config.infile = 'foo'
        with patch('utils.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(name='magic mock', spec=file)
            mock_open.return_value.__enter__.return_value = [
                '"wind"  \n  "Sandheads_wind"  \n  "wind forcing data"\n',
            ]
            infile_dict = config._read_SOG_infile()
        self.assertEqual(
            infile_dict,
            {'forcing_data_files': {
                'wind': 'Sandheads_wind'
            }})


    def test_read_SOG_run_start_date(self):
        """_read_SOG_infile returns expected run start date
        """
        config = self._make_one()
        config.infile = 'foo'
        with patch('utils.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(name='magic mock', spec=file)
            mock_open.return_value.__enter__.return_value = [
                '"init datetime" "2011-09-19 18:49:00" '
                    '"initialization CTD profile date/time"\n',
            ]
            infile_dict = config._read_SOG_infile()
        self.assertEqual(
            infile_dict,
            {'run_start_date': datetime(2011, 9, 19, 18, 49),
             'forcing_data_files': {}})


class TestForcingDataProcessor(unittest.TestCase):
    """Unit tests for ForcingDataProcessor object.
    """
    def _get_target_class(self):
        from utils import ForcingDataProcessor
        return ForcingDataProcessor


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_patch_data_1_hour_gap(self):
        """patch_data correctly interpolates value for 1 hour gap in data
        """
        processor = self._make_one(Mock(name='config'))
        processor.data['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), 235.0),
        ]
        processor.interpolate_values = Mock()
        processor.patch_data('air_temperature')
        processor.interpolate_values.assert_called_once_with(
            'air_temperature', 1, 1)


    def test_patch_data_2_hour_gap(self):
        """patch_data correctly interpolates value for 2 hour gap in data
        """
        processor = self._make_one(Mock(name='config'))
        processor.data = {}
        processor.data['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime(2011, 9, 25, 12, 0, 0), 230.0),
        ]
        processor.interpolate_values = Mock()
        processor.patch_data('air_temperature')
        processor.interpolate_values.assert_called_once_with(
            'air_temperature', 1, 2)


    def test_patch_data_2_gaps(self):
        """patch_data correctly interpolates value for 2 gaps in data
        """
        processor = self._make_one(Mock(name='config'))
        processor.data['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime(2011, 9, 25, 12, 0, 0), 230.0),
            (datetime(2011, 9, 25, 13, 0, 0), None),
            (datetime(2011, 9, 25, 14, 0, 0), 250.0),
        ]
        processor.interpolate_values = Mock()
        processor.patch_data('air_temperature')
        self.assertEqual(
            processor.interpolate_values.call_args_list,
            [(('air_temperature', 1, 2),), (('air_temperature', 4, 4),)])


    def test_interpolate_values_1_hour_gap(self):
        """interpolates correctly interpolates value for 1 hour gap in data
        """
        processor = self._make_one(Mock(name='config'))
        processor.data = {}
        processor.data['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), 235.0),
        ]
        processor.interpolate_values('air_temperature', 1, 1)
        self.assertEqual(
            processor.data['air_temperature'][1],
            (datetime(2011, 9, 25, 10, 0, 0), 225.0))


    def test_interpolate_values_2_hour_gap(self):
        """interpolate_values correctly interpolates value for 2 hour gap in data
        """
        processor = self._make_one(Mock(name='config'))
        processor.data = {}
        processor.data['air_temperature'] = [
            (datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime(2011, 9, 25, 12, 0, 0), 230.0),
        ]
        processor.interpolate_values('air_temperature', 1, 2)
        self.assertEqual(
            processor.data['air_temperature'][1],
            (datetime(2011, 9, 25, 10, 0, 0), 220.0))
        self.assertEqual(
            processor.data['air_temperature'][2],
            (datetime(2011, 9, 25, 11, 0, 0), 225.0))


class TestClimateDataProcessor(unittest.TestCase):
    """Unit tests for ClimateDataProcessor object.
    """
    def _get_target_class(self):
        from wind import ClimateDataProcessor
        return ClimateDataProcessor


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_get_data_months_run_start_date_same_year(self):
        """_get_data_months returns data months for run start date in same year
        """
        mock_config = Mock()
        mock_config.climate.params = {}
        mock_config.run_start_date = date(2011, 9, 19)
        processor = self._make_one(mock_config, Mock(name='data_readers'))
        with patch('utils.date') as mock_date:
            mock_date.today.return_value = date(2011, 9, 1)
            mock_date.side_effect = date
            data_months = processor._get_data_months()
        self.assertEqual(data_months[0], date(2011, 1, 1))
        self.assertEqual(data_months[-1], date(2011, 9, 1))


    def test_get_data_months_run_start_date_prev_year(self):
        """_get_data_months returns data months for run start date in previous yr
        """
        mock_config = Mock()
        mock_config.climate.params = {}
        mock_config.run_start_date = date(2011, 9, 19)
        processor = self._make_one(mock_config, Mock(name='data_readers'))
        with patch('utils.date') as mock_date:
            mock_date.today.return_value = date(2012, 2, 1)
            mock_date.side_effect = date
            data_months = processor._get_data_months()
        self.assertEqual(data_months[0], date(2011, 1, 1))
        self.assertEqual(data_months[11], date(2011, 12, 1))
        self.assertEqual(data_months[-1], date(2012, 2, 1))


class TestWindProcessor(unittest.TestCase):
    """Unit tests for WindProcessor object.
    """
    def _get_target_class(self):
        from wind import WindProcessor
        return WindProcessor


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_interpolate_values_1_hour_gap(self):
        """interpolate_values correctly interpolates value for 1 hour gap in data
        """
        wind = self._make_one(Mock(name='config'))
        wind.data['wind'] = [
            (datetime(2011, 9, 25, 9, 0, 0), (1.0, -2.0)),
            (datetime(2011, 9, 25, 10, 0, 0), (None, None)),
            (datetime(2011, 9, 25, 11, 0, 0), (2.0, -1.0)),
        ]
        wind.interpolate_values('wind', 1, 1)
        self.assertEqual(
            wind.data['wind'][1],
            (datetime(2011, 9, 25, 10, 0, 0), (1.5, -1.5)))


    def test_interpolate_values_2_hour_gap(self):
        """interpolate_values correctly interpolates value for 2 hour gap in data
        """
        wind = self._make_one(Mock(name='config'))
        wind.data['wind'] = [
            (datetime(2011, 9, 25, 9, 0, 0), (1.0, -2.0)),
            (datetime(2011, 9, 25, 10, 0, 0), (None, None)),
            (datetime(2011, 9, 25, 11, 0, 0), (None, None)),
            (datetime(2011, 9, 25, 12, 0, 0), (2.5, -0.5)),
        ]
        wind.interpolate_values('wind', 1, 2)
        self.assertEqual(
            wind.data['wind'][1],
            (datetime(2011, 9, 25, 10, 0, 0), (1.5, -1.5)))
        self.assertEqual(
            wind.data['wind'][2],
            (datetime(2011, 9, 25, 11, 0, 0), (2.0, -1.0)))


    def test_interpolate_values_gap_gt_11_hr_logs_warning(self):
        """wind data gap >11 hr generates warning log message
        """
        wind = self._make_one(Mock(name='config'))
        wind.data['wind'] = [(datetime(2011, 9, 25, 0, 0, 0), (1.0, -2.0))]
        wind.data['wind'].extend([
            (datetime(2011, 9, 25, 1 + i, 0, 0), (None, None)) for i in xrange(15)])
        wind.data['wind'].append(
            (datetime(2011, 9, 25, 16, 0, 0), (1.0, -2.0)))
        with patch('wind.log', Mock()) as mock_log:
            wind.interpolate_values('wind', gap_start=1, gap_end=15)
            mock_log.warning.assert_called_once_with(
                'A wind forcing data gap > 11 hr starting at 2011-09-25 01:00 '
                'has been patched by linear interpolation')


    def test_format_data(self):
        """format_data generator returns correctly formatted forcing data file line
        """
        wind = self._make_one(Mock(name='config'))
        wind.data['wind'] = [
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
        meteo.data['air_temperature'] = [
            (datetime(2011, 9, 25, i, 0, 0), 215.0)
            for i in xrange(24)]
        line = meteo.format_data('air_temperature').next()
        self.assertEqual(line, '889 2011 09 25 42' + ' 215.0' * 24 + '\n')



class TestRiverProcessor(unittest.TestCase):
    """Uni tests for RiverProcessor object.
    """
    def _get_target_class(self):
        from rivers import RiversProcessor
        return RiversProcessor


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_process_data_1_row(self):
        """process_data produces expected result for 1 row of data
        """
        rivers = self._make_one(Mock(name='config'))
        test_data = [
            '<table>',
            '  <tr>',
            '    <td>2011-09-27 21:11:00</td>',
            '    <td>4200.0</td>',
            '  </tr>',
            '</table>',
        ]
        rivers.raw_data = BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        self.assertEqual(rivers.data['major'], [(date(2011, 9, 27), 4200.0)])


    def test_process_data_2_rows_1_day(self):
        """process_data produces expected result for 2 rows of data from same day
        """
        rivers = self._make_one(Mock(name='config'))
        test_data = [
            '<table>',
            '  <tr>',
            '    <td>2011-09-27 21:11:00</td>',
            '    <td>4200.0</td>',
            '  </tr>',
            '  <tr>',
            '    <td>2011-09-27 21:35:00</td>',
            '    <td>4400.0</td>',
            '  </tr>',
            '</table>',
        ]
        rivers.raw_data = BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        self.assertEqual(rivers.data['major'], [(date(2011, 9, 27), 4300.0)])


    def test_process_data_2_rows_2_days(self):
        """process_data produces expected result for 2 rows of data from 2 days
        """
        rivers = self._make_one(Mock(name='config'))
        test_data = [
            '<table>',
            '  <tr>',
            '    <td>2011-09-27 21:11:00</td>',
            '    <td>4200.0</td>',
            '  </tr>',
            '  <tr>',
            '    <td>2011-09-28 21:35:00</td>',
            '    <td>4400.0</td>',
            '  </tr>',
            '</table>',
        ]
        rivers.raw_data = BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        self.assertEqual(
            rivers.data['major'], [
                (date(2011, 9, 27), 4200.0),
                (date(2011, 9, 28), 4400.0)])


    def test_process_data_4_rows_2_days(self):
        """process_data produces expected result for 4 rows of data from 2 days
        """
        rivers = self._make_one(Mock(name='config'))
        test_data = [
            '<table>',
            '  <tr>',
            '    <td>2011-09-27 21:11:00</td>',
            '    <td>4200.0</td>',
            '  </tr>',
            '  <tr>',
            '    <td>2011-09-27 21:35:00</td>',
            '    <td>4400.0</td>',
            '  <tr>',
            '    <td>2011-09-28 21:11:00</td>',
            '    <td>3200.0</td>',
            '  </tr>',
            '  <tr>',
            '    <td>2011-09-28 21:35:00</td>',
            '    <td>3400.0</td>',
            '  </tr>',
            '</table>',
        ]
        rivers.raw_data = BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        self.assertEqual(
            rivers.data['major'], [
                (date(2011, 9, 27), 4300.0),
                (date(2011, 9, 28), 3300.0)])


    def test_format_data(self):
        """format_data generator returns correctly formatted forcing data file line
        """
        rivers = self._make_one(Mock(name='config'))
        rivers.data['major'] = [
            (date(2011, 9, 27), 4200.0)
        ]
        line = rivers.format_data('major').next()
        self.assertEqual(line, '2011 09 27 4.200000e+03\n')
