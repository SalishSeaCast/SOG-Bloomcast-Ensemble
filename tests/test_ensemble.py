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

"""Unit tests for SoG-bloomcast ensemble module.
"""
import datetime
from unittest.mock import (
    Mock,
    mock_open,
    patch,
)
import unittest.mock as mock

import arrow
import cliff.app
import pytest


@pytest.fixture
def ensemble():
    import bloomcast.ensemble
    return bloomcast.ensemble.Ensemble(Mock(spec=cliff.app.App), [])


@pytest.fixture
def ensemble_module():
    import bloomcast.ensemble
    return bloomcast.ensemble


@pytest.fixture(scope='function')
def ensemble_config():
    config = Mock(
        ensemble=Mock(
            max_concurrent_jobs=32,
            base_infile='foo.yaml',
            start_year=1981,
            end_year=1981,
            forcing_data_file_roots={
                'wind': 'wind_data',
                'air_temperature': 'AT_data',
                'cloud_fraction': 'CF_data',
                'relative_humidity': 'Hum_data',
                'major_river': 'major_river_data',
                'minor_river': 'minor_river_data',
            }
        ),
        std_phys_ts_outfile='std_phys_bloomcast.out',
        user_phys_ts_outfile='user_phys_bloomcast.out',
        std_bio_ts_outfile='std_bio_bloomcast.out',
        user_bio_ts_outfile='user_bio_bloomcast.out',
        std_chem_ts_outfile='std_chem_bloomcast.out',
        user_chem_ts_outfile='user_chem_bloomcast.out',
        profiles_outfile_base='profiles/bloomcast',
        user_profiles_outfile_base='profiles/user_bloomcast',
        halocline_outfile='profiles/halo_bloomcast.out',
        Hoffmueller_profiles_outfile='hoff_bloomcast.out',
        user_Hoffmueller_profiles_outfile='user_hoff_bloomcast.out',
    )
    return config


def test_get_parser(ensemble):
    parser = ensemble.get_parser('bloomcast ensemble')
    assert parser.prog == 'bloomcast ensemble'


