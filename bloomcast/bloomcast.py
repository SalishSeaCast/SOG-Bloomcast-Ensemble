"""Driver module for SoG-bloomcast project
"""
from __future__ import absolute_import
# Standard library:
import logging
import sys
# Bloomcast:
from utils import Config


log = logging.getLogger(__file__)


def run(config_file):
    """
    """
    config = Config()
    config.load_config(config_file)


if __name__ == '__main__':
    run(sys.argv[1])
