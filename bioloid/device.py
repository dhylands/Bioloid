"""This module provides the bioloid.Device class, which is used to
communicate with a real bioloid device.

"""

import logging

from bioloid import packet
from bioloid import bus


class Device(object):
    """Base class for communicating with a bioloid device."""

    def __init__(self, dev_bus=None, dev_id=None, log=None):
        self._bus = dev_bus
        self._dev_id = dev_id
        self._log = log or logging.getLogger(__name__)

    def set_bus_and_id(self, dev_bus, dev_id):
        """Sets the bus and id of the real bioloid device that this object
        is associated with.

        """
        self._bus = dev_bus
        self._dev_id = dev_id

    def dev_id(self):
        """Returns the device id associated with this device object."""
        return self._dev_id

    ##########################################################################
    #
    # Commands which return an error code, and optionally data read.
    #
    ##########################################################################

    def ping(self):
        """Sends a PING request.

        Returns true if the device responds successfully, false if a timeout
        occurs, and raises a bus.Error for any other failures.

        raises a bioloid.bus.Error for any other failures.

        """
        self.send_ping()
        try:
            self._bus.read_status_packet()
        except bus.Error as ex:
            if ex.error_code() == packet.ErrorCode.TIMEOUT:
                return False
            raise
        return True

    def read(self, offset, num_bytes):
        """Sends a READ request and returns data read.

        Raises a bus.Error if any errors occur.

        """
        self.send_read(offset, num_bytes)
        pkt = self._bus.read_status_packet()
        return pkt.params()

    def read_reg(self, reg):
        """Reads a register value. Returns the value read.

        Raises a bus.Error if any errors occur.

        """
        data = self.read(reg.offset(), reg.size())
        val = ord(data[0])
        if reg.size() > 1:
            val += ord(data[1]) * 256
        return val

    def write(self, offset, data):
        """Sends a WRITE request.

        Raises a bus.Error if any errors occur.

        """
        self.send_write(offset, data)
        if self._dev_id == packet.Id.BROADCAST:
            return packet.ErrorCode.NONE
        self._bus.read_status_packet()

    def write_reg(self, reg, val):
        """Sends a WRITE request. Returns the error code.

        Raises a bus.Error if any errors occur.

        """
        data = ""
        data += chr(val % 256)
        if reg.size() > 1:
            data += chr(val / 256)
        err = self.write(reg.offset(), data)
        return err

    def deferred_write(self, offset, data):
        """Sends a REG_WRITE, which defers the wrrite until an ACTION
        command is sent. There is no response to a deferred write.

        """
        self.send_deferred_write(offset, data)

    def action(self):
        """Sends an ACTION command, which triggers previous deferred
        writes.

        The ACTION command is typically sent to the broadcast id.
        There is no response to this command.

        """
        self.send_action()

    def reset(self):
        """Sends a RESET request.

        Raises a bus.Error if any errors occur.

        """
        self.send_reset()
        if self._dev_id == packet.Id.BROADCAST:
            return packet.ErrorCode.NONE
        self._bus.read_status_packet()

    ##########################################################################
    #
    # SendXxx functions send a packet containing the corresponding command,
    # but do not wait for a result.
    #
    ##########################################################################

    def send_ping(self):
        """Sends a ping command to this device."""
        self._log.debug("Sending PING to ID %d", self._dev_id)
        self._bus.send_cmd_header(self._dev_id, 0, packet.Command.PING)
        self._bus.send_checksum()

    def send_read(self, offset, num_bytes):
        """Sends a READ request to read data from the device's control
        table.

        """
        self._log.debug("Sending READ to ID %d offset 0x%02x len %d",
                        self._dev_id, offset, num_bytes)
        self._bus.send_cmd_header(self._dev_id, 2, packet.Command.READ)
        self._bus.send_byte(offset)
        self._bus.send_byte(num_bytes)
        self._bus.send_checksum()

    def send_write(self, offset, data):
        """Sends a WRITE request to write data into the device's
        control table.

        """
        self._log.debug("Sending WRITE to ID %d offset 0x%02x len %d",
                        self._dev_id, offset, len(data))
        self._bus.send_cmd_header(self._dev_id, len(data) + 1,
                                  packet.Command.WRITE)
        self._bus.send_byte(offset)
        self._bus.send_data(data)
        self._bus.send_checksum()

    def send_deferred_write(self, offset, data):
        """Sends a REG_WRITE request to write data into the device's
        control table.

        """
        self._log.debug("Sending REG_WRITE to ID %d offset 0x%02x len %d",
                        self._dev_id, offset, len(data))
        self._bus.send_cmd_header(self._dev_id, len(data) + 1,
                                  packet.Command.REG_WRITE)
        self._bus.send_byte(offset)
        self._bus.send_data(data)
        self._bus.send_checksum()

    def send_reset(self):
        """Sends a RESET command to the device, which causes it to reset the
           control tableto factory defaults."""
        self._log.debug("Sending RESET to ID %d", self._dev_id)
        self._bus.send_cmd_header(self._dev_id, 0, packet.Command.RESET)
        self._bus.send_checksum()

    def send_action(self):
        """Sends an ACTION command to the device, which causes the
        deferred writes to take place.

        """
        self._log.debug("Sending ACTION to ID %d", self._dev_id)
        self._bus.send_cmd_header(self._dev_id, 0, packet.Command.ACTION)
        self._bus.send_checksum()
