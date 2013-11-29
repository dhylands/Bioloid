"""This module defines the packets sent to and from the devices on the
bioloid bus.

"""

import logging

from bioloid.dumpmem import dump_mem


class Id(object):
    """Constants for reserved IDs."""

    BROADCAST = 0xFE
    INVALID = 0xFF

    idStr = {
        BROADCAST:  "BROADCAST",
        INVALID:    "INVALID"
    }

    def __init__(self, dev_id):
        self._dev_id = dev_id

    def __repr__(self):
        """Return a python parsable representation of ourselves."""
        return "Id(0x%02x)" % self._dev_id

    def __str__(self):
        """Return a human readable representation of ourselves."""
        if self._dev_id in Id.idStr:
            return Id.idStr[self._dev_id]
        return "0x%02x" % self._dev_id

    def dev_id(self):
        """Returns the device Id that this object represents."""
        return self._dev_id


class Command(object):
    """Constants for the commands sent in a packet."""

    PING = 0x01         # Used to obatin a status packet
    READ = 0x02         # Read values from the control table
    WRITE = 0x03        # Write values to control table
    REG_WRITE = 0x04    # Prime values to write when ACTION sent
    ACTION = 0x05       # Triggers REG_WRITE
    RESET = 0x06        # Changes control values back to factory defaults
    SYNC_WRITE = 0x83   # Writes values to many devices

    cmd_str = {
        PING:        "PING",
        READ:        "READ",
        WRITE:       "WRITE",
        REG_WRITE:   "REG_WRITE",
        ACTION:      "ACTION",
        RESET:       "RESET",
        SYNC_WRITE:  "SYNC_WRITE"
    }
    cmd_id = None

    def __init__(self, cmd):
        self._cmd = cmd

    def __repr__(self):
        """Return a python parsable representation of ourselves."""
        return "Bioloidcommand(0x%02x)" % self._cmd

    def __str__(self):
        """Return a human readable representation of ourselves."""
        if self._cmd in Command.cmd_str:
            return Command.cmd_str[self._cmd]
        return "0x%02x" % self._cmd

    @staticmethod
    def parse(string):
        if Command.cmd_id is None:
            Command.cmd_id = {}
            for cmd_id in Command.cmd_str:
                cmd_str = Command.cmd_str[cmd_id].lower()
                Command.cmd_id[cmd_str] = cmd_id
        string = string.lower()
        if string in Command.cmd_id:
            return Command.cmd_id[string]
        raise ValueError("Unrecognized command: '%s'" % string)


class ErrorCode(object):
    """Constants for the error codes used in response packets."""

    RESERVED = 0x80         # Reserved - set to zero
    INSTRUCTION = 0x40      # Undefined instruction
    OVERLOAD = 0x20         # Max torque can't control applied load
    CHECKSUM = 0x10         # Checksum of instruction packet incorrect
    RANGE = 0x08            # Instruction is out of range
    OVERHEATING = 0x04      # Internal temperature is too high
    ANGLE_LIMIT = 0x02      # Goal position is outside of limit range
    INPUT_VOLTAGE = 0x01    # Input voltage out of range
    NONE = 0x00             # No Error

    NOT_DONE = 0x100        # Special error code used by packet::ProcessChar
    TIMEOUT = 0x101         # Indicates that a timeout occurred while waiting
                            # for a reply
    TOO_MUCH_DATA = 0x102   # Packet storage isn't big enough

    lookup = ["InputVoltage", "AngleLimit", "OverHeating", "Range",
              "Checksum", "Overload", "Instruction", "Reserved"]
    lookupLower = None

    def __init__(self, error_code):
        self._error_code = error_code

    def __repr__(self):
        """Return a python parsable representation of ourselves."""
        return "ErrorCode(0x%02x)" % self._error_code

    def __str__(self):
        """Return a human readable representation of ourselves."""
        if self._error_code == ErrorCode.NONE:
            return "None"
        if self._error_code == ErrorCode.NOT_DONE:
            return "NotDone"
        if self._error_code == ErrorCode.TIMEOUT:
            return "Timeout"
        if self._error_code == ErrorCode.TOO_MUCH_DATA:
            return "TooMuchData"
        if self._error_code == 0x7f:
            return "All"
        result = []
        for i in range(len(ErrorCode.lookup)):
            if self._error_code & (1 << i):
                result.append(ErrorCode.lookup[i])
        return ",".join(result)

    @staticmethod
    def parse(error_str):
        """Parses a comma separated list of error strings to produce
        the corresponding mask or value.

        """
        if error_str.lower() == "none":
            return 0
        if error_str.lower() == "all":
            return 0x7f
        if ErrorCode.lookupLower is None:
            ErrorCode.lookupLower = [s.lower() for s in ErrorCode.lookup]
        result = 0
        for word in error_str.split(','):
            word = word.strip().lower()
            if word not in ErrorCode.lookupLower:
                raise ValueError("Invalid mask string '%s'" % word)
            result |= (1 << ErrorCode.lookupLower.index(word))
        return result


