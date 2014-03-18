"""Unit tests for bloomcast modules.
"""
import datetime
import unittest.mock as mock
import pytest


@pytest.fixture
def make_config():
    from bloomcast.utils import Config
    return Config()


@pytest.fixture(scope='function')
def config_dict():
    config_dict = {
        'get_forcing_data': None,
        'run_SOG': None,
        'SOG_executable': None,
        'html_results': None,
        'ensemble': {
            'base_infile': None,
        },
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
            'use_test_smtpd': None,
        },
        'results_dir': None,
    }
    return config_dict


@pytest.fixture(scope='function')
def infile_dict():
    infile_dict = {
        'run_start_date': datetime.datetime(2011, 11, 11, 12, 33, 42),
        'SOG_timestep': '900',
        'std_phys_ts_outfile': None,
        'user_phys_ts_outfile': None,
        'std_bio_ts_outfile': None,
        'user_bio_ts_outfile': None,
        'std_chem_ts_outfile': None,
        'user_chem_ts_outfile': None,
        'profiles_outfile_base': None,
        'user_profiles_outfile_base': None,
        'halocline_outfile': None,
        'Hoffmueller_profiles_outfile': None,
        'user_Hoffmueller_profiles_outfile': None,
        'forcing_data_files': {
            'air_temperature': None,
            'relative_humidity': None,
            'cloud_fraction': None,
            'wind': None,
            'major_river': None,
            'minor_river': None,
        },
    }
    return infile_dict


@pytest.fixture
def mock_config():
    return mock.Mock(name='config')


@pytest.fixture
def make_ForcingDataProcessor():
    from bloomcast.utils import ForcingDataProcessor
    return ForcingDataProcessor(mock_config)


@pytest.fixture
def make_ClimateDataProcessor():
    from bloomcast.wind import ClimateDataProcessor
    mock_config_ = mock_config()
    mock_config_.climate.params = {}
    mock_config_.run_start_date = datetime.date(2011, 9, 19)
    mock_data_readers = mock.Mock(name='data_readers')
    return ClimateDataProcessor(mock_config_, mock_data_readers)


class TestConfig():
    """Unit tests for Config object.
    """
    def test_load_config_climate_url(self):
        """load_config puts expected value in config.climate.url
        """
        test_url = 'http://example.com/climateData/bulkdata_e.html'
        mock_config_dict = config_dict()
        mock_config_dict['climate']['url'] = test_url
        config = make_config()
        config._read_yaml_file = mock.Mock(return_value=mock_config_dict)
        config._read_SOG_infile = mock.Mock(return_value=infile_dict())
        config.load_config('config_file')
        assert config.climate.url == test_url

    def test_load_config_climate_params(self):
        """load_config puts expected value in config.climate.params
        """
        test_params = {
            'timeframe': 1,
            'Prov': 'BC',
            'format': 'xml',
        }
        mock_config_dict = config_dict()
        mock_config_dict['climate']['params'] = test_params
        config = make_config()
        config._read_yaml_file = mock.Mock(return_value=mock_config_dict)
        config._read_SOG_infile = mock.Mock(return_value=infile_dict())
        config.load_config('config_file')
        assert config.climate.params == test_params

    def test_load_meteo_config_station_id(self):
        """_load_meteo_config puts exp value in config.climate.meteo.station_id
        """
        test_station_id = 889
        mock_config_dict = config_dict()
        mock_config_dict['climate']['meteo']['station_id'] = test_station_id
        config = make_config()
        config.climate = mock.Mock()
        config._read_yaml_file = mock.Mock(return_value=mock_config_dict)
        config._load_meteo_config(mock_config_dict, infile_dict())
        assert config.climate.meteo.station_id == test_station_id

    def test_load_meteo_config_cloud_fraction_mapping(self):
        """_load_meteo_config puts expected value in cloud_fraction_mapping
        """
        test_cloud_fraction_mapping_file = 'cloud_fraction_mapping.yaml'
        mock_config_dict = config_dict()
        mock_config_dict['climate']['meteo']['cloud_fraction_mapping'] = (
            test_cloud_fraction_mapping_file)
        test_cloud_fraction_mapping = {
            'Drizzle': [9.9675925925925934],
            'Clear': [0.0] * 12,
        }
        config = make_config()
        config.climate = mock.Mock()

        def side_effect(config_file):   # NOQA
            return (mock.DEFAULT if config_file == 'config_file'
                    else test_cloud_fraction_mapping)
        config._read_yaml_file = mock.Mock(
            return_value=mock_config_dict, side_effect=side_effect)
        config._load_meteo_config(mock_config_dict, infile_dict())
        expected = test_cloud_fraction_mapping
        assert config.climate.meteo.cloud_fraction_mapping == expected

    def test_load_wind_config_station_id(self):
        """_load_wind_config puts value in config.climate.wind.station_id
        """
        test_station_id = 889
        mock_config_dict = config_dict()
        mock_config_dict['climate']['wind']['station_id'] = test_station_id
        config = make_config()
        config.climate = mock.Mock()
        config._read_yaml_file = mock.Mock(return_value=mock_config_dict)
        config._load_wind_config(mock_config_dict, infile_dict())
        assert config.climate.wind.station_id == test_station_id


