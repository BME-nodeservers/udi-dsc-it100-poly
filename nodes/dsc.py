#!/usr/bin/env python3
"""
Polyglot v2 node server DSC alarm panel status and control via IT-100
Copyright (C) 2020 Robert Paauwe
"""

import polyinterface
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
        self.discovery_ok = False

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
            'default': 'Example Zone',
            'isRequired': False,
            'notice': '',
            },
            ])

        self.poly.onConfig(self.process_config)

    # Process changes to customParameters
    def process_config(self, config):
        LOGGER.error('process_config = {}'.format(config))
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
            if self.discovery_ok:
                self.discover()
        elif valid:
            LOGGER.debug('-- configuration not changed, but is valid')
            # is this necessary
            #self.configured = True

    def start(self):
        LOGGER.info('Starting node server')
        self.set_logging_level()
        self.check_params()

        self.discovery_ok = True

        # Open a connection to the IT-100
        if self.configured:
            self.dsc = it100.DSCConnection(self.params.get('IP Address'), self.params.get('Port'))
            self.dsc.Connect()

            self.discover()

            self.update_profile(' ')

            if self.dsc.connected:
                # Start a thread that listens for messages from the russound.
                self.mesg_thread = threading.Thread(target=self.dsc.Loop, args=(self.processCommand,))
                self.mesg_thread.daemon = True
                self.mesg_thread.start()

                # status update
                self.dsc.StatusRequest()
                self.dsc.LabelRequest()

            LOGGER.info('Node server started')
        else:
            LOGGER.info('Waiting for configuration to be complete')

    def longPoll(self):
        pass

    def shortPoll(self):
        if not self.mesg_thread.is_alive():
            LOGGER.info('DSC thread has stopped, restarting....')
            self.dsc.Close()
            self.dsc.Connect()
            self.mesg_thread = threading.Thread(target=self.dsc.Loop, args=(self.processCommand,))
            self.mesg_thread.daemon = True
            self.mesg_thread.start()

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        LOGGER.debug('in discover() - Setting up zones')
        for z in range(1,65):
            param = 'Zone ' + str(z)
            if self.params.get(param) == None:
                continue

            node = zone.Zone(self, self.address, 'zone_' + str(z), self.params.get(param))
            #node.connection(self.dsc)

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
        self.dsc.connected = False
        self.dsc.Close()

    def stop(self):
        LOGGER.info('Stopping node server')
        self.dsc.connected = False
        self.dsc.Close()

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
            zone_addr = 'zone_' + str(zone)
            LOGGER.warning('   zone {} open'.format(zone))
            if zone_addr in self.nodes:
                self.nodes[zone_addr].set_state(1)
        elif msg.command == protocol.MSG_ZONE_RESTORED:
            zone = int(msg.data.decode())
            zone_addr = 'zone_' + str(zone)
            LOGGER.warning('   zone {} closed'.format(zone))
            if zone_addr in self.nodes:
                self.nodes[zone_addr].set_state(0)
        elif msg.command == protocol.MSG_ZONE_ALARM:
            zone = int(msg.data[:-3].decode())
            zone_addr = 'zone_' + str(zone)
            LOGGER.warning('   zone {} in alarm'.format(zone))
            if zone_addr in self.nodes:
                self.nodes[zone_addr].set_state(2)
        elif msg.command == protocol.MSG_ZONE_ALARM_RESTORE:
            zone = int(msg.data[:-3].decode())
            zone_addr = 'zone_' + str(zone)
            LOGGER.warning('   zone {} alarm restore'.format(zone))
            if zone_addr in self.nodes:
                self.nodes[zone_addr].set_state(0)
        elif msg.command == protocol.MSG_LCD_UPDATE: # LCD update
            LOGGER.warning('   message = ' + str(msg.data[5:].decode()))
        elif msg.command == protocol.MSG_LCD_UPDATE: # LCD update
            LOGGER.warning('   message = ' + str(msg.data[5:].decode()))
        elif msg.command == protocol.MSG_ACK:
            LOGGER.debug('Ack')
        elif msg.command == protocol.MSG_SYSTEM_BELL_TROUBLE:
            self.setDriver('GV1', 1)
        elif msg.command == protocol.MSG_SYSTEM_BELL_RESTORED:
            self.setDriver('GV1', 0)
        elif msg.command == protocol.MSG_PANEL_BATTERY_TROUBLE:
            self.setDriver('GV2', 1)
        elif msg.command == protocol.MSG_PANEL_BATTERY_RESTORED:
            self.setDriver('GV2', 0)
        elif msg.command == protocol.MSG_PANEL_AC_TROUBLE:
            self.setDriver('GV3', 1)
        elif msg.command == protocol.MSG_PANEL_AC_RESTORED:
            self.setDriver('GV3', 0)
        elif msg.command == protocol.MSG_FTC_TROUBLE:
            self.setDriver('GV4', 1)
        elif msg.command == protocol.MSG_FTC_RESTORED:
            self.setDriver('GV4', 0)
        elif msg.command == protocol.MSG_GENERAL_SYSTEM_TAMPER:
            self.setDriver('GV5', 1)
        elif msg.command == protocol.MSG_GENERAL_SYSTEM_TAMPER_RESTORED:
            self.setDriver('GV5', 0)
        elif msg.command == protocol.MSG_PARTITION_READY:
            partition = int(msg.data.decode())
            LOGGER.warning('  partition {} ready'.format(partition))
        elif msg.command == protocol.MSG_PARTITION_NOT_READY:
            partition = int(msg.data.decode())
            LOGGER.warning('  partition {} not ready'.format(partition))
        elif msg.command == protocol.MSG_PARTITION_BUSY:
            partition = int(msg.data.decode())
            LOGGER.warning('  partition {} busy'.format(partition))
        elif msg.command == protocol.MSG_PARTITION_TROUBLE_RESTORED:
            partition = int(msg.data.decode())
            LOGGER.warning('  partition {} trouble restored'.format(partition))
        elif msg.command == protocol.MSG_LED_STATUS:
            led = {
                0x31:'Ready',
                0x32:'Armed',
                0x33:'Memory',
                0x34:'Bypass',
                0x35:'Trouble',
                0x36:'Program',
                0x37:'Fire',
                0x38:'Backlight',
                0x39:'AC',
                }
            led_status = {
                0x30:'OFF',
                0x31:'ON',
                0x32:'Flashing',
                }
            LOGGER.warning('  LED {} is {}'.format(led[msg.data[0]], led_status[msg.data[1]]))
        elif msg.command == protocol.MSG_LABELS:
            zone = int(msg.data[0:3].decode())
            label = msg.data[3:].decode()
            LOGGER.warning('Label: {} = {}'.format(zone, label))
        else:
            LOGGER.warning('command = {}'.format(msg.command))
            LOGGER.warning('   data = ' + ' '.join('{:02x}'.format(x) for x in msg.data))


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

