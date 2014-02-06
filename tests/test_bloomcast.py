"""Unit tests for bloomcast modules.
"""
import bs4
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
        'infiles': {
            'base': None,
            'edits': {
                'avg_forcing': None,
                'early_bloom_forcing': None,
                'late_bloom_forcing': None,
            },
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
        'std_bio_ts_outfile': None,
        'Hoffmueller_profiles_outfile': None,
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


@pytest.fixture
def make_WindProcessor():
    from bloomcast.wind import WindProcessor
    return WindProcessor(mock_config)


@pytest.fixture
def make_MeteoProcessor():
    from bloomcast.meteo import MeteoProcessor
    mock_config_ = mock_config()
    return MeteoProcessor(mock_config_)


@pytest.fixture
def make_RiversProcessor():
    from bloomcast.rivers import RiversProcessor
    mock_config_ = mock_config()
    return RiversProcessor(mock_config_)


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
        mock_log.debug.assert_called_once_with(
            'air_temperature data patched for 2011-09-25 10:00:00')
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


class TestWindProcessor():
    """Unit tests for WindProcessor object.
    """
    def test_interpolate_values_1_hour_gap(self):
        """interpolate_values interpolates value for 1 hour gap in data
        """
        wind = make_WindProcessor()
        wind.data['wind'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), (1.0, -2.0)),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), (None, None)),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), (2.0, -1.0)),
        ]
        wind.interpolate_values('wind', 1, 1)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), (1.5, -1.5))
        assert wind.data['wind'][1] == expected

    def test_interpolate_values_2_hour_gap(self):
        """interpolate_values interpolates value for 2 hour gap in data
        """
        wind = make_WindProcessor()
        wind.data['wind'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), (1.0, -2.0)),
            (datetime.datetime(2011, 9, 25, 10, 0, 0), (None, None)),
            (datetime.datetime(2011, 9, 25, 11, 0, 0), (None, None)),
            (datetime.datetime(2011, 9, 25, 12, 0, 0), (2.5, -0.5)),
        ]
        wind.interpolate_values('wind', 1, 2)
        expected = (datetime.datetime(2011, 9, 25, 10, 0, 0), (1.5, -1.5))
        assert wind.data['wind'][1] == expected
        expected = (datetime.datetime(2011, 9, 25, 11, 0, 0), (2.0, -1.0))
        assert wind.data['wind'][2] == expected

    def test_interpolate_values_gap_gt_11_hr_logs_warning(self):
        """wind data gap >11 hr generates warning log message
        """
        wind = make_WindProcessor()
        wind.data['wind'] = [
            (datetime.datetime(2011, 9, 25, 0, 0, 0), (1.0, -2.0))
        ]
        wind.data['wind'].extend([
            (datetime.datetime(2011, 9, 25, 1 + i, 0, 0), (None, None))
            for i in range(15)])
        wind.data['wind'].append(
            (datetime.datetime(2011, 9, 25, 16, 0, 0), (1.0, -2.0)))
        with mock.patch('bloomcast.wind.log', mock.Mock()) as mock_log:
            wind.interpolate_values('wind', gap_start=1, gap_end=15)
            mock_log.warning.assert_called_once_with(
                'A wind forcing data gap > 11 hr starting at 2011-09-25 01:00 '
                'has been patched by linear interpolation')

    def test_format_data(self):
        """format_data generator returns formatted forcing data file line
        """
        wind = make_WindProcessor()
        wind.data['wind'] = [
            (datetime.datetime(2011, 9, 25, 9, 0, 0), (1.0, 2.0)),
        ]
        line = next(wind.format_data())
        assert line == '25 09 2011 9.0 1.000000 2.000000\n'


