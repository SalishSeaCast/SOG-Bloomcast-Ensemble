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
from unittest.mock import Mock

import cliff.app
import pytest


@pytest.fixture
def ensemble():
    import bloomcast.ensemble
    return bloomcast.ensemble.Ensemble(Mock(spec=cliff.app.App), [])


def test_get_parser(ensemble):
    parser = ensemble.get_parser('bloomcast ensemble')
    assert parser.prog == 'bloomcast ensemble'