@pytest.mark.usefixtures('ensemble')
class TestEnsembleTakeAction():
    """Unit tests for take_action method of Ensemble class.
    """
    @patch('bloomcast.ensemble.utils.Config')
    def test_get_forcing_data_conflicts_w_data_date(self, m_config, ensemble):
        parsed_args = Mock(
            config_file='config.yaml',
            data_date=None,
        )
        m_config.return_value = Mock(get_forcing_data=False)
        ensemble.log = Mock()
        with patch('bloomcast.ensemble.configure_logging'):
            ensemble.take_action(parsed_args)
        ensemble.log.debug.assert_called_once_with(
            'This will not end well: get_forcing_data=False '
            'and data_date=None'
        )

    @patch('bloomcast.ensemble.utils.Config')
    @patch('bloomcast.ensemble.arrow.now', return_value=arrow.get(2014, 3, 12))
    def test_no_river_flow_data_by_date(self, m_now, m_config, ensemble):
        parsed_args = Mock(
            config_file='config.yaml',
            data_date=None,
        )
        m_config.return_value = Mock(
            get_forcing_data=True,
            run_start_date=datetime.datetime(2012, 9, 19),
        )
        ensemble.log = Mock()
        with patch('bloomcast.ensemble.configure_logging'):
            ensemble.take_action(parsed_args)
        ensemble.log.error.assert_called_once_with(
            'A bloomcast run starting 2012-09-19 cannot be done today '
            'because there are no river flow data available prior to '
            '2012-09-12'
        )

    @patch('bloomcast.ensemble.utils.Config')
    def test_no_new_wind_data(self, m_config, ensemble):
        parsed_args = Mock(
            config_file='config.yaml',
            data_date=None,
        )
        m_config.return_value = Mock(
            get_forcing_data=True,
            run_start_date=datetime.datetime(2013, 9, 19),
        )
        ensemble.log = Mock()
        p_config_logging = patch('bloomcast.ensemble.configure_logging')

        def get_forcing_data(config, log):
            config.data_date = arrow.get(2014, 3, 12)
            raise ValueError
        p_get_forcing_data = patch(
            'bloomcast.ensemble.get_forcing_data',
            side_effect=get_forcing_data,
        )
        with p_config_logging, p_get_forcing_data:
            ensemble.take_action(parsed_args)
        ensemble.log.info.assert_called_once_with(
            'Wind data date 2014-03-12 is unchanged since last run'
        )

    @patch('bloomcast.ensemble.yaml')
    @patch('bloomcast.ensemble.utils.Config')
    def test_create_infile_edits_forcing_data(
        self, m_config, m_yaml, ensemble,
    ):
        ensemble.config = ensemble_config()
        ensemble.log = Mock()
        with patch('bloomcast.ensemble.open', mock_open(), create=True):
            ensemble._create_infile_edits()
        result = m_yaml.dump.call_args[0][0]['forcing_data']
        assert result['avg_historical_wind_file']['value'] == 'wind_data_8081'
        expected_keys = (
            'avg_historical_wind_file avg_historical_air_temperature_file '
            'avg_historical_cloud_file avg_historical_humidity_file '
            'avg_historical_major_river_file avg_historical_minor_river_file'
            .split())
        for key in expected_keys:
            assert result[key]['value'] is not None
        ensemble.log.debug.assert_called_once_with(
            'wrote infile edit file foo_8081.yaml'
        )

    @patch('bloomcast.ensemble.yaml')
    @patch('bloomcast.ensemble.utils.Config')
    def test_create_infile_edits_timeseries_results(
        self, m_config, m_yaml, ensemble,
    ):
        ensemble.config = ensemble_config()
        ensemble.log = Mock()
        with patch('bloomcast.ensemble.open', mock_open(), create=True):
            ensemble._create_infile_edits()
        result = m_yaml.dump.call_args[0][0]['timeseries_results']
        assert result['std_physics']['value'] == 'std_phys_bloomcast.out_8081'
        expected_keys = (
            'std_physics user_physics '
            'std_biology user_biology '
            'std_chemistry user_chemistry'
            .split())
        for key in expected_keys:
            assert result[key]['value'] is not None
        ensemble.log.debug.assert_called_once_with(
            'wrote infile edit file foo_8081.yaml'
        )

    @patch('bloomcast.ensemble.yaml')
    @patch('bloomcast.ensemble.utils.Config')
    def test_create_infile_edits_profiles_results(
        self, m_config, m_yaml, ensemble,
    ):
        ensemble.config = ensemble_config()
        ensemble.log = Mock()
        with patch('bloomcast.ensemble.open', mock_open(), create=True):
            ensemble._create_infile_edits()
        result = m_yaml.dump.call_args[0][0]['profiles_results']
        expected = 'profiles/bloomcast_8081'
        assert result['profile_file_base']['value'] == expected
        expected_keys = (
            'profile_file_base user_profile_file_base '
            'halocline_file '
            'hoffmueller_file user_hoffmueller_file'
            .split())
        for key in expected_keys:
            assert result[key]['value'] is not None
        ensemble.log.debug.assert_called_once_with(
            'wrote infile edit file foo_8081.yaml'
        )

    @patch('bloomcast.ensemble.yaml')
    @patch('bloomcast.ensemble.utils.Config')
    def test_create_infile_edits_sets_edit_files_list_attr(
        self, m_config, m_yaml, ensemble,
    ):
        ensemble.config = ensemble_config()
        ensemble.config.ensemble.end_year = 1982
        ensemble.log = Mock()
        with patch('bloomcast.ensemble.open', mock_open(), create=True):
            ensemble._create_infile_edits()
        assert ensemble.edit_files == [
            (1981, 'foo_8081.yaml', '_8081'),
            (1982, 'foo_8182.yaml', '_8182'),
        ]

    @patch('bloomcast.ensemble.yaml')
    def test_create_batch_description(self, m_yaml, ensemble):
        ensemble.config = ensemble_config()
        ensemble.config.ensemble.end_year = 1982
        ensemble.log = Mock()
        ensemble.edit_files = [
            (1981, 'foo_8081.yaml', '_8081'),
            (1982, 'foo_8182.yaml', '_8182'),
        ]
        with patch('bloomcast.ensemble.open', mock_open(), create=True):
            ensemble._create_batch_description()
        result = m_yaml.dump.call_args[0][0]
        expected = ensemble.config.ensemble.max_concurrent_jobs
        assert result['max_concurrent_jobs'] == expected
        assert result['SOG_executable'] == ensemble.config.SOG_executable
        assert result['base_infile'] == ensemble.config.ensemble.base_infile
        assert result['jobs'] == [
            {''.join(('bloomcast', suffix)): {
                'edit_files': [filename],
            }}
            for year, filename, suffix in ensemble.edit_files
        ]
        ensemble.log.debug.assert_called_once_with(
            'wrote ensemble batch description file: '
            'bloomcast_ensemble_jobs.yaml'
        )

    @patch('bloomcast.ensemble.SOGcommand')
    def test_run_SOG_batch_skip(self, m_SOGcommand, ensemble):
        ensemble.config = ensemble_config()
        ensemble.config.run_SOG = False
        ensemble.log = Mock()
        ensemble._run_SOG_batch()
        ensemble.log.info.assert_called_once_with('Skipped running SOG')
        assert not m_SOGcommand.api.batch.called

    @patch('bloomcast.ensemble.SOGcommand')
    def test_run_SOG_batch(self, m_SOGcommand, ensemble):
        ensemble.config = ensemble_config()
        ensemble.config.run_SOG = True
        ensemble.log = Mock()
        m_SOGcommand.api.batch.return_value = 0
        ensemble._run_SOG_batch()
        m_SOGcommand.api.batch.assert_called_once_with(
            'bloomcast_ensemble_jobs.yaml')
        ensemble.log.info.assert_called_once_with(
            'ensemble batch SOG runs completed with return code 0')

    @patch('bloomcast.utils.SOG_Timeseries')
    def test_load_biology_timeseries_instances(self, m_SOG_ts, ensemble):
        ensemble.config = ensemble_config()
        ensemble.edit_files = [(1981, 'foo_8081.yaml', '_8081')]
        ensemble._load_biology_timeseries()
        expected = [
            mock.call('std_bio_bloomcast.out_8081'),
            mock.call('std_bio_bloomcast.out_8081'),
        ]
        assert m_SOG_ts.call_args_list == expected

    @patch('bloomcast.utils.SOG_Timeseries')
    def test_load_biology_timeseries_read_nitrate(self, m_SOG_ts, ensemble):
        ensemble.config = ensemble_config()
        ensemble.edit_files = [(1981, 'foo_8081.yaml', '_8081')]
        ensemble._load_biology_timeseries()
        call = ensemble.nitrate_ts[1981].read_data.call_args_list[0]
        assert call == mock.call('time', '3 m avg nitrate concentration')

    @patch('bloomcast.utils.SOG_Timeseries')
    def test_load_biology_timeseries_read_diatoms(self, m_SOG_ts, ensemble):
        ensemble.config = ensemble_config()
        ensemble.edit_files = [(1981, 'foo_8081.yaml', '_8081')]
        ensemble._load_biology_timeseries()
        call = ensemble.diatoms_ts[1981].read_data.call_args_list[1]
        assert call == mock.call('time', '3 m avg micro phytoplankton biomass')

    @patch('bloomcast.utils.SOG_Timeseries')
    def test_load_biology_timeseries_mpl_dates(self, m_SOG_ts, ensemble):
        ensemble.config = ensemble_config()
        ensemble.edit_files = [(1981, 'foo_8081.yaml', '_8081')]
        ensemble._load_biology_timeseries()
        ensemble.nitrate_ts[1981].calc_mpl_dates.assert_called_with(
            ensemble.config.run_start_date)
        ensemble.diatoms_ts[1981].calc_mpl_dates.assert_called_with(
            ensemble.config.run_start_date)

    @patch('bloomcast.utils.SOG_Timeseries')
    def test_load_biology_timeseries_copies(self, m_SOG_ts, ensemble):
        ensemble.config = ensemble_config()
        ensemble.edit_files = [(1981, 'foo_8081.yaml', '_8081')]
        ensemble._load_biology_timeseries()
        assert ensemble.nitrate == ensemble.nitrate_ts
        assert ensemble.nitrate is not ensemble.nitrate_ts
        assert ensemble.diatoms == ensemble.diatoms_ts
        assert ensemble.diatoms is not ensemble.diatoms_ts


