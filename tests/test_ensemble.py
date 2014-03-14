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

import arrow
import cliff.app
import pytest


@pytest.fixture
def ensemble():
    import bloomcast.ensemble
    return bloomcast.ensemble.Ensemble(Mock(spec=cliff.app.App), [])


@pytest.fixture
def ensemble_mod():
    import bloomcast.ensemble
    return bloomcast.ensemble


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
            config.data_date = datetime.date(2014, 3, 12)
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
        ensemble.config = Mock(
            ensemble=Mock(
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
            )
        )
        ensemble.log = Mock()
        with patch('bloomcast.ensemble.open', mock_open(), create=True):
            ensemble._create_infile_edits()
        result = m_yaml.dump.call_args[0][0]['forcing_data']
        assert result['avg_historical_wind_file']['value'] == 'wind_data_8081'
        ensemble.log.debug.assert_called_once_with(
            'wrote infile edit file foo_8081.yaml'
        )


def test_two_yr_suffix(ensemble_mod):
    suffix = ensemble_mod.two_yr_suffix(1981)
    assert suffix == '_8081'
