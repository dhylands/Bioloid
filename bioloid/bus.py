"""This module provides the bioloid.Bus abstract base class for
implementing bioloid busses.

"""

import logging

from bioloid import packet
from bioloid.dumpmem import dump_mem


class Error(Exception):
    """Exception which is raised when non-successful status packet."""

    def __init__(self, error_code, *args, **kwargs):
        self._error_code = error_code
        Exception.__init__(self, *args, **kwargs)

    def error_code(self):
        """Retrieves the error code associated with the exception."""
        return self._error_code


class Bus(object):
    """Abstract base class for a bioloid bus.

    Essentially there is avbus for each UART (or other bus) which has
    bioloid devices attached.

    """

    def __init__(self, show_packets, log=None):
        self._show_packets = show_packets
        self._buffered_data = ""
        self._checksum = 0
        self._log = log or logging.getLogger(__name__)

    def read_byte(self):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.

        It is expected that a derived function will actually implement
        this function.

        """
        raise NotImplementedError

    def read_status_packet(self):
        """Reads a status packet and returns it.

        Rasises a bioloid.bus.Error if an error occurs.

        """
        pkt = packet.Packet()
        while True:
            byte = self.read_byte()
            if byte is None:
                raise Error(packet.ErrorCode.TIMEOUT)
            self._buffered_data += chr(byte)
            err = pkt.process_byte(byte)
            if err != packet.ErrorCode.NOT_DONE:
                break
        if err != packet.ErrorCode.NONE:
            self._log.error("Rcvd Status: %s" % packet.ErrorCode(err))
            raise Error(err)
        if self._show_packets:
            dump_mem(self._buffered_data, prefix="R", show_ascii=False,
                     print_func=self._log.debug)
        err = pkt.error_code()
        self._log.debug("Rcvd Status: %s" % packet.ErrorCode(err))
        return pkt

    def scan(self, start_id, num_ids, dev_found, dev_missing):
        """Scans the bus, calling devFound(self, dev) for each device
        which responds, and dev_missing(self, dev) for each device
        which doesn't.

        Returns true if any devices were found.

        """
        from bioloid.device import Device
        end_id = start_id + num_ids - 1
        if end_id >= packet.Id.BROADCAST:
            end_id = packet.Id.BROADCAST - 1
        dev = Device()
        some_dev_found = False
        for dev_id in range(start_id, end_id + 1):
            dev.set_bus_and_id(self, dev_id)
            if dev.ping():
                some_dev_found = True
                if dev_found:
                    dev_found(self, dev)
            else:
                if dev_missing:
                    dev_missing(self, dev)
        return some_dev_found

    def send_action(self):
        """Broadcasts an action packet to all of the devices on the bus.
        This causes all of the devices to perform their deferred writes
        at the sam time.

        """
        self._log.debug("Sending ACTION")
        self.send_cmd_header(packet.Id.BROADCAST, 0, packet.Command.ACTION)
        self.send_checksum()

    def send_byte(self, byte):
        """Buffers a byte to be sent. This will automatically accumulate
        the byte into the checksum.

        """
        self._checksum += byte
        self._buffer_byte(byte)

    def send_checksum(self):
        """Send the checksum, which is the last byte of the packet."""
        self.send_byte(~self._checksum & 0xff)
        self._write_buffer()

    def send_cmd_header(self, dev_id, param_len, cmd):
        """Sends the command header, which is common to all of the
        commmands.

        The param_len will be incremented by 2 to cover the length and
        cmd bytes). This way the caller is only responsible for
        figuring out how many extra parameter bytes are being sent.

        """
        self._buffered_data = ""
        self.send_byte(0xff)
        self.send_byte(0xff)
        self._checksum = 0
        self.send_byte(dev_id)
        self.send_byte(param_len + 2)  # 1 for len, 1 for cmd
        self.send_byte(cmd)

    def send_data(self, data):
        """Sends all of the bytes found in 'data'."""
        for byte in data:
            self.send_byte(ord(byte))

    def _buffer_byte(self, byte):
        """Adds a byte to the buffer of data to send."""
        self._buffered_data += chr(byte)

    def _write_buffer(self):
        """Writes all of the buffered bytes to the serial port."""
        if self._show_packets:
            dump_mem(self._buffered_data, prefix="W", show_ascii=False,
                     print_func=self._log.debug)
        self.write_buffered_data(self._buffered_data)
        self._buffered_data = ""

    def write_buffered_data(self, data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        It is expected that a derived function will actually implement
        this function.

        """
        raise NotImplementedError
