#!/usr/bin/env python3
"""
Polyglot v3 node server DSC alarm panel status and control via IT-100
Copyright (C) 2020,2021 Robert Paauwe
"""

import udi_interface
import sys
import time
import datetime
import requests
import threading
import socket
import math
import protocol
import it100
from nodes import zone

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom

class Controller(udi_interface.Node):
    id = 'dsc'

    def __init__(self, polyglot, primary, address, name):
        super(Controller, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.configured = False
        self.dsc = None
        self.mesg_thread = None
        self.discovery_ok = False
        self.zone_map = []

        self.Parameters = Custom(polyglot, 'customparams')
        self.Notices = Custom(polyglot, 'notices')

        self.poly.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(polyglot.START, self.start, address)
        self.poly.subscribe(polyglot.POLL, self.poll)

        self.poly.ready()
        self.poly.addNode(self)


    # Process changes to customParameters
    def parameterHandler(self, params):
        self.Parameters.load(params)
        self.configured = False
        validIP = False
        validPort = False

        self.Notices.clear()

        for p in self.Parameters:
            if 'IP Address' in p:
                if self.Parameters[p] is not '':
                    validIP = True
                else:
                    self.Notices['ip'] = 'IP Address of serial network interface must be set.'
            elif 'Port' in p:
                if self.Parameters[p] is not '':
                    validPort = True
                else:
                    self.Notices['port'] = 'Serial network interface port must be set.'
            elif 'Zone' in p:
                self.zone_map[p] = self.Parameters[p]

        if validIP and validPort:
            self.connect()
            # create nodes?
            self.discover()

            self.configured = True


    """
      Connect to the DSC IT 100 
    """
    def connect(self):
        self.dsc = it100.DSCConnection(self.Parameters['IP Address'], self.Parameters['Port'])
        self.dsc.Connect()

    def start(self):
        LOGGER.info('Starting node server')
        self.poly.setCustomParamsDoc()
        self.poly.updateProfile()

        while not self.configured:
            time.sleep(5)

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

    def poll(self, polltype):
        if 'longPoll' in polltype:
            return

        # Attempt to restart network connect if it drops
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
        for z in self.zone_map:
        for z in range(1,65):
            param = 'Zone ' + str(z)
            if self.Parameters[param]) is None:
                # TODO: Check and delete if neccessary zone
                continue

            node = zone.Zone(self, self.address, 'zone_' + str(z), self.Parameters[param])

            # TODO: check and rename if necessary zone
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



    commands = {
            }

    # For this node server, all of the info is available in the single
    # controller node.
    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 2},   # node server status
            {'driver': 'GV1', 'value': 0, 'uom': 25},  # system bell status
            {'driver': 'GV2', 'value': 0, 'uom': 25},  # panel battery status
            {'driver': 'GV3', 'value': 0, 'uom': 25},  # panel AC status
            {'driver': 'GV4', 'value': 0, 'uom': 25},  # FTC status
            {'driver': 'GV5', 'value': 0, 'uom': 25},  # General status
            ]

