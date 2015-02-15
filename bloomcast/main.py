# Copyright 2011-2015 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SoG-bloomcast application.

Operational prediction of the Strait of Georgia spring phytoplankton bloom

This module is connected to the `bloomcast` command via a console_scripts
entry point in setup.py.
"""
import sys

import cliff.app
import cliff.commandmanager

from . import __pkg_metadata__


__all__ = [
    'BloomcastApp', 'main',
]


class BloomcastApp(cliff.app.App):
    CONSOLE_MESSAGE_FORMAT = '%(levelname)s:%(name)s:%(message)s'

    def __init__(self):
        app_namespace = 'bloomcast.app'
        super(BloomcastApp, self).__init__(
            description=__pkg_metadata__.DESCRIPTION,
            version=__pkg_metadata__.VERSION,
            command_manager=cliff.commandmanager.CommandManager(app_namespace),
        )


def main(argv=sys.argv[1:]):
    app = BloomcastApp()
    return app.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
