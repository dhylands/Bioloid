"""Encapsulates a type of bioloid device, like a sensor or servo."""

from bioloid.column import column_print
from bioloid.parse_utils import str_to_int

import logging

DEBUG = False


class DeviceTypes(object):
    """Container class for the registered device types."""

    def __init__(self):
        self._device_types = {}
        self._device_types_iter = None

    def __iter__(self):
        """For iteration purposes, we want to look like an array."""
        self._device_types_iter = sorted(list(self._device_types.values()),
                                         key=lambda dev_type: dev_type.name())
        return self._device_types_iter.__iter__()

    def __next__(self):
        """Forward iterator support to the dictionary."""
        return next(self._device_types_iter)

    def add(self, dev_type):
        """Adds a device type to the global collection of device types."""
        self._device_types[dev_type.name()] = dev_type

    def get(self, dev_type_name):
        """Returns the  nmed device type."""
        if dev_type_name in self._device_types:
            return self._device_types[dev_type_name]

    def get_names(self):
        """Returns a list containing all of the registered device types."""
        return sorted(self._device_types.keys())


class DeviceType(object):
    """Represents a type of bioloid device, like a servo or sensor.

    The device type knows about all of the registerswhich are used to
    access/manipulate the device.

    """

    def __init__(self, name, model, registers, log=None):
        self._name = name
        self._model = model
        self._registers = registers
        self._register_list_by_offset = None
        self._register_dict_by_name = None
        self._register_names = None
        self._log = log or logging.getLogger(__name__)

    def model(self):
        """Returns the model of  this device type."""
        return self._model

    def name(self):
        """Returns the name of this device type."""
        return self._name

    def num_regs(self):
        """Returns the number of registers this device type has."""
        return len(self._registers)

    def get_registers_ordered_by_offset(self):
        """Returns the registers associated with this device type,
        ordered by offset.

        """
        if not self._register_list_by_offset:
            self._register_list_by_offset = (
                sorted(self._registers, key=lambda reg: reg.offset()))
        return self._register_list_by_offset

    def get_register_names(self):
        """Returns the names of the registers associated with this
        device type.

        """
        if self._register_names is None:
            self._register_names = tuple(reg.name() for reg in self._registers)
        return self._register_names

    def get_register_by_name(self, name):
        """Retrives the named register."""
        if not self._register_dict_by_name:
            self._register_dict_by_name = {}
            for reg in self._registers:
                self._register_dict_by_name[reg.name()] = reg
        if name in self._register_dict_by_name:
            return self._register_dict_by_name[name]
        # Check to see name looks like an offset
        offset = str_to_int(name)
        if offset is not None:
            for reg in self._registers:
                if offset == reg.offset():
                    return reg
        return None

    def get_register_set_by_name(self, name, num_regs):
        """Returns an array of registers, verifying that they form a
        contigous set of registers.

        Raises KeyError if name isn't found in the registers.
        Raises ValueError if the registers aren't contiguous.

        """
        regs = self.get_registers_ordered_by_offset()
        reg_idx = -1
        for idx in range(len(regs)):
            if regs[idx].name() == name:
                reg_idx = idx
                break
        if reg_idx < 0:
            raise KeyError("Register '%s' not found in device type '%s'" %
                           (name, self.name()))
        if reg_idx + num_regs >= len(regs):
            raise ValueError("idx %d + num_regs %d exceeds %d" %
                             (reg_idx, num_regs, len(regs)))
        prev_offset = regs[reg_idx].offset()
        prev_size = regs[reg_idx].size()
        result = [regs[reg_idx]]
        for idx in range(reg_idx + 1, reg_idx + num_regs):
            curr_offset = regs[idx].offset()
            curr_size = regs[idx].size()
            if curr_offset != (prev_offset + prev_size):
                raise ValueError("Register '%s' not contiguou with '%s'" %
                                 (regs[idx].name(), regs[idx - 1].name()))
            result.append(regs[idx])
            prev_offset = curr_offset
            prev_size = curr_size
        return result

    def get_offset_by_name(self, name):
        """Returns the offset (within the control table) of the named
        register.

        """
        reg = self.get_register_by_name(name)
        if reg is None:
            # See if name is already an offset
            return str_to_int(name)
        return reg.offset()

    def dump_regs_raw(self):
        """Dumps the register definitions for all of the registers associated
        with this device type.

        """
        regs = self.get_registers_ordered_by_offset()
        lines = [['Addr', 'Size', 'Min', 'Max', 'Type', 'Name'], '-']
        for reg in regs:
            lines.append(["0x%02x" % reg.offset(),
                          "%s %d" % (reg.access(), reg.size()),
                          reg.fmt_raw(reg.min_raw()),
                          reg.fmt_raw(reg.max_raw()),
                          reg.type(),
                          reg.name()])
        column_print("<<>>< ", lines, print_func=self._log.info)

    def dump_regs(self):
        """Dumps the register definitions for all of the registers associated
        with this device type.

        """
        regs = self.get_registers_ordered_by_offset()
        lines = [['Addr', 'Size', 'Min', 'Max', 'Type', 'Name'], '-']
        for reg in regs:
            lines.append(["0x%02x" % reg.offset(),
                          "%s %d" % (reg.access(), reg.size()),
                          reg.fmt(reg.min_raw()),
                          reg.fmt(reg.max_raw()),
                          reg.type(),
                          reg.name()])
        column_print("<<>>< ", lines, print_func=self._log.info)
