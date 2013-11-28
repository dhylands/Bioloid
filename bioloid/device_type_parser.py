"""Contains the DeviceTypeParser class, for parsing reg-*.bld files."""

import os
import fnmatch
import logging

from bioloid.device_type import DeviceTypes, DeviceType
from bioloid.register import get_register_class
from bioloid.parse_utils import parse_int

DEBUG = True


class DeviceTypeParser(object):
    """Parses a reg-*.bld file to create DeviceTypes."""

    def __init__(self, dev_types, log=None):
        self._dev_types = dev_types
        self._dev_type_name = None
        self._model = None
        self._registers = None
        self._reg_offset = None
        self._reg_name = None
        self._reg_size = None
        self._reg_access = None
        self._reg_min = None
        self._reg_max = None
        self._line_num = 0
        self._filename = None
        self._error_encountered = False
        self._log = log or logging.getLogger(__name__)
        self.reset()

    def reset(self):
        """Sets the parser back to its default state."""
        self._dev_type_name = None
        self._model = None
        self._registers = []

    def parse_dev_type_files(self, dirname):
        """Finds all files in dir which match reg-*.bld and parses the files
        as device types.

        """
        for filename in os.listdir(dirname):
            fullname = os.path.join(dirname, filename)
            if not os.path.isfile(fullname):
                continue
            if fnmatch.fnmatch(filename, "reg-*.bld"):
                self.parse_file(fullname)

    def parse_file(self, filename):
        """Parses a file and adds parsed device types to the dev_types
        object passed into the constructor.

        """
        self._filename = filename
        self._line_num = 0
        self._error_encountered = False
        with open(filename) as bld_file:
            for line in bld_file:
                self._line_num += 1
                # Strip comments
                line = line[0:line.find("#")]
                words = line.split()
                if len(words) == 0:
                    # Ignore blank lines
                    continue
                try:
                    self.parse_line(words)
                except ValueError as ex:
                    self._log.error("Error: file '%s' line %d: %s",
                                    self._filename, self._line_num, str(ex))
                    self._error_encountered = True
        return not self._error_encountered

    def parse_line(self, words):
        """Parses a single line from the file."""
        if DEBUG:
            self._log.debug("parse_line: %s", ' '.join(words))
        cmd = words.pop(0)
        if self._dev_type_name:
            if cmd in DeviceTypeParser._dev_type_cmds:
                self._dev_type_cmds[cmd](self, words)
                return
            raise ValueError("Unrecognized keyword: %s" % cmd)
        if cmd == "DeviceType:":
            self.parse_device_type(words)
            return
        raise ValueError("Unexpected keyword outside a device type: %s" % cmd)

    def parse_device_type(self, words):
        """Parses the 'DeviceType:' keyword."""
        if len(words) != 1:
            raise ValueError("DeviceType: expecting 1 arguent")
        self._dev_type_name = words[0]

    def parse_model(self, words):
        """Parses the 'Model:' keyword."""
        if len(words) != 1:
            raise ValueError("Model: expecting 1 arguent")
        self._model = parse_int(words[0], "model")

    def parse_register(self, words):
        """Parses the Register: keyword."""
        if len(words) < 4:
            raise ValueError("Expecting offset, name, size, and access")
        self._reg_offset = parse_int(words.pop(0), "offset")
        self._reg_name = words.pop(0)
        self._reg_size = parse_int(words.pop(0), "size")
        if self._reg_size < 1 or self._reg_size > 2:
            raise ValueError("Register '%s' size must be 1 or 2. Found: %s"
                             % (self._reg_name, self._reg_size))
        self._reg_access = words.pop(0)
        if self._reg_access != "ro" and self._reg_access != "rw":
            raise ValueError("Register %s: access must be ro or rw. Found: %s"
                             % (self._reg_name, self._reg_access))
        self._reg_min = None
        self._reg_max = None
        if len(words) == 2 or len(words) == 3:
            self._reg_min = parse_int(words.pop(0), "min")
            self._reg_max = parse_int(words.pop(0), "max")
        elif len(words) > 1:
            raise ValueError("Register " + self._reg_name +
                             ": Expecting 'type' or 'min max type'. " +
                             "Found %d arguments" % len(words))
        reg_type = words[0] if len(words) > 0 else ""
        reg_class = get_register_class(reg_type)
        if reg_class is None:
            raise ValueError("Register %s: Unknown register type: '%s'"
                             % (self._reg_name, reg_type))
        reg = reg_class(self._reg_offset, self._reg_name, self._reg_size,
                        self._reg_access, self._reg_min, self._reg_max)
        self._registers.append(reg)

    def parse_end_device_type(self, words):
        """Parses the 'EndDeviceType' keyword."""
        if len(words) != 0:
            raise ValueError("EndDeviceType: not expecting any arguents")
        if self._error_encountered:
            raise ValueError("Not adding device type due to errors.")
        dev_type = DeviceType(self._dev_type_name, self._model,
                              self._registers)
        self._dev_types.add(dev_type)
        self.reset()

    _dev_type_cmds = {
        "Model:":           parse_model,
        "Register:":        parse_register,
        "EndDeviceType":    parse_end_device_type
    }


def test_main():
    """Test function."""
    from bioloid.log_setup import log_setup
    log_setup(cfg_path='../logging.cfg')
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    dev_types = DeviceTypes()
    parser = DeviceTypeParser(dev_types)
    parser.parse_file('../reg-servo.bld')
    dev_type = dev_types.get('servo')
    dev_type.dump_regs()


if __name__ == '__main__':
    test_main()
