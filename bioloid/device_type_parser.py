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
        self.dev_types = dev_types
        self.dev_type_name = None
        self.model = None
        self.registers = None
        self.reg_offset = None
        self.reg_name = None
        self.reg_size = None
        self.reg_access = None
        self.reg_min = None
        self.reg_max = None
        self.line_num = 0
        self.filename = None
        self.error_encountered = False
        self.log = log or logging.getLogger(__name__)
        self.reset()

    def reset(self):
        """Sets the parser back to its default state."""
        self.dev_type_name = None
        self.model = None
        self.registers = []

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
        self.filename = filename
        self.line_num = 0
        self.error_encountered = False
        with open(filename) as bld_file:
            for line in bld_file:
                self.line_num += 1
                # Strip comments
                comment_idx = line.find("#")
                if comment_idx >= 0:
                    line = line[0:comment_idx]
                words = line.split()
                if len(words) == 0:
                    # Ignore blank lines
                    continue
                try:
                    self.parse_line(words)
                except ValueError as ex:
                    self.log.error("Error: file '%s' line %d: %s",
                                   self.filename, self.line_num, str(ex))
                    self.error_encountered = True
        return not self.error_encountered

    def parse_line(self, words):
        """Parses a single line from the file."""
        if DEBUG:
            self.log.debug("parse_line: %s", ' '.join(words))
        cmd = words.pop(0)
        if self.dev_type_name:
            if cmd in DeviceTypeParser.dev_type_cmds:
                DeviceTypeParser.dev_type_cmds[cmd](self, words)
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
        self.dev_type_name = words[0]

    def parse_model(self, words):
        """Parses the 'Model:' keyword."""
        if len(words) != 1:
            raise ValueError("Model: expecting 1 arguent")
        self.model = parse_int(words[0], "model")

    def parse_register(self, words):
        """Parses the Register: keyword."""
        if len(words) < 4:
            raise ValueError("Expecting offset, name, size, and access")
        self.reg_offset = parse_int(words.pop(0), "offset")
        self.reg_name = words.pop(0)
        self.reg_size = parse_int(words.pop(0), "size")
        if self.reg_size < 1 or self.reg_size > 2:
            raise ValueError("Register '%s' size must be 1 or 2. Found: %s"
                             % (self.reg_name, self.reg_size))
        self.reg_access = words.pop(0)
        if self.reg_access != "ro" and self.reg_access != "rw":
            raise ValueError("Register %s: access must be ro or rw. Found: %s"
                             % (self.reg_name, self.reg_access))
        self.reg_min = None
        self.reg_max = None
        if len(words) == 2 or len(words) == 3:
            self.reg_min = parse_int(words.pop(0), "min")
            self.reg_max = parse_int(words.pop(0), "max")
        elif len(words) > 1:
            raise ValueError("Register " + self.reg_name +
                             ": Expecting 'type' or 'min max type'. " +
                             "Found %d arguments" % len(words))
        reg_type = words[0] if len(words) > 0 else ""
        reg_class = get_register_class(reg_type)
        if reg_class is None:
            raise ValueError("Register %s: Unknown register type: '%s'"
                             % (self.reg_name, reg_type))
        reg = reg_class(self.reg_offset, self.reg_name, self.reg_size,
                        self.reg_access, self.reg_min, self.reg_max)
        self.registers.append(reg)

    def parse_end_device_type(self, words):
        """Parses the 'EndDeviceType' keyword."""
        if len(words) != 0:
            raise ValueError("EndDeviceType: not expecting any arguents")
        if self.error_encountered:
            raise ValueError("Not adding device type due to errors.")
        dev_type = DeviceType(self.dev_type_name, self.model,
                              self.registers)
        self.dev_types.add(dev_type)
        self.reset()

    dev_type_cmds = {
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
