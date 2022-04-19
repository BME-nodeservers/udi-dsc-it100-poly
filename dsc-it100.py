#!/usr/bin/env python3
"""
Polyglot v3 node server for DSC alarm panel control/status via IT-100
Copyright (C) 2020,2021 Robert Paauwe
"""
import sys
import time
import udi_interface
from nodes import dsc
from nodes import zone

LOGGER = udi_interface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start('2.0.1')
        dsc.Controller(polyglot, 'controller', 'controller', 'DSC')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