def test_two_yr_suffix(ensemble_module):
    suffix = ensemble_module.two_yr_suffix(1981)
    assert suffix == '_8081'


def test_find_member_single_year_day_match(ensemble_module):
    bloom_dates = {
        2014: arrow.get(2014, 3, 26),
    }
    member = ensemble_module.find_member(bloom_dates, 735317)
    assert member == 2014


def test_find_member_multiple_year_day_matches(ensemble_module):
    bloom_dates = {
        2005: arrow.get(2014, 3, 25),
        1997: arrow.get(2014, 3, 25),
    }
    member = ensemble_module.find_member(bloom_dates, 735316)
    assert member == 2005


def test_find_member_single_next_year_day_match(ensemble_module):
    bloom_dates = {
        1995: arrow.get(2014, 3, 27),
        1991: arrow.get(2014, 3, 21),
    }
    member = ensemble_module.find_member(bloom_dates, 735317)
    assert member == 1995


def test_find_member_single_previous_year_day_match(ensemble_module):
    bloom_dates = {
        2005: arrow.get(2014, 3, 25),
        1999: arrow.get(2014, 3, 29),
    }
    member = ensemble_module.find_member(bloom_dates, 735317)
    assert member == 2005


def test_find_member_multiple_previous_next_year_day_matches(ensemble_module):
    bloom_dates = {
        2005: arrow.get(2014, 3, 25),
        1995: arrow.get(2014, 3, 27),
    }
    member = ensemble_module.find_member(bloom_dates, 735317)
    assert member == 2005