class TestForcingDataProcessor():
    """Unit tests for ForcingDataProcessor object.
    """
    def test_patch_data_1_hour_gap(self):
        """patch_data correctly flags 1 hour gap in data for interpolation
        """
        processor = make_ForcingDataProcessor()
        processor.data['air_temperature'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), 235.0),
        ]
        processor.interpolate_values = mock.Mock(name='interpolate_values')
        with mock.patch('bloomcast.utils.log') as mock_log:
            processor.patch_data('air_temperature')
        expected = [
            (('air_temperature data patched for 2011-09-25 10:00:00',),),
            (('1 air_temperature data values patched; '
              'see debug log on disk for details',),),
        ]
        assert mock_log.debug.call_args_list == expected
        processor.interpolate_values.assert_called_once_with(
            'air_temperature', 1, 1)

    def test_patch_data_2_hour_gap(self):
        """patch_data correctly flags 2 hour gap in data for interpolation
        """
        processor = make_ForcingDataProcessor()
        processor.data = {}
        processor.data['air_temperature'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), 230.0),
        ]
        processor.interpolate_values = mock.Mock()
        with mock.patch('bloomcast.utils.log') as mock_log:
            processor.patch_data('air_temperature')
        expected = [
            (('air_temperature data patched for 2011-09-25 10:00:00',),),
            (('air_temperature data patched for 2011-09-25 11:00:00',),),
            (('2 air_temperature data values patched; '
              'see debug log on disk for details',),),
        ]
        assert mock_log.debug.call_args_list == expected
        processor.interpolate_values.assert_called_once_with(
            'air_temperature', 1, 2)

    def test_patch_data_2_gaps(self):
        """patch_data correctly flags 2 gaps in data for interpolation
        """
        processor = make_ForcingDataProcessor()
        processor.data['air_temperature'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), 230.0),
            (datetime.datetime(2011, 9, 25, 13, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 14, 0, 0), 250.0),
        ]
        processor.interpolate_values = mock.Mock()
        with mock.patch('bloomcast.utils.log') as mock_log:
            processor.patch_data('air_temperature')
        expected = [
            (('air_temperature data patched for 2011-09-25 10:00:00',),),
            (('air_temperature data patched for 2011-09-25 11:00:00',),),
            (('air_temperature data patched for 2011-09-25 13:00:00',),),
            (('3 air_temperature data values patched; '
              'see debug log on disk for details',),),
        ]
        assert mock_log.debug.call_args_list == expected
        expected = [(('air_temperature', 1, 2),), (('air_temperature', 4, 4),)]
        assert processor.interpolate_values.call_args_list == expected

    def test_interpolate_values_1_hour_gap(self):
        """interpolate_values interpolates value for 1 hour gap in data
        """
        processor = make_ForcingDataProcessor()
        processor.data = {}
        processor.data['air_temperature'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), 235.0),
        ]
        processor.interpolate_values('air_temperature', 1, 1)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), 225.0)
        assert processor.data['air_temperature'][1] == expected

    def test_interpolate_values_2_hour_gap(self):
        """interpolate_values interpolates value for 2 hour gap in data
        """
        processor = make_ForcingDataProcessor()
        processor.data = {}
        processor.data['air_temperature'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), 215.0),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), None),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), 230.0),
        ]
        processor.interpolate_values('air_temperature', 1, 2)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), 220.0)
        assert processor.data['air_temperature'][1] == expected
        expected = (datetime.datetime(2011, 9, 25, 11, 0, 0), 225.0)
        assert processor.data['air_temperature'][2] == expected

    def test_interpolate_values_gap_gt_11_hr_logs_warning(self):
        """data gap >11 hr generates warning log message
        """
        processor = make_ForcingDataProcessor()
        processor.data['air_temperature'] = [
            (datetime.datetime(2014, 2, 11, 0, 0, 0), 15.0)
        ]
        processor.data['air_temperature'].extend([
            (datetime.datetime(2014, 2, 11, 1 + i, 0, 0), None)
            for i in range(15)])
        processor.data['air_temperature'].append(
            (datetime.datetime(2014, 2, 11, 16, 0, 0), 30.0))
        with mock.patch('bloomcast.utils.log', mock.Mock()) as mock_log:
            processor.interpolate_values(
                'air_temperature', gap_start=1, gap_end=15)
            mock_log.warning.assert_called_once_with(
                'A air_temperature forcing data gap > 11 hr starting at '
                '2014-02-11 01:00 has been patched by linear interpolation')


class TestClimateDataProcessor():
    """Unit tests for ClimateDataProcessor object.
    """
    def test_get_data_months_run_start_date_same_year(self):
        """_get_data_months returns data months for run start date in same year
        """
        processor = make_ClimateDataProcessor()
        with mock.patch('bloomcast.utils.datetime') as mock_datetime:
            mock_datetime.date.today.return_value = datetime.date(2011, 9, 1)
            mock_datetime.date.side_effect = datetime.date
            data_months = processor._get_data_months()
        assert data_months[0] == datetime.date(2011, 1, 1)
        assert data_months[-1] == datetime.date(2011, 9, 1)

    def test_get_data_months_run_start_date_prev_year(self):
        """_get_data_months returns data months for run start date in prev yr
        """
        processor = make_ClimateDataProcessor()
        with mock.patch('bloomcast.utils.datetime') as mock_datetime:
            mock_datetime.date.today.return_value = datetime.date(2012, 2, 1)
            mock_datetime.date.side_effect = datetime.date
            data_months = processor._get_data_months()
        assert data_months[0] == datetime.date(2011, 1, 1)
        assert data_months[11] == datetime.date(2011, 12, 1)
        assert data_months[-1] == datetime.date(2012, 2, 1)