class TestMeteoProcessor():
    """Unit tests for MeteoProcessor object.
    """
    def test_read_cloud_fraction_single_avg(self):
        """read_cloud_fraction returns expected value for single avg CF list
        """
        meteo = make_MeteoProcessor()
        meteo.config.climate.meteo.cloud_fraction_mapping = {
            'Drizzle': [9.9675925925925934],
        }
        record = mock.Mock(name='record')
        record.find().text = 'Drizzle'
        cloud_faction = meteo.read_cloud_fraction(record)
        assert cloud_faction == 9.9675925925925934

    def test_read_cloud_fraction_monthly_avg(self):
        """read_cloud_fraction returns expected value for monthly avg CF list
        """
        meteo = make_MeteoProcessor()
        meteo.config.climate.meteo.cloud_fraction_mapping = {
            'Fog': [
                9.6210045662100452, 9.3069767441860467, 9.5945945945945947,
                9.5, 9.931034482758621, 10.0, 9.7777777777777786,
                9.6999999999999993, 7.8518518518518521, 8.9701492537313428,
                9.2686980609418281, 9.0742358078602621]
        }
        record = mock.Mock(name='record')
        record.find().text = 'Fog'

        def mock_timestamp_data(part):
            parts = {'year': 2012, 'month': 4, 'day': 1, 'hour': 12}
            return parts[part]
        record.get = mock_timestamp_data
        cloud_faction = meteo.read_cloud_fraction(record)
        assert cloud_faction == 9.5

    def test_format_data(self):
        """format_data generator returns formatted forcing data file line
        """
        meteo = make_MeteoProcessor()
        meteo.config.climate.meteo.station_id = '889'
        meteo.data['air_temperature'] = [
            (datetime.datetime(2011, 9, 25, i, 0, 0), 215.0)
            for i in range(24)]
        line = next(meteo.format_data('air_temperature'))
        assert line == '889 2011 09 25 42' + ' 215.00' * 24 + '\n'


