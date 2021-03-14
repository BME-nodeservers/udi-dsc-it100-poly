
# DSC IT100 Polyglot

This is a DSC Alarm Poly for systems with a IT100 interface connected to a serial/IP bridge.
Designed to work with [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY)
[Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/)
Running on a [Polisy](https;//www.universal-devices.com/product/polisy/)

Copyright (c)2020,2021 Robert Paauwe

This node server is intended to provide basic support for a DSC PC 16xx alarm system with an IT100
serial interface.  It connects to the IT100 over a serial/ethernet bridge.

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Add NodeServer in Polyglot Web to a free slot.
4. From the Dashboard, select the DSC-IT100 node server and go to the configuration tab.
5. Configure the IP address and port of the serial/IP bridge device.
6. Configure the active zones by adding a key/value pair for each active zone.  The key
   must be the "Zone [n]" and the value is the name for the zone.  For example:
   *  "Zone 1"  "Front door"

### Node Settings
The settings for this node are:

#### Long Poll
   * Verify that the connection to the IT100 is still good and attempt to re-connect if necessar.

#### IP Address
   * The IP Address of the serial device server conected to the IT100. 
#### Port
   * The UDP/TCP port number assigned by the serial device server for the serial port.
#### Zone 1
   * The name for zone 1
#### Zone 2
   * The name for zone 2
#### Zone 64
   * The name for zone 64

## Requirements
1. Polyglot V3.
2. ISY firmware 5.3.x or later
3. A DSC alarm panel with IT100 interface

# Release Notes
- 2.0.0 03/14/2021
   - Ported to PG3
- 1.0.2 06/16/2020
   - Process undocumented message to get keypad source selection.
- 1.0.2 06/16/2020
   - Fix TCP networking code.
   - Fix get source info response.
- 1.0.1 06/10/2020
   - Add parameter for network protocol selection (UDP/TCP)
- 1.0.0 06/10/2020
   - Initial release to public github
