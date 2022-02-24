"""This module provides the bioloid.Device class, which is used to
communicate with a real bioloid device.

"""

import logging

from bioloid import packet
from bioloid import bus


class DeviceRegister(object):
    """Links a register and device."""

    def __init__(self, dev, reg):
        self.dev = dev
        self.reg = reg

    def get(self):
        """Retrieves the value for the associated register from the
        associated device.

        """
        return self.reg.raw_to_val(self.dev.read_reg(self.reg))

    def set(self, value, deferred=False):
        """Sets the value for the associated register on the
        associated device.

        """
        self.dev.write_reg(self.reg, self.reg.val_to_raw(value), deferred)


class Device(object):
    """Base class for communicating with a bioloid device."""

    def __init__(self, dev_bus=None, dev_id=None, dev_type=None, log=None):
        self.bus = dev_bus
        self.dev_id = dev_id
        self.dev_type = dev_type
        self.log = log or logging.getLogger(__name__)

    def set_bus_and_id(self, dev_bus, dev_id):
        """Sets the bus and id of the real bioloid device that this object
        is associated with.

        """
        self.bus = dev_bus
        self.dev_id = dev_id

    def set_dev_type(self, dev_type):
        """Sets the device type associated with this device."""
        self.dev_type = dev_type

    def get_dev_id(self):
        """Returns the device id associated with this device object."""
        return self.dev_id

    def get_dev_reg(self, name):
        """Returns a device register linking the named register and
        ths device.

        """
        if not self.dev_type:
            return None
        reg = self.dev_type.get_register_by_name(name)
        if not reg:
            return None
        return DeviceRegister(self, reg)

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
            self.bus.read_status_packet()
        except bus.BusError as ex:
            if ex.get_error_code() == packet.ErrorCode.TIMEOUT:
                return False
            raise
        return True

    def read(self, offset, num_bytes):
        """Sends a READ request and returns data read.

        Raises a bus.Error if any errors occur.

        """
        self.send_read(offset, num_bytes)
        pkt = self.bus.read_status_packet()
        return pkt.params()

    def read_reg(self, reg):
        """Reads a register value. Returns the value read.

        Raises a bus.Error if any errors occur.

        """
        data = self.read(reg.offset(), reg.size())
        val = data[0]
        if reg.size() > 1:
            val += data[1] * 256
        return val

    def write(self, offset, data, deferred=False):
        """Sends a WRITE request if deferred is False, or a REG_WRITE
        request if deferred is True.

        Raises a bus.Error if any errors occur.

        """
        self.send_write(offset, data, deferred)
        if self.dev_id == packet.Id.BROADCAST:
            return packet.ErrorCode.NONE
        self.bus.read_status_packet()

    def write_reg(self, reg, val, deferred=False):
        """Sends a WRITE request. Returns the error code.

        Raises a bus.Error if any errors occur.

        """
        data = bytes([val % 256])
        if reg.size() > 1:
            data += bytes([val // 256])
        err = self.write(reg.offset(), data, deferred)
        return err

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
        if self.dev_id == packet.Id.BROADCAST:
            return packet.ErrorCode.NONE
        self.bus.read_status_packet()

    ##########################################################################
    #
    # SendXxx functions send a packet containing the corresponding command,
    # but do not wait for a result.
    #
    ##########################################################################

    def send_ping(self):
        """Sends a ping command to this device."""
        self.log.debug("Sending PING to ID %d", self.dev_id)
        self.bus.send_cmd_header(self.dev_id, 0, packet.Command.PING)
        self.bus.send_checksum()

    def send_read(self, offset, num_bytes):
        """Sends a READ request to read data from the device's control
        table.

        """
        self.log.debug("Sending READ to ID %d offset 0x%02x len %d",
                       self.dev_id, offset, num_bytes)
        self.bus.send_cmd_header(self.dev_id, 2, packet.Command.READ)
        self.bus.send_byte(offset)
        self.bus.send_byte(num_bytes)
        self.bus.send_checksum()

    def send_write(self, offset, data, deferred=False):
        """Sends a WRITE request if deferred is False, or REG_WRITE
        request if deferred is True to write data into the device's
        control table.

        """
        self.log.debug("Sending WRITE to ID %d offset 0x%02x len %d",
                       self.dev_id, offset, len(data))
        cmd = packet.Command.REG_WRITE if deferred else packet.Command.WRITE
        self.bus.send_cmd_header(self.dev_id, len(data) + 1, cmd)
        self.bus.send_byte(offset)
        self.bus.send_data(data)
        self.bus.send_checksum()

    def send_reset(self):
        """Sends a RESET command to the device, which causes it to reset the
           control tableto factory defaults."""
        self.log.debug("Sending RESET to ID %d", self.dev_id)
        self.bus.send_cmd_header(self.dev_id, 0, packet.Command.RESET)
        self.bus.send_checksum()

    def send_action(self):
        """Sends an ACTION command to the device, which causes the
        deferred writes to take place.

        """
        self.log.debug("Sending ACTION to ID %d", self.dev_id)
        self.bus.send_cmd_header(self.dev_id, 0, packet.Command.ACTION)
        self.bus.send_checksum()
