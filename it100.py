import logging
import time
import socket
import threading
import protocol

_LOGGER = logging.getLogger(__name__)

class DSCConnection:
    def __init__(self, ipaddress, port):
        self.ip = ipaddress
        self.port = int(port)
        self.connected = False
        self.sock = None


    def processCommand(msg):
        logging.warning(' -> TODO: message ' + str(msg))

    ## Connect to the IT-100 via IP address (serial/IP adaptor)
    def Connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect(('192.168.92.56', 4999))
            self.sock.setblocking(False)
            logging.warning('Successfully connected to IT-100 via iTach.')
            self.connected = True
        except socket.error as msg:
            _LOGGER.error('Error trying to connect to IT-100 controller.')
            _LOGGER.error(msg)

    def Close(self):
        self.sock.close()
        self.sock = None
        self.connected = False

    def StatusRequest(self):
        cmd = protocol.DSCMessage(protocol.CMD_STATUS_REQUEST, b'')
        logging.warning('[{}]'.format(', '.join(hex(x) for x in cmd.serialize())))
        self.sock.send(cmd.serialize())

    def LabelRequest(self):
        cmd = protocol.DSCMessage(protocol.CMD_LABELS_REQUEST, b'')
        logging.warning('[{}]'.format(', '.join(hex(x) for x in cmd.serialize())))
        self.sock.send(cmd.serialize())

    def Loop(self, handler):
        # Main loop waits for messages from IT-100 and then processes them
        #status_request()
        buf = bytearray(100)
        st = 0
        while self.connected:
            try:
                tcp = self.sock.recv(4096)
                #logging.warning('len= %s data= %s', len(tcp), '[{}]'.format(', '.join(hex(x) for x in tcp)))

                data = tcp[0:]
                for b in data:
                    if b == 0x0a:  # looking for end byte
                        buf[st] = b
                        message = protocol.DSCMessage.deserialize(buf[0:st+1])
                        handler(message)
                        st = 0
                    else:
                        buf[st] = b
                        st += 1

            except BlockingIOError:
                _LOGGER.info('waiting on data')
                pass
            except ConnectionResetError as msg:
                _LOGGER.error('Connection error: ' + msg)
                self.connected = False



def process_line(data):
    message = protocol.DSCMessage.deserialize(data)

    if message.command == protocol.MSG_ZONE_OPEN:
        zone = int(message.data.decode())
        logging.warning('   zone {} open'.format(zone))
    elif message.command == protocol.MSG_ZONE_RESTORED:
        zone = int(message.data.decode())
        logging.warning('   zone {} closed'.format(zone))
    elif message.command == protocol.MSG_VERSION:
        v = message.data[0:2]
        s = message.data[2:4]
        logging.warning('  version {}.{}'.format(v.decode(), s.decode()))
    elif message.command == protocol.MSG_PARTITION_READY:
        partition = int(message.data.decode())
        logging.warning('  partition {} ready'.format(partition))
    elif message.command == protocol.MSG_PARTITION_NOT_READY:
        partition = int(message.data.decode())
        logging.warning('  partition {} not ready'.format(partition))
    elif message.command == protocol.MSG_PARTITION_BUSY:
        partition = int(message.data.decode())
        logging.warning('  partition {} busy'.format(partition))
    elif message.command == protocol.MSG_PARTITION_TROUBLE_RESTORED:
        partition = int(message.data.decode())
        logging.warning('  partition {} trouble restored'.format(partition))
    elif message.command == protocol.MSG_LED_STATUS:
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
        logging.warning('  LED {} is {}'.format(led[message.data[0]], led_status[message.data[1]]))
    elif message.command == protocol.MSG_LCD_UPDATE: # LCD update
        logging.warning('   line    = ' + str(message.data[0]))
        logging.warning('   column  = ' + str(message.data[1:3]))
        logging.warning('   number  = ' + str(message.data[3:5]))
        logging.warning('   message = ' + str(message.data[5:].decode()))
    else:
        logging.warning('command = {}'.format(message.command))



