# Node definition for a alarm zone
# 

import udi_interface
import json
import time
import datetime

LOGGER = udi_interface.LOGGER

class Zone(udi_interface.Node):
    id = 'zone'
    #power_state = False

    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 25},       # zone status
            {'driver': 'GV0', 'value': 0, 'uom': 25},      # zone bypass
            ]


    def set_state(self, state):
        self.setDriver('ST', state, True, True, 25)

    def set_bypass(self, source):
        self.setDriver('GV0', source + 1, True, True, 25)

    def process_cmd(self, cmd=None):
        # {'address': 'zone_2', 'cmd': 'VOLUME', 'value': '28', 'uom': '56', 'query': {}}

        LOGGER.debug('ISY sent: ' + str(cmd))

    commands = {
            'DON': process_cmd,
            'DOF': process_cmd,
            }