class Packet(object):
    """Encapsulates the packets sent to and from the bioloid device."""

    def __init__(self, log=None):
        """Constructs a packet from a bufffer, if provided."""
        self._state_func = self._state_idle
        self._cmd = None
        self._dev_id = None
        self._checksum = None
        self._param = None
        self._length = None
        self._log = log or logging.getLogger(__name__)

    def dev_id(self):
        """Returns the bioloid device Id from the packet."""
        return self._dev_id

    def length(self):
        """Returns the length of the packet, in bytes."""
        return self._length

    def command(self):
        """Retuns the command contained within the packet."""
        return self._cmd

    def param_byte(self, idx):
        """Returns the idx'th parameter byte."""
        return ord(self._param[idx])

    def params(self):
        """Returns all of the parameter bytes."""
        return self._param

    def param_len(self):
        """Returns the length of the parameter bytes."""
        return len(self._param)

    def error_code(self):
        """Returns the error code, from a response packet, which
        occupies the same position as the command.

        """
        return self._cmd

    def error_code_str(self):
        """Returns a string representation of the error code."""
        return str(ErrorCode(self._cmd))

    def checksum(self):
        """Returns the packet checksum."""
        return self._checksum

    def process_byte(self, char):
        """Runs a single byte through the packet parsing state
        machine.

        Returns ErrorCode.NOT_DONE if the packet is incomplete,
        ErrorCode.NONE if the packet was receivedsuccessfully, and
        ErrorCode.CHECKSUM if an error is detected.

        """
        return self._state_func(char)

    def _state_idle(self, char):
        """We're waiting for the next packet."""
        self._dev_id = Id.INVALID
        self._cmd = 0
        self._length = 0
        self._param = []
        if char == 0xFF:
            self._state_func = self._state_first_ff_rcvd
        return ErrorCode.NOT_DONE

    def _state_first_ff_rcvd(self, char):
        """We've received the first 0xFF and we're waiting for the
        second 0xFF.

        """
        if char == 0xFF:
            self._state_func = self._state_second_ff_rcvd
        else:
            self._state_func = self._state_idle
        return ErrorCode.NOT_DONE

    def _state_second_ff_rcvd(self, char):
        """We've received two 0xFFs and we're waiting for the ID."""
        if char != 0xFF:
            self._dev_id = char
            self._checksum = char
            self._state_func = self._state_id_rcvd
        # 0xFF isn't a valid ID, so just stay in this state until we
        # received a non 0xFF
        return ErrorCode.NOT_DONE

    def _state_id_rcvd(self, char):
        """We've received the ID and we're waiting for the length."""
        self._length = char
        self._checksum += char
        self._state_func = self._state_length_rcvd
        return ErrorCode.NOT_DONE

    def _state_length_rcvd(self, char):
        """We've received the length and we're waiting for the command."""
        self._cmd = char
        self._checksum += char
        self._state_func = self._state_cmd_rcvd
        self._param = []
        return ErrorCode.NOT_DONE

    def _state_cmd_rcvd(self, char):
        """We've received the command and we're waiting for the data."""
        if len(self._param) + 2 >= self._length:
            self._state_func = self._state_idle
            # char is the checksum
            self._checksum = ~self._checksum & 0xff
            if char == self._checksum:
                return ErrorCode.NONE
            self._log.error("Checksum Error: got 0x%02x expecting 0x%02x",
                            char, self.checksum)
            return ErrorCode.CHECKSUM
        self._checksum += char
        self._param.append(chr(char))
        return ErrorCode.NOT_DONE

    def dump_response(self):
        """Dumps the response packet received from a device."""
        self._log.info("ID:0x%02x Err: 0x%02x (%s)",
                       self.dev_id(), self.error_code(), self.error_code_str())
        if self.param_len() > 0:
            dump_mem(self.params(), prefix="  Rsp", show_ascii=False,
                     print_func=self._log.info)

    def dump_command(self):
        """Dumps the command packet destined for a device."""
        cmd = self.command()
        if cmd in Packet._dump_cmd_func:
            Packet._dump_cmd_func[cmd](self)
        else:
            self._log.error("Unrecognnized command: %d", cmd)

    def _dump_cmd_ping(self):
        """Dumps a PING command packet."""
        self._log.info("ID:0x%02x Cmd: PING", self.dev_id())

    def _dump_cmd_read(self):
        """Dumps a READ command packet."""
        self._log.info("ID:0x%02x Cmd: READ @ 0x%02x Len:%d",
                       self.dev_id(), self.param_byte(0), self.param_byte(1))

    def _dump_cmd_write(self):
        """Dumps a WRITE command packet."""
        self._log.info("ID:0x%02x Cmd: WRITE @ 0x%02x Len:%d",
                       self.dev_id(), self.param_byte(0), self.param_len() - 1)
        dump_mem(self.params()[1:], show_ascii=False,
                 print_func=self._log.info)

    def _dump_cmd_reg_write(self):
        """Dumps a REG_WRITE command packet."""
        self._log.info("ID:0x%02x Cmd: REG_WRITE @ 0x%02x Len:%d",
                       self.dev_id(), self.param_byte(0), self.param_len() - 1)
        dump_mem(self.params()[1:], show_ascii=False,
                 print_func=self._log.info)

    def _dump_cmd_action(self):
        """Dumps an ACTION command packet."""
        self._log.info("ID:0x%02x Cmd: ACTION", self.dev_id())

    def _dump_cmd_reset(self):
        """Dumps a RESET command packet."""
        self._log.info("ID:0x%02x Cmd: RESET", self.dev_id())

    def _dump_cmd_sync_write(self):
        """Dumps a SYNC_WRITE command packet."""
        param_len = self.param_byte(1)
        num_devs = (self.param_len() - 2) / (param_len + 1)
        self._log.info("ID:0x%02x Cmd: SYNC_WRITE @ 0x%02x " +
                       "Len:%d x %d devices",
                       self.dev_id(), self.param_byte(0), param_len, num_devs)
        param_idx = 2
        params = self.params()
        for _ in range(num_devs):
            id_str = "  ID:0x%02x" % self.param_byte(param_idx)
            dump_mem(params[param_idx + 1:param_idx + param_len + 1],
                     prefix=id_str, show_ascii=False, show_addr=False,
                     print_func=self._log.info)
            param_idx += (param_len + 1)

    _dump_cmd_func = {
        Command.PING:        _dump_cmd_ping,
        Command.READ:        _dump_cmd_read,
        Command.WRITE:       _dump_cmd_write,
        Command.REG_WRITE:   _dump_cmd_reg_write,
        Command.ACTION:      _dump_cmd_action,
        Command.RESET:       _dump_cmd_reset,
        Command.SYNC_WRITE:  _dump_cmd_sync_write
    }