class TestRiverProcessor():
    """Uni tests for RiverProcessor object.
    """
    def test_date_params(self):
        """_date_params handles month-end rollover correctly
        """
        rivers = make_RiversProcessor()
        rivers.config.data_date = datetime.date(2011, 11, 30)
        expected = {
            'syr': 2011,
            'smo': 1,
            'sday': 1,
            'eyr': 2011,
            'emo': 12,
            'eday': 1,
        }
        assert rivers._date_params(2011) == expected

    def test_process_data_1_row(self):
        """process_data produces expected result for 1 row of data
        """
        rivers = make_RiversProcessor()
        test_data = [
            '<table>',
            '  <tr>',
            '    <td>2011-09-27 21:11:00</td>',
            '    <td>4200.0</td>',
            '  </tr>',
            '</table>',
        ]
        rivers.raw_data = bs4.BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        assert rivers.data['major'] == [(datetime.date(2011, 9, 27), 4200.0)]

    def test_process_data_2_rows_1_day(self):
        """process_data produces result for 2 rows of data from same day
        """
        rivers = make_RiversProcessor()
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
        rivers.raw_data = bs4.BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        assert rivers.data['major'] == [(datetime.date(2011, 9, 27), 4300.0)]

    def test_process_data_2_rows_2_days(self):
        """process_data produces expected result for 2 rows of data from 2 days
        """
        rivers = make_RiversProcessor()
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
        rivers.raw_data = bs4.BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        expected = [
            (datetime.date(2011, 9, 27), 4200.0),
            (datetime.date(2011, 9, 28), 4400.0),
        ]
        assert rivers.data['major'] == expected

    def test_process_data_4_rows_2_days(self):
        """process_data produces expected result for 4 rows of data from 2 days
        """
        rivers = make_RiversProcessor()
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
        rivers.raw_data = bs4.BeautifulSoup(''.join(test_data))
        rivers.process_data('major')
        expected = [
            (datetime.date(2011, 9, 27), 4300.0),
            (datetime.date(2011, 9, 28), 3300.0),
        ]
        assert rivers.data['major'] == expected

    def test_format_data(self):
        """format_data generator returns formatted forcing data file line
        """
        rivers = make_RiversProcessor()
        rivers.data['major'] = [
            (datetime.date(2011, 9, 27), 4200.0)
        ]
        line = next(rivers.format_data('major'))
        assert line == '2011 09 27 4.200000e+03\n'

    def test_patch_data_1_day_gap(self):
        """patch_data correctly flags 1 day gap in data for interpolation
        """
        processor = make_RiversProcessor()
        processor.data['major'] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 25), 4500.0),
        ]
        processor.interpolate_values = mock.Mock(name='interpolate_values')
        with mock.patch('bloomcast.rivers.log') as mock_log:
            processor.patch_data('major')
        expected = (datetime.date(2011, 10, 24), None)
        assert processor.data['major'][1] == expected
        mock_log.debug.assert_called_once_with(
            'major river data patched for 2011-10-24')
        processor.interpolate_values.assert_called_once_with(
            'major', 1, 1)

    def test_patch_data_2_day_gap(self):
        """patch_data correctly flags 2 day gap in data for interpolation
        """
        processor = make_RiversProcessor()
        processor.data['major'] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 26), 4600.0),
        ]
        processor.interpolate_values = mock.Mock(name='interpolate_values')
        with mock.patch('bloomcast.rivers.log') as mock_log:
            processor.patch_data('major')
        expected = [
            (datetime.date(2011, 10, 24), None),
            (datetime.date(2011, 10, 25), None),
        ]
        assert processor.data['major'][1:3] == expected
        expected = [
            (('major river data patched for 2011-10-24',),),
            (('major river data patched for 2011-10-25',),),
        ]
        assert mock_log.debug.call_args_list == expected
        processor.interpolate_values.assert_called_once_with(
            'major', 1, 2)

    def test_patch_data_2_gaps(self):
        """patch_data correctly flags 2 gaps in data for interpolation
        """
        processor = make_RiversProcessor()
        processor.data['major'] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 25), 4500.0),
            (datetime.date(2011, 10, 26), 4500.0),
            (datetime.date(2011, 10, 29), 4200.0),
        ]
        processor.interpolate_values = mock.Mock(name='interpolate_values')
        with mock.patch('bloomcast.rivers.log') as mock_log:
            processor.patch_data('major')
        expected = (datetime.date(2011, 10, 24), None)
        assert processor.data['major'][1] == expected
        expected = [
            (datetime.date(2011, 10, 27), None),
            (datetime.date(2011, 10, 28), None),
        ]
        assert processor.data['major'][4:6] == expected
        expected = [
            (('major river data patched for 2011-10-24',),),
            (('major river data patched for 2011-10-27',),),
            (('major river data patched for 2011-10-28',),),
        ]
        assert mock_log.debug.call_args_list == expected
        expected = [(('major', 1, 1),), (('major', 4, 5),)]
        assert processor.interpolate_values.call_args_list == expected

    def test_interpolate_values_1_day_gap(self):
        """interpolate_values interpolates value for 1 day gap in data
        """
        processor = make_RiversProcessor()
        processor.data = {}
        processor.data['major'] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 24), None),
            (datetime.date(2011, 10, 25), 4500.0),
        ]
        processor.interpolate_values('major', 1, 1)
        expected = (datetime.date(2011, 10, 24), 4400.0)
        assert processor.data['major'][1] == expected

    def test_interpolate_values_2_day_gap(self):
        """interpolate_values interpolates value for 2 day gap in data
        """
        processor = make_RiversProcessor()
        processor.data = {}
        processor.data['major'] = [
            (datetime.date(2011, 10, 23), 4300.0),
            (datetime.date(2011, 10, 24), None),
            (datetime.date(2011, 10, 25), None),
            (datetime.date(2011, 10, 26), 4600.0),
        ]
        processor.interpolate_values('major', 1, 2)
        expected = [
            (datetime.date(2011, 10, 24), 4400.0),
            (datetime.date(2011, 10, 25), 4500.0),
        ]
        assert processor.data['major'][1:3] == expected
