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

"""SoG-bloomcast command plug-in to run an ensemble forecast to predict
the first spring diatom phytoplankon bloom in the Strait of Georgia.
"""
import logging

import cliff.command


__all__ = ['Ensemble']


class Ensemble(cliff.command.Command):
    """run the ensemble bloomcast
    """
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.description = '''
            Run an ensemble forecast to predict  the first spring diatom
            phytoplanton bloom in the Strait of Georgia.
        '''
        return parser

    def take_action(self, parsed_args):
        pass
