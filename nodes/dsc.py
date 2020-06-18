#!/usr/bin/env python3
"""
Polyglot v2 node server DSC alarm panel status and control via IT-100
Copyright (C) 2020 Robert Paauwe
"""

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import time
import datetime
import requests
import threading
import socket
import math
import protocol
import it100
import node_funcs
from nodes import zone

LOGGER = polyinterface.LOGGER

@node_funcs.add_functions_as_methods(node_funcs.functions)
class Controller(polyinterface.Controller):
    id = 'dsc'
    hint = [0,0,0,0]

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'DSC'
        self.address = 'dsc'
        self.primary = self.address
        self.configured = False
        self.dsc = None
        self.mesg_thread = None
        self.source_status = 0x00 # assume all sources are inactive

        self.params = node_funcs.NSParameters([{
            'name': 'IP Address',
            'default': 'set me',
            'isRequired': True,
            'notice': 'IP Address of serial network interface must be set',
            },
            {
            'name': 'Port',
            'default': '0',
            'isRequired': True,
            'notice': 'Serial network interface port must be set',
            },
            {
            'name': 'Zone 1',
            'default': 'Zone 1',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 2',
            'default': 'Zone 2',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 3',
            'default': 'Zone 3',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 4',
            'default': 'Zone 4',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 5',
            'default': 'Zone 5',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 6',
            'default': 'Zone 6',
            'isRequired': False,
            'notice': '',
            },
            ])

        self.poly.onConfig(self.process_config)

    # Process changes to customParameters
    def process_config(self, config):
        (valid, changed) = self.params.update_from_polyglot(config)
        if changed and not valid:
            LOGGER.debug('-- configuration not yet valid')
            self.removeNoticesAll()
            self.params.send_notices(self)
        elif changed and valid:
            LOGGER.debug('-- configuration is valid')
            self.removeNoticesAll()
            self.configured = True
            # TODO: Run discovery/startup here?
        elif valid:
            LOGGER.debug('-- configuration not changed, but is valid')
            # is this necessary
            #self.configured = True

    def start(self):
        LOGGER.info('Starting node server')
        self.set_logging_level()
        self.check_params()

        # Open a connection to the IT-100
        if self.configured:
            self.dsc = it100.DSCConnection(self.params.get('IP Address'), self.params.get('Port'))
            self.dsc.Connect()

            self.discover()

            if self.dsc.connected:
                # Start a thread that listens for messages from the russound.
                self.mesg_thread = threading.Thread(target=self.dsc.Loop, args=(self.processCommand,))
                self.mesg_thread.daemon = True
                self.mesg_thread.start()

                # status update
                self.dsc.StatusRequest()

            LOGGER.info('Node server started')
        else:
            LOGGER.info('Waiting for configuration to be complete')

    def longPoll(self):
        pass

    def shortPoll(self):
        pass

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        LOGGER.debug('in discover() - Setting up zones')
        for z in range(1,17):
            param = 'Zone ' + str(z)
            node = zone.Zone(self, self.address, 'zone_' + str(z), self.params.get(param))
            node.connection(self.dsc)

            try:
                old = self.poly.getNode('zone_' + str(z))
                if old['name'] != self.params.get(param):
                    self.delNode('zone_' + str(z))
                    time.sleep(1)  # give it time to remove from database
            except:
                LOGGER.warning('Failed to delete node ' + param)

            self.addNode(node)

    # Delete the node server from Polyglot
    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def update_profile(self, command):
        st = self.poly.installprofile()
        return st

    def check_params(self):
        # NEW code, try this:
        self.removeNoticesAll()

        if self.params.get_from_polyglot(self):
            LOGGER.debug('All required parameters are set!')
            self.configured = True
        else:
            LOGGER.debug('Configuration required.')
            LOGGER.debug('IP Address = ' + self.params.get('IP Address'))
            LOGGER.debug('Port = ' + self.params.get('Port'))
            self.params.send_notices(self)

    def remove_notices_all(self, command):
        self.removeNoticesAll()

    def processCommand(self, msg):
        if msg.command == protocol.MSG_ZONE_OPEN:
            zone = int(msg.data.decode())
            LOGGER.warning('   zone {} open'.format(zone))
        elif msg.command == protocol.MSG_ZONE_RESTORED:
            zone = int(msg.data.decode())
            LOGGER.warning('   zone {} closed'.format(zone))
        elif msg.command == protocol.MSG_LCD_UPDATE: # LCD update
            LOGGER.warning('   message = ' + str(msg.data[5:].decode()))
        else:
            LOGGER.warning('command = {}'.format(msg.command))


    def set_logging_level(self, level=None):
        if level is None:
            try:
                level = self.get_saved_log_level()
            except:
                LOGGER.error('set_logging_level: get saved level failed.')

            if level is None:
                level = 10
            level = int(level)
        else:
            level = int(level['value'])

        self.save_log_level(level)

        LOGGER.info('set_logging_level: Setting log level to %d' % level)
        LOGGER.setLevel(level)


    commands = {
            'UPDATE_PROFILE': update_profile,
            'REMOVE_NOTICES_ALL': remove_notices_all,
            'DEBUG': set_logging_level,
            }

    # For this node server, all of the info is available in the single
    # controller node.
    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 2},   # node server status
            {'driver': 'GV1', 'value': 0, 'uom': 25},  # source 1 On/off status
            {'driver': 'GV2', 'value': 0, 'uom': 25},  # source 2 On/off status
            {'driver': 'GV3', 'value': 0, 'uom': 25},  # source 3 On/off status
            {'driver': 'GV4', 'value': 0, 'uom': 25},  # source 4 On/off status
            {'driver': 'GV5', 'value': 0, 'uom': 25},  # source 5 On/off status
            {'driver': 'GV6', 'value': 0, 'uom': 25},  # source 6 On/off status
            ]

