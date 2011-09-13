"""Unit tests for bloomcast modules.
"""
from __future__ import absolute_import
import unittest2 as unittest
from mock import Mock


class TestConfig(unittest.TestCase):
    """Unit tests for Config object.
    """
    def _get_target_class(self):
        from .utils import Config
        return Config


    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)


    def test_config_climate_url(self):
        """
        """
        test_url = 'http://example.com/climateData/bulkdata_e.html'
        config = self._make_one()
        config._read_config_file = Mock(return_value={'climate': {'url': test_url}})
        config.load_config('config_file')
        self.assertEqual(config.climate.url, test_url)
