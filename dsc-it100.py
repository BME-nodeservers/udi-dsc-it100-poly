#!/usr/bin/env python3
"""
Polyglot v2 node server for DSC alarm panel control/status via IT-100
Copyright (C) 2020 Robert Paauwe
"""
import sys
import time
try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
from nodes import dsc
from nodes import zone

LOGGER = polyinterface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('DSC')
        polyglot.start()
        control = dsc.Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

