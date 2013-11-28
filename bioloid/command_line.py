"""This module implements a command line interface which allows the bioloid
devices to be  queried and manipulated.

"""

import sys
import logging

from cmd import Cmd
from bioloid import packet
from bioloid.device import Device
from bioloid.column import column_print
from bioloid.dumpmem import dump_mem
from bioloid.parse_utils import str_to_int


def trim(docstring):
    """Trims the leading spaces from docstring comments.

    From http://www.python.org/dev/peps/pep-0257/

    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


class CommandLineBase(Cmd):
    """Contains common customizations to the Cmd class."""

    _prompt_array = []
    _cmdloop_executed = False
    _quitting = False

    def __init__(self, log=None, *args, **kwargs):
        Cmd.__init__(self, *args, **kwargs)
        self.command = None
        try:
            import readline
            delims = readline.get_completer_delims()
            readline.set_completer_delims(delims.replace("-", ""))
        except ImportError:
            pass
        self._log = log or logging.getLogger(__name__)

    def add_completion_funcs(self, names, complete_func_name):
        """Helper function which adds a completion function for an array of
        command names.

        """
        for name in names:
            name = name.replace("-", "_")
            func_name = "complete_" + name
            cls = self.__class__
            try:
                getattr(cls, func_name)
            except AttributeError:
                setattr(cls, func_name, getattr(cls, complete_func_name))

    def emptyline(self):
        """We want empty lines to do nothing. By default they would repeat the
        previous command.

        """
        pass

    def auto_cmdloop(self, line):
        """If line is empty, then we assume that the user wants to enter
        commands, so we call cmdloop. If line is non-empty, then we assume
        that a command was entered on the command line, and we'll just
        execute it, and not hang around for user input. Things get
        interesting since we also used nested cmd loops. So if the user
        passes in "servo 15" we'll process the servo 15 using onecmd, and
        then enter a cmdloop to process the servo specific command. The
        logic in this function basically says that if we ever waited for
        user input (i.e. called cmdloop) then we should continue to call
        cmdloop until the user decides to quit. That way if you run
        "bioloid.py servo 15" and then press Control-D you'll get to the
        servo prompt rather than exiting the program.

        """
        try:
            if len(line) == 0:
                self.cmdloop()
            else:
                self.onecmd(line)
                if (CommandLineBase._cmdloop_executed and
                        not CommandLineBase._quitting):
                    self.cmdloop()
        except KeyboardInterrupt:
            print
            CommandLineBase._quitting = True
            return True
        if CommandLineBase._quitting:
            return True

    def onecmd(self, line):
        """Clean up some Control-D output. Call print so that the user's shell
        prompt starts on a new line.

        """
        if line == "EOF":
            print()
            CommandLineBase._prompt_array.pop()
            return True
        return Cmd.onecmd(self, line)

    def cmdloop(self, *args, **kwargs):
        """We override this to support auto_cmdloop."""
        CommandLineBase._cmdloop_executed = True
        self.prompt = " ".join(CommandLineBase._prompt_array) + "> "
        return Cmd.cmdloop(self, *args, **kwargs)

    def parseline(self, line):
        """Record the command that was executed. This also allows us to
         transform dashes back to underscores.

        """
        (command, arg, line) = Cmd.parseline(self, line)
        self.command = command
        command = command.replace("-", "_")
        return command, arg, line

    def completenames(self, text, *ignored):
        """Override completenames so we can support names which have a dash
        in them.

        """
        real_names = Cmd.completenames(self, text.replace("-", "_"), *ignored)
        return [string.replace("_", "-") for string in real_names]

    def do_help(self, arg):
        """List available commands with "help" or detailed help with
        "help cmd".

        """
        if not arg:
            return Cmd.do_help(self, arg)
        arg = arg.replace("-", "_")
        try:
            doc = getattr(self, 'do_' + arg).__doc__
            if doc:
                doc = doc.format(command=arg)
                self.stdout.write("%s\n" % trim(str(doc)))
                return
        except AttributeError:
            pass
        self.stdout.write("%s\n" % str(self.nohelp % (arg,)))
        return

    def print_topics(self, header, cmds, cmdlen, maxcol):
        """Transform underscores to dashes when we print the command names."""
        if isinstance(cmds, list):
            for i in range(len(cmds)):
                cmds[i] = cmds[i].replace("_", "-")
        Cmd.print_topics(self, header, cmds, cmdlen, maxcol)

    def do_quit(self, _):
        """Exits from the program."""
        CommandLineBase._quitting = True
        return True


class CommandLine(CommandLineBase):
    """Converts command lines into bioloid commands and sends them to a
    bioloid device.

    """

    def __init__(self, bus, dev_types, *args, **kwargs):
        CommandLineBase.__init__(self, *args, **kwargs)
        self._bus = bus
        self._dev_types = dev_types
        CommandLineBase._prompt_array.append("bioloid")
        Cmd.identchars += '-'
        # We use the device types as commands, so add a do_xxx where
        # xxx is the device type name.
        for dt_name in self._dev_types.get_names():
            dt_name = dt_name.replace("-", "_")
            func_name = "do_" + dt_name
            cls = self.__class__
            try:
                getattr(cls, func_name)
            except AttributeError:
                setattr(cls, func_name, getattr(cls, "cb_do_device_type"))
        self.add_completion_funcs(self._dev_types.get_names(),
                                  "cb_complete_device_type")
        self._scan_idx = 0
        self._scan_spin = "-\\|/"

    def cb_complete_device_type(self, text, line, begin_idx, end_idx):
        """Completion support for device types."""
        return [dt_name for dev_type in self._dev_types.get_names()
                if dt_name.startswith(text)]

    def cb_do_device_type(self, line):
        """bioloid> {command}

        Select the {command} device type to receive the next portion of the
        command.

        """
        dev_type_name = self.command
        dev_type = self._dev_types.get(dev_type_name)
        return DevTypeCommandLine(dev_type, self._bus).auto_cmdloop(line)

    def do_action(self, _):
        """bioloid> action

        Broadcasts an ACTION command on the bus. This will cause registered
        writes to be performed.

        """
        self._bus.send_action()

    def do_scan(self, line):
        """bioloid> scan

        Scans the bus, by sending ping commands to the indicated devices.
        If num_ids is not specified, then it is assumed to be 32. If num_ids
        is less than 100, then addresses from 0 to num_ids - 1, and 100 to
        100 + num_ids - 1 will be scanned. If num_ids is greater than 100,
        then ids from 0 to num_ids - 1 will be scanned. For devices that
        respond, The model number and version will be read and reported.

        bioloid> scan
        ID:  15 Model:    12 Version:    22
        ID:  18 Model:    12 Version:    22

        """
        if line:
            try:
                num_ids = int(line)
            except ValueError:
                self._log.error("expecting a numeric id")
                return
        else:
            num_ids = 32
        self._scan_idx = 0
        if num_ids < 100:
            servo_id_found = self._bus.scan(0, num_ids,
                                            self.cb_scan_dev_found,
                                            self.cb_scan_dev_missing)
            sensor_id_found = self._bus.scan(100, num_ids,
                                             self.cb_scan_dev_found,
                                             self.cb_scan_dev_missing)
            if not servo_id_found and not sensor_id_found:
                self._log.info("No devices found")
        else:
            if not self._bus.scan(0, num_ids,
                                  self.cb_scan_dev_found,
                                  self.cb_scan_dev_missing):
                self._log.info("No devices found")

    def cb_scan_dev_found(self, bus, dev):
        """This is called whenever the scan command finds a device."""
        # We want to read the model and version, which is at offset 0, 1,
        # and 2 so we do it with a single read.
        data = dev.read(0, 3)
        model = ord(data[0]) + ord(data[1]) * 256
        version = ord(data[2])
        self._log.info("ID: %3d Model: %5u Version: %5u",
                       dev.dev_id(), model, version)

    def cb_scan_dev_missing(self, bus, dev):
        """Called whenever a device fails to response."""
        sys.stdout.write("%c\r" % self._scan_spin[self._scan_idx])
        sys.stdout.flush()
        self._scan_idx += 1
        self._scan_idx %= len(self._scan_spin)

    def do_dev_types(self, _):
        """bioloid> dev-types

        Lists the device types that the program knows about.

        bioloid> dev-types
        servo      Model:    12 with 34 registers

        """
        for dev_type in self._dev_types:
            self._log.info("%-10s Model: %5u with %2d registers",
                           dev_type.name(), dev_type.model(),
                           dev_type.num_regs())


class DevTypeCommandLine(CommandLineBase):
    """Processes subcommands for device types (i.e. sensor or servo, etc.)"""

    def __init__(self, dev_type, bus, *args, **kwargs):
        CommandLineBase.__init__(self, *args, **kwargs)
        self._prompt_array.append(dev_type.name())
        self._dev_type = dev_type
        self._bus = bus
        self.add_completion_funcs(("reg", "reg-raw"), "cb_complete_reg_name")

    def cb_complete_reg_name(self, text, line, begin_idx, end_idx):
        """Completion function for completing a register name."""
        return [rn for rn in self._dev_type.get_register_names()
                if rn.startswith(text)]

    def onecmd(self, line):
        """See if the command looks like a number. This is useful if the
        user ran "bioloid.py servo" and then enters just the id.

        """
        try:
            id_str, rest, line = self.parseline(line)
            dev_id = int(id_str, 0)
            return DevTypeIdCommandLine(self._dev_type,
                                        self._bus, dev_id).auto_cmdloop(rest)
        except ValueError:
            return CommandLineBase.onecmd(self, line)

    def do_reg(self, _):
        """bioloid dev-type> reg

        Prints the registers associated with this device type. The min and
        max values are formatted based on their type.

        bioloid> servo reg
        Addr Size         Min       Max Type            Name
        ---- ---- ----------- --------- --------------- ------------------
        0x00 ro 2                                       model
        0x02 ro 1                                       version
        0x03 rw 1           0       253                 id
        0x04 rw 1 2000000 bps  7843 bps BaudRate        baud-rate
        0x05 rw 1      0 usec  508 usec RDT             return-delay-time
        0x06 rw 2       0 deg   300 deg Angle           cw-angle-limit
        0x08 rw 2       0 deg   300 deg Angle           ccw-angle-limit
        ...
        0x2f rw 1           0         1                 lock
        0x30 rw 2           0      1023                 punch

        """
        self._dev_type.dump_regs()

    def do_reg_raw(self, _):
        """bioloid> dev-type reg-raw

        Prints the registers associated with this device type. The min and
        max values are formatted using their raw values.

        bioloid> servo reg-raw
        Addr Size Min  Max Type            Name
        ---- ---- --- ---- --------------- ------------------
        0x00 ro 2                          model
        0x02 ro 1                          version
        0x03 rw 1   0  253                 id
        0x04 rw 1   0  254 BaudRate        baud-rate
        0x05 rw 1   0  254 RDT             return-delay-time
        0x06 rw 2   0 1023 Angle           cw-angle-limit
        0x08 rw 2   0 1023 Angle           ccw-angle-limit
        ...
        0x2f rw 1   0    1                 lock
        0x30 rw 2   0 1023                 punch

        """
        self._dev_type.dump_regs_raw()


class DevTypeIdCommandLine(CommandLineBase):
    """Processes subcommands for device types followed by an id.

    (i.e. sensor 7 ping)

    """

    def __init__(self, devType, bus, dev_id, *args, **kwargs):
        CommandLineBase.__init__(self, *args, **kwargs)
        self._dev_type = devType
        self._bus = bus
        self._dev_id = dev_id
        CommandLineBase._prompt_array.append(str(dev_id))
        self._dev = Device(bus, dev_id)
        self.add_completion_funcs(("get", "get-raw", "set", "set-raw",
                                   "read-data", "rd", "write-data", "wd",
                                   "reg-write", "rw", "reg", "reg-raw"),
                                  "cb_complete_reg_name")

    def cb_complete_reg_name(self, text, line, begin_idx, end_idx):
        """Provides completion for register names."""
        return [rn for rn in self._dev_type.get_register_names()
                if rn.startswith(text)]

    def do_ping(self, _):
        """bioloid> device-type id ping

        Sends a PING command to the indicated device.

        """
        if not self._dev.ping():
            self._log.error("device %d not responding", self._dev.dev_id())

    def get_reg(self, reg_name, raw):
        """Retrieves a (or all) register from the device and prints the
        value.

        If 'raw' is true then raw register values will be printed,
        otherwise formatted values will be printed.

        """
        if self._dev_id == packet.Id.BROADCAST:
            self._log.error("Broadcast ID not valid with get command")
            return
        if reg_name != "all":
            reg = self._dev_type.get_register_by_name(reg_name)
            if not reg:
                self._log.error("Register '%s' not defined.", reg_name)
                return
            val = self._dev.read_reg(reg)
            self._log.info(reg.fmt(val))
            return
        lines = [['Addr', 'Size', 'Value', 'Type', 'Name'], '-']
        for reg in self._dev_type.get_registers_ordered_by_offset():
            val = self._dev.read_reg(reg)
            if raw:
                val_str = reg.fmt_raw(val)
            else:
                val_str = reg.fmt(val)
            lines.append(["0x%02x" % reg.offset(),
                          "%s %d" % (reg.access(), reg.size()),
                          val_str,
                          reg.type(),
                          reg.name()])
        column_print("<<>< ", lines, print_func=self._log.info)

    def set_reg(self, line, raw):
        """Sets a register to a value. 'raw' determines if the value is a raw
        register value, or a "formatted" value.

        """
        args = line.split()
        if len(args) != 2:
            self._log.error("Expecting 2 arguments, found %d", len(args))
            return
        reg = self._dev_type.get_register_by_name(args[0])
        if reg is None:
            self._log.error("Expecting register-name or numeric offset. " +
                            "Found '%s'", args[0])
            return
        if raw:
            val = reg.parse_raw(args[1])
        else:
            val = reg.parse(args[1])
        if val is not None:
            self._dev.write_reg(reg, val)

    def parse_offset_and_data(self, line):
        """Parses a register offset (or name) and raw bytes to write into
        the control table.

        """
        args = line.split()
        if len(args) < 2:
            self._log.error("Expecting offset and at least 1 " +
                            "additional value.")
            return None, None
        offset = self._dev_type.get_offset_by_name(args[0])
        if offset is None:
            self._log.error("Expecting register-name or numeric offset. " +
                            "Found '%s'", args[0])
            return None, None
        data = ""
        for byte_str in args[1:]:
            byte = str_to_int(byte_str)
            if byte is None:
                self._log.error("Expecting numeric value. Found '%s'",
                                byte_str)
                return None, None
            if byte < 0 or byte > 255:
                self._log.error("Expecting value to be in range 0-255. " +
                                "Found: %d", byte)
                return None, None
            data += byte
        return offset, data

    def do_get(self, line):
        """bioloig> device-type id get offset-or-register-name

        Retrieves the named register from the device indicated by 'id',
        and formats the result based on the register type. There is a
        special register name called 'all' which will cause all of the
        registers to be retrieved and printed.

        > servo 15 get present-voltage
        Read: 11.7 volts
        > servo 15 get all
        Addr Size Value           Name
        ---- ---- --------------- --------------------
        0x00 ro 2 12              model
        0x02 ro 1 22              version
        0x03 rw 1 15              id
        0x04 rw 1 1000000 baud    baud-rate
        ...

        """
        self.get_reg(line, raw=False)

    def do_get_raw(self, line):
        """bioloid> device-type id get-raw offset-or-register-name

        Retrieves the named register from the device indicated by 'id',
        and prints the raw register value. There is a special register
        name called 'all' which will cause all of the registers to be
        retrieved and printed.

        > servo 15 get-raw present-voltage
        Read:   117

        """
        self.get_reg(line, raw=True)

    def do_set(self, line):
        """bioloid> dev-type id set offset-or-register-name value

        Sets the value of a register using the natural units of the
        register type (degrees, volts, etc).

        """
        self.set_reg(line, raw=False)

    def do_set_raw(self, line):
        """bioloid> device-type id set offset-or-register-name value

        Sets the raw value of a register.

        """
        self.set_reg(line, raw=True)

    def do_read_data(self, line):
        """bioloid> device-type id read-data offset-or-register-name len

        Issues the READ_DATA command to the inidcated device. The data
        which is read is formatted as hex bytes.

        > servo 15 read-data 0x1e 4
        Read: 001e: AA 02 00 00

        """
        args = line.split()
        if len(args) != 2:
            self._log.error("Expecting offset and length.")
            return
        offset = self._dev_type.get_offset_by_name(args[0])
        if offset is None:
            self._log.Error("Expecting register name or numeric offset. " +
                            "Found '%s'", args[0])
            return
        data_len = str_to_int(args[1])
        if data_len is None:
            self._log.error("Expecting numeric length, found '%s'", args[1])
            return
        if data_len < 0 or data_len > 255:
            self._log.error("Expecting length to be betweeen 0 and 255. " +
                            "Found: %d", data_len)
            return
        data = self._dev.read(offset, data_len)
        dump_mem(data, prefix="Read", show_ascii=False,
                 print_func=self._log.info)

    def do_rd(self, line):
        """bioloid> device-type id rd offset-or-register-name len

        Alias for read-data.

        """
        return self.do_read_data(line)

    def do_write_data(self, line):
        """bioloid> device-type id write-data offset-or-register-name data ...

        Issues the WRITE_DATA command to the indicated device. The data
        is parsed as individual bytes, and may be in decimal, octal (if
        prefixed with a 0), or hexadecimal (if prefixed with a 0x).

        """
        offset, data = self.parse_offset_and_data(line)
        if offset is None:
            return
        self._dev.write(offset, data)

    def do_wd(self, line):
        """bioloid> device-type id wd offset-or-register-name data ...

        Alias for write-data."""
        return self.do_write_data(line)

    def do_reg_write(self, line):
        """bioloid> device-type id reg-wite offset-or-register-name data ...

        Issues the REG_WRITE command to the indicated device. The data
        is parsed as individual bytes, and may be in decimal, octal (if
        prefixed with a 0), or hexadecimal (if prefixed with a 0x).

        """
        offset, data = self.parse_offset_and_data(line)
        if offset is None:
            return
        self._dev.deferred_write(offset, data)

    def do_rw(self, line):
        """bioloid> device-type id rw offset data ...

        Alias for reg-write.

        """
        return self.do_reg_write(line)

    def do_reset(self, _):
        """bioloid> device-type id reset

        Issues the RESET command to the indicated device. This causes the
        device to reset all of the control table values to their default
        values.

        """
        self._dev.reset()

    def do_reg(self, _):
        """bioloid> dev-type id reg

        Alias for reg command at the device type level (you're currently
        at the device level).

        """
        self._dev_type.dump_regs()

    def do_reg_raw(self, _):
        """bioloid> dev-type id reg-raw

        Alias for reg-raw command at the device type level (you're
        currently at the device level).

        """
        self._dev_type.dump_regs_raw()
