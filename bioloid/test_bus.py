"""This module implements a test bus, which can be used for testing the
command line program.

To use this, queue up expected packets to be sent, expected responses, and
optionally, timeouts.

When sending a packet, write_buffered_data verifies that data matches the
command packet at the front of the queue, and read_ byte returns data
from the response packet at the front of the queue.

"""

from bioloid.bus import Bus


class TestBus(Bus):
    """Implements a BioloidBus which sends commands to a bioloid device
    via a BioloidSerialPort.

    """

    def __init__(self, show_packets=False):
        Bus.__init__(self, show_packets)

    def queue_cmd(self, packet):
        pass

    def queue_response(self, packet):
        pass

    def read_byte(self):
        pass

    def write_buffered_data(self, data):
        pass
