"""This module implements a test bus, which can be used for testing the
command line program.

To use this, queue up expected packets to be sent, expected responses, and
optionally, timeouts.

When sending a packet, write_buffered_data verifies that data matches the
command packet at the front of the queue, and read_ byte returns data
from the response packet at the front of the queue.

"""

import logging

from bioloid.bus import BusError, Bus
from bioloid.packet import ErrorCode
from bioloid.dumpmem import dump_mem


class TestError(Exception):
    """Error raised by this module when a test failure occurs."""
    pass


class TestPacket(object):
    """Implements a packet variant which knows what type of packet it is."""

    COMMAND = 0
    RESPONSE = 1
    TIMEOUT = 2

    def __init__(self, packet_type, data=None):
        self.pkt_type = packet_type
        self.pkt_data = data if data is not None else []

    def packet_type(self):
        """Returns the type of this packet."""
        return self.pkt_type

    def packet_data(self):
        """Returns the packet data associatedd with this packet."""
        return self.pkt_data

    def packet_size(self):
        """Returns the size of the packet in bytes. In this context size
           means the number of bytes which will be written on the wire.
        """
        return len(self.pkt_data)

    def compare_data(self, cmp_data):
        """Compares the packet data with the indicated data."""
        if len(cmp_data) != len(self.pkt_data):
            return False
        for i in range(len(cmp_data)):
            if cmp_data[i] != self.pkt_data[i]:
                return False
        return True


class TestBus(Bus):
    """Implements a BioloidBus which sends commands to a bioloid device
    via a BioloidSerialPort.

    """

    def __init__(self, show_packets=False, log=None):
        Bus.__init__(self, show_packets, log)
        self.pkt_queue = []
        self.pkt_data = []
        self.log = log or logging.getLogger(__name__)
        self.test_pass_count = 0
        self.test_fail_count = 0

        self.packets_read_count = 0
        self.packets_written_count = 0
        self.packet_bytes_read = 0
        self.packet_bytes_written = 0
        self.max_packet_size_read = 0;
        self.max_packet_size_written = 0;

    def get_pass_count(self):
        """Returns the number of tests that passed."""
        return self.test_pass_count

    def get_fail_count(self):
        """Returns the number of tests that failed."""
        return self.test_fail_count

    def test_passed(self):
        """Marks a test as passed and resets the queue."""
        self.log.good('=== PASS ===')
        self.test_pass_count += 1
        self.pkt_queue = []
        self.pkt_data = []

    def test_failed(self):
        """Marks a test as failed and resets the queue."""
        self.log.error('=== FAIL ===')
        self.test_fail_count += 1
        self.pkt_queue = []
        self.pkt_data = []

    def queue(self, packet):
        """Adds a packet to the end of the queue."""
        self.pkt_queue.append(packet)

    def read_status_packet(self):
        """Intercept exceptions so that our test framework can deal with
        them, and not cause the command framework to exit.

        """
        try:
            packet = Bus.read_status_packet(self)
            self.packets_read_count += 1
            self.packet_bytes_read += packet.packet_size()
            self.max_packet_size_read = max(packet.packet_size(), self.max_packet_size_read)
            return packet
        except BusError as ex:
            err = ex.get_error_code()
            if err == ErrorCode.TIMEOUT:
                self.log.error("Rcvd Status: %s" % ErrorCode(err))
            return None

    def read_byte(self):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        For the TestBus, we expect the packet at the front of the queue
        to be either a response packet, or a timeout packet.

        """
        if len(self.pkt_data) > 0:
            # There is still unread data from a packet previously taken
            # from the queue
            return self.pkt_data.pop(0)
        if len(self.pkt_queue) == 0:
            raise TestError("TestBus: packet queue is empty (unexpected)")
        pkt = self.pkt_queue.pop(0)
        if pkt.packet_type() == TestPacket.COMMAND:
            raise TestError("Expecting response packet, found command")
        if pkt.packet_type() == TestPacket.TIMEOUT:
            return None
        if pkt.packet_type() != TestPacket.RESPONSE:
            raise TestError("Unexpected packet type '%d'" % pkt.packet_type())

        for byte in pkt.packet_data():
            self.pkt_data.append(byte)
        self.packets_read_count += 1
        self.packet_bytes_read += pkt.packet_size()
        self.max_packet_size_read = max(pkt.packet_size(), self.max_packet_size_read)
        return self.pkt_data.pop(0)

    def write_packet(self, packet_data):
        """Writes a packet to the TestBus.

        For the TestBus, we expect the packet at the front of the queue
        to be a command packets. We compare this data to data from the
        queued packet to see if they're identical.

        """
        if len(self.pkt_queue) == 0:
            raise TestError("TestBus: packet queue is empty (unexpected)")
        pkt = self.pkt_queue.pop(0)
        if pkt.packet_type() == TestPacket.RESPONSE:
            raise TestError("Expecting command packet, found response")
        if pkt.packet_type() == TestPacket.TIMEOUT:
            raise TestError("Expecting command packet, found timeout")
        if pkt.packet_type() != TestPacket.COMMAND:
            raise TestError("Unexpected packet type '%d'" % pkt.packet_type())
        if not pkt.compare_data(packet_data):
            self.log.error("Found")
            dump_mem(packet_data, prefix="  F", show_ascii=False,
                     print_func=self.log.error)
            self.log.error("Expecting")
            dump_mem(pkt.packet_data(), prefix="  E", show_ascii=False,
                     print_func=self.log.error)
            raise TestError("write_packet: Unexpected packet written")
        self.packets_written_count += 1
        self.packet_bytes_written += pkt.packet_size()
        self.max_packet_size_written = max(pkt.packet_size(), self.max_packet_size_written)
