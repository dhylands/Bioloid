"""This module implements a socket bus class which talks to bioloid
devices through a network socket.

"""

import select
import socket

from bioloid.bus import Bus

class SocketBus(Bus):
    """Implements a BioloidBus which sends commands to a bioloid device
    via a BioloidSerialPort.

    """

    def __init__(self, show_packets=False):
        Bus.__init__(self, show_packets)

        IP_ADDR = '127.0.0.1'
        IP_PORT = 8888
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((IP_ADDR, IP_PORT))

    def read_byte(self):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.

        """
        readable, _, _ = select.select([self.socket.fileno()], [], [], 0.1)
        if readable:
            data = self.socket.recv(1)
            if data:
                return ord(data[0])

    def write_packet(self, packet_data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        """
        self.socket.send(packet_data)
