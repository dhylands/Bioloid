"""This module provides the bioloid.Bus abstract base class for
implementing bioloid busses.

"""

import logging

from bioloid import packet
from bioloid.dumpmem import dump_mem


class BusError(Exception):
    """Exception which is raised when non-successful status packet."""

    def __init__(self, error_code, *args, **kwargs):
        self.error_code = error_code
        Exception.__init__(self, *args, **kwargs)

    def get_error_code(self):
        """Retrieves the error code associated with the exception."""
        return self.error_code

    def __str__(self):
        return "Rcvd Status: " + str(packet.ErrorCode(self.error_code))


class Bus(object):
    """Abstract base class for a bioloid bus.

    Essentially there is avbus for each UART (or other bus) which has
    bioloid devices attached.

    """

    def __init__(self, show_packets, log=None):
        self.show_packets = show_packets
        self.buffered_data = ""
        self.checksum = 0
        self.log = log or logging.getLogger(__name__)

    def set_log(self, log):
        """Sets the log to use for logging output."""
        self.log = log

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

        Rasises a bioloid.bus.BusError if an error occurs.

        """
        pkt = packet.Packet()
        while True:
            byte = self.read_byte()
            if byte is None:
                raise BusError(packet.ErrorCode.TIMEOUT)
            self.buffered_data += chr(byte)
            err = pkt.process_byte(byte)
            if err != packet.ErrorCode.NOT_DONE:
                break
        if err != packet.ErrorCode.NONE:
            self.log.error("Rcvd Status: %s" % packet.ErrorCode(err))
            raise BusError(err)
        if self.show_packets:
            dump_mem(self.buffered_data, prefix="R", show_ascii=False,
                     print_func=self.log.debug)
        err = pkt.error_code()
        if err != packet.ErrorCode.NONE:
            self.log.error("Rcvd Status: %s" % packet.ErrorCode(err))
            raise BusError(err)
        self.log.debug("Rcvd Status: %s" % packet.ErrorCode(err))
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

    def sync_write(self, dev_ids, reg_set, values, raw=False):
        """Sets up a synchroous write command.

        dev_ids should be an array of device ids.
        regs should be a register set (obtained from
        DeviceType.get_register_set_by_name())
        values should be a 2 dimensional array. The first dimension
        corresponds to the ids, and the second dimension corresponds to the
        registers.

        raises ValueError if the dimensionality of values is incorrect.

        """
        num_ids = len(dev_ids)
        num_regs = len(reg_set)
        if num_ids != len(values):
            raise ValueError("len(dev_ids) = %d must match len(values) = %d" %
                             (num_ids, len(values)))
        bytes_per_id = sum([reg.size() for reg in reg_set])
        param_len = num_ids * (bytes_per_id + 1) + 2
        self.log.debug("Sending SYNC_WRITE")
        self.send_cmd_header(packet.Id.BROADCAST, param_len,
                             packet.Command.SYNC_WRITE)
        self.send_byte(reg_set[0].offset())
        self.send_byte(bytes_per_id)
        for id_idx in range(num_ids):
            self.send_byte(dev_ids[id_idx])
            for reg_idx in range(num_regs):
                reg = reg_set[reg_idx]
                if raw:
                    raw_val = int(values[id_idx][reg_idx])
                else:
                    raw_val = reg.val_to_raw(values[id_idx][reg_idx])
                self.send_byte(raw_val & 0xff)
                if reg.size() > 1:
                    self.send_byte((raw_val >> 8) & 0xff)
        self.send_checksum()

    def send_action(self):
        """Broadcasts an action packet to all of the devices on the bus.
        This causes all of the devices to perform their deferred writes
        at the sam time.

        """
        self.log.debug("Sending ACTION")
        self.send_cmd_header(packet.Id.BROADCAST, 0, packet.Command.ACTION)
        self.send_checksum()

    def send_byte(self, byte):
        """Buffers a byte to be sent. This will automatically accumulate
        the byte into the checksum.

        """
        self.checksum += byte
        self.buffer_byte(byte)

    def send_checksum(self):
        """Send the checksum, which is the last byte of the packet."""
        self.send_byte(~self.checksum & 0xff)
        self.write_buffer()

    def send_cmd_header(self, dev_id, param_len, cmd):
        """Sends the command header, which is common to all of the
        commmands.

        The param_len will be incremented by 2 to cover the length and
        cmd bytes). This way the caller is only responsible for
        figuring out how many extra parameter bytes are being sent.

        """
        self.buffered_data = b''
        self.send_byte(0xff)
        self.send_byte(0xff)
        self.checksum = 0
        self.send_byte(dev_id)
        self.send_byte(param_len + 2)  # 1 for len, 1 for cmd
        self.send_byte(cmd)

    def send_data(self, data):
        """Sends all of the bytes found in 'data'."""
        for byte in data:
            self.send_byte(byte)

    def buffer_byte(self, byte):
        """Adds a byte to the buffer of data to send."""
        self.buffered_data += bytes([byte])

    def write_buffer(self):
        """Writes all of the buffered bytes to the serial port."""
        if self.show_packets:
            dump_mem(self.buffered_data, prefix="W", show_ascii=False,
                     print_func=self.log.debug)
        self.write_packet(self.buffered_data)
        self.buffered_data = ""

    def write_packet(self, packet_data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        It is expected that a derived function will actually implement
        this function.

        """
        raise NotImplementedError
