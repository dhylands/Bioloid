"""This module implements a command line interface which allows the bioloid
devices to be  queried and manipulated.

"""

import sys
import logging
import shlex

from cmd import Cmd
from bioloid import packet
from bioloid.device import Device
from bioloid.column import column_print
from bioloid.dumpmem import dump_mem
from bioloid.parse_utils import parse_int, parse_byte_array
from bioloid.test_bus import TestError, TestPacket, TestBus
from bioloid.bus import BusError

GOOD = logging.INFO + 1


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
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


class CommandLineOutput(object):
    """A class which allows easy integration of Cmd output into logging
    and also allows for easy capture of the output for testing purposes.

    """

    def __init__(self, log=None):
        self.captured_output = None
        self.error_count = 0
        self.fatal_count = 0
        self.buffered_output = ""
        self.log = log or logging.getLogger(__name__)

    def set_capture_output(self, capture_output):
        """Sets capture_output flag, which determines whether the logging
        output is captured or not.

        """
        if capture_output:
            self.captured_output = []
        else:
            self.captured_output = None

    def get_captured_output(self):
        """Returns the logging output which has been captured so far."""
        return self.captured_output

    def get_error_count(self):
        """Returns the number of errors which have been recorded in the
        currently captured output.

        """
        return self.error_count

    def get_fatal_count(self):
        """Returns the number of fatal errors which have been recorded in the
        currently captured output.

        """
        return self.fatal_count

    def flush(self):
        """Used by Cmd just after printing the prompt."""
        prompt = self.buffered_output
        self.buffered_output = ""
        self.write_prompt(prompt)

    def debug(self, msg, *args, **kwargs):
        """Captures and logs a debug level message."""
        self.log.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Captures and logs an info level message."""
        if self.captured_output is not None:
            self.captured_output.append(('info', msg % args))
        self.log.info(msg, *args, **kwargs)

    def good(self, msg, *args, **kwargs):
        """Logs a GOOD level string, which the color formatter prints as
        a green color..

        """
        self.log.log(GOOD, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Captures and logs an error level message."""
        if self.captured_output is not None:
            self.captured_output.append(('error', msg % args))
        self.error_count += 1
        self.log.error(msg, *args, **kwargs)

    def fatal(self, msg, *args, **kwargs):
        """Captures and logs an fatal level message."""
        if self.captured_output is not None:
            self.captured_output.append(('fatal', msg % args))
        self.fatal_count += 1
        self.log.fatal(msg, *args, **kwargs)

    def write(self, string):
        """Characters to output. Lines will be delimited by newline
        characters.

        This routine breaks the output into lines and logs each line
        individually.

        """
        if len(self.buffered_output) > 0:
            string = self.buffered_output + string
            self.buffered_output = ""
        while True:
            nl_index = string.find('\n')
            if nl_index < 0:
                self.buffered_output = string
                return
            self.info(string[0:nl_index])
            string = string[nl_index + 1:]

    def write_prompt(self, prompt):
        """A derived class can override this method to split out the
        prompt from regular output.

        """
        sys.stdout.write(prompt)
        sys.stdout.flush()
        self.captured_output = []
        self.error_count = 0
        self.fatal_count = 0


class CommandLineBase(Cmd):
    """Contains common customizations to the Cmd class."""

    cmd_stack = []
    quitting = False
    output = None

    def __init__(self, log=None, filename=None, *args, **kwargs):
        if 'stdin' in kwargs:
            Cmd.use_rawinput = 0
        if not CommandLineBase.output:
            CommandLineBase.output = CommandLineOutput(log=log)
        self.log = CommandLineBase.output
        Cmd.__init__(self, stdout=self.log, *args, **kwargs)
        if '-' not in Cmd.identchars:
            Cmd.identchars += '-'
        self.filename = filename
        self.line_num = 0
        self.command = None
        if len(CommandLineBase.cmd_stack) == 0:
            self.cmd_prompt = "bioloid"
        else:
            self.cmd_prompt = CommandLineBase.cmd_stack[-1].command
        self.cmdloop_executed = False
        try:
            import readline
            delims = readline.get_completer_delims()
            readline.set_completer_delims(delims.replace("-", ""))
        except ImportError:
            pass

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

    def default(self, line):
        """Called when a command isn't recognized."""
        raise ValueError("Unrecognized command: '%s'" % line)

    def emptyline(self):
        """We want empty lines to do nothing. By default they would repeat the
        previous command.

        """
        pass

    def update_prompt(self):
        """Sets the prompt based on the current command stack."""
        if Cmd.use_rawinput:
            prompts = [cmd.cmd_prompt for cmd in CommandLineBase.cmd_stack]
            self.prompt = " ".join(prompts) + "> "
        else:
            self.prompt = ""

    def preloop(self):
        """Update the prompt before cmdloop, which is where the prompt
        is used.

        """
        Cmd.preloop(self)
        self.update_prompt()

    def postcmd(self, stop, line):
        """We also update the prompt here since the command stack may
        have been modified.

        """
        stop = Cmd.postcmd(self, stop, line)
        self.update_prompt()
        return stop

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
        CommandLineBase.cmd_stack.append(self)
        stop = self.auto_cmdloop_internal(line)
        CommandLineBase.cmd_stack.pop()
        return stop

    def auto_cmdloop_internal(self, line):
        """The main code for auto_cmdloop."""
        try:
            if len(line) == 0:
                self.cmdloop()
            else:
                self.onecmd(line)
                if (self.cmdloop_executed and
                        not CommandLineBase.quitting):
                    self.cmdloop()
        except KeyboardInterrupt:
            print('')
            CommandLineBase.quitting = True
            return True
        if CommandLineBase.quitting:
            return True

    def handle_exception(self, err, log=None):
        """Common code for handling an exception."""
        if not log:
            log = self.log.error
        base = CommandLineBase.cmd_stack[0]
        if base.filename is not None:
            log("File: %s Line: %d Error: %s",
                base.filename, base.line_num, err)
            CommandLineBase.quitting = True
            return True
        log("Error: %s", err)

    def onecmd(self, line):
        """Override onecmd.

        1 - So we don't have to have a do_EOF method.
        2 - So we can strip comments
        3 - So we can track line numbers

        """
        self.line_num += 1
        if line == "EOF":
            if Cmd.use_rawinput:
                # This means that we printed a prompt, and we'll want to
                # print a newline to pretty things up for the caller.
                print('')
            return True
        # Strip comments
        comment_idx = line.find("#")
        if comment_idx >= 0:
            line = line[0:comment_idx]
            line = line.strip()
        try:
            return Cmd.onecmd(self, line)
        except ValueError as err:
            return self.handle_exception(err)
        except TestError as err:
            return self.handle_exception(err, log=self.log.fatal)
        except BusError as err:
            return self.handle_exception(err)

    def cmdloop(self, *args, **kwargs):
        """We override this to support auto_cmdloop."""
        self.cmdloop_executed = True
        return Cmd.cmdloop(self, *args, **kwargs)

    def parseline(self, line):
        """Record the command that was executed. This also allows us to
         transform dashes back to underscores.

        """
        (command, arg, line) = Cmd.parseline(self, line)
        self.command = command
        if command:
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

    def do_exit(self, _):
        """Exits from the program."""
        CommandLineBase.quitting = True
        return True

    def do_quit(self, _):
        """Exits from the program."""
        CommandLineBase.quitting = True
        return True


class CommandLine(CommandLineBase):
    """Converts command lines into bioloid commands and sends them to a
    bioloid device.

    """

    def __init__(self, bus, dev_types, capture_output=False, *args, **kwargs):
        CommandLineBase.__init__(self, *args, **kwargs)
        self.bus = bus
        self.bus.set_log(self.log)
        self.log.set_capture_output(capture_output)
        self.dev_types = dev_types
        # We use the device types as commands, so add a do_xxx where
        # xxx is the device type name.
        for dt_name in self.dev_types.get_names():
            dt_name = dt_name.replace("-", "_")
            func_name = "do_" + dt_name
            cls = self.__class__
            try:
                getattr(cls, func_name)
            except AttributeError:
                setattr(cls, func_name, getattr(cls, "cb_do_device_type"))
        self.add_completion_funcs(self.dev_types.get_names(),
                                  "cb_complete_device_type")
        self.scan_idx = 0
        self.scan_spin = "-\\|/"

    def cb_complete_device_type(self, text, line, begin_idx, end_idx):
        """Completion support for device types."""
        return [dt_name for dt_name in self.dev_types.get_names()
                if dt_name.startswith(text)]

    def cb_do_device_type(self, line):
        """bioloid> {command}

        Select the {command} device type to receive the next portion of the
        command.

        """
        dev_type_name = self.command
        dev_type = self.dev_types.get(dev_type_name)
        return DevTypeCommandLine(dev_type, self.bus).auto_cmdloop(line)

    def do_action(self, _):
        """bioloid> action

        Broadcasts an ACTION command on the bus. This will cause registered
        writes to be performed.

        """
        self.bus.send_action()

    def do_args(self, line):
        """Prints out the command line arguments."""
        self.log.info("args line = '%s'", line)

    def do_echo(self, line):
        """Prints the rest of the line to the output.

        This is mostly useful when processing from a script.

        """
        self.log.info("%s", line)

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
            num_ids = parse_int(line, "number of ids")
        else:
            num_ids = 32
        self.scan_idx = 0
        if num_ids < 100:
            servo_id_found = self.bus.scan(0, num_ids,
                                           self.cb_scan_dev_found,
                                           self.cb_scan_dev_missing)
            sensor_id_found = self.bus.scan(100, num_ids,
                                            self.cb_scan_dev_found,
                                            self.cb_scan_dev_missing)
            if not servo_id_found and not sensor_id_found:
                self.log.info("No devices found")
        else:
            if not self.bus.scan(0, num_ids,
                                 self.cb_scan_dev_found,
                                 self.cb_scan_dev_missing):
                self.log.info("No devices found")

    def cb_scan_dev_found(self, bus, dev):
        """This is called whenever the scan command finds a device."""
        # We want to read the model and version, which is at offset 0, 1,
        # and 2 so we do it with a single read.
        data = dev.read(0, 3)
        model = data[0] + data[1] * 256
        version = data[2]
        self.log.info("ID: %3d Model: %5u Version: %5u",
                      dev.get_dev_id(), model, version)

    def cb_scan_dev_missing(self, bus, dev):
        """Called whenever a device fails to response."""
        sys.stdout.write("%c\r" % self.scan_spin[self.scan_idx])
        sys.stdout.flush()
        self.scan_idx += 1
        self.scan_idx %= len(self.scan_spin)

    def do_dev_types(self, _):
        """bioloid> dev-types

        Lists the device types that the program knows about.

        bioloid> dev-types
        servo      Model:    12 with 34 registers

        """
        for dev_type in self.dev_types:
            self.log.info("%-10s Model: %5u with %2d registers",
                          dev_type.name(), dev_type.model(),
                          dev_type.num_regs())

    def do_test(self, line):
        """bioloid> test
        """
        if not isinstance(self.bus, TestBus):
            self.log.error("The test command requires the TestBus")
            return
        return TestCommandLine(self.bus, self.dev_types).auto_cmdloop(line)


class DevTypeCommandLine(CommandLineBase):
    """Processes subcommands for device types (i.e. sensor or servo, etc.)"""

    def __init__(self, dev_type, bus, *args, **kwargs):
        CommandLineBase.__init__(self, *args, **kwargs)
        self.dev_type = dev_type
        self.bus = bus
        self.add_completion_funcs(("reg", "reg-raw"), "cb_complete_reg_name")

    def cb_complete_reg_name(self, text, line, begin_idx, end_idx):
        """Completion function for completing a register name."""
        return [rn for rn in self.dev_type.get_register_names()
                if rn.startswith(text)]

    def onecmd(self, line):
        """See if the command looks like a number. This is useful if the
        user ran "bioloid.py servo" and then enters just the id.

        """
        try:
            id_str, rest, line = self.parseline(line)
            dev_id = int(id_str, 0)
            return DevTypeIdCommandLine(self.dev_type,
                                        self.bus, dev_id).auto_cmdloop(rest)
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
        self.dev_type.dump_regs()

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
        self.dev_type.dump_regs_raw()

    def sync_write(self, line, raw):
        """Does a synchronous write to multiple devices.
        """
        args = line.split()
        try:
            num_ids = parse_int(args.pop(0))
            dev_ids = []
            for _ in range(num_ids):
                dev_ids.append(parse_int(args.pop(0)))
            reg_name = args.pop(0)
            num_regs = parse_int(args.pop(0))
            reg_set = self.dev_type.get_register_set_by_name(reg_name,
                                                             num_regs)
            values = []
            for idx in range(num_ids):
                values.append([])
                for reg_idx in range(num_regs):
                    val_str = args.pop(0)
                    reg = reg_set[reg_idx]
                    if raw:
                        val = reg.parse_raw(val_str)
                    else:
                        val = reg.parse(val_str)
                    values[idx].append(val)
        except IndexError:
            raise ValueError("Not enough arguments")
        self.bus.sync_write(dev_ids, reg_set, values, raw=True)

    def do_sync_write(self, line):
        """bioloid> dev-type sync_write <num-ids> <id1> ... <reg-name> \
<num-regs> <val1> ...

        Sends a synchronous write command, which writes multiple register
        values to multiple devices simultaneously.

        bioloid> servo sync_write 2 1 2 goal-position 2 45 5 90 10

        writes to 2 id's (1 and 2), and writes 2 registers: goal-position
        and the moving-speed.

        """
        self.sync_write(line, raw=False)

    def do_sync_write_raw(self, line):
        """bioloid> dev-type sync_write_raw <num-ids> <id1> ... <reg-name> \
<num-regs> <val1> ...

        Sends a synchronous write command, which writes multiple register
        values to multiple devices simultaneously.

        bioloid> servo sync_write 2 1 2 goal-position 2 150 0 250 20

        writes to 2 id's (1 and 2), and writes 2 registers: goal-position
        and the moving-speed.

        """
        self.sync_write(line, raw=True)

class DevTypeIdCommandLine(CommandLineBase):
    """Processes subcommands for device types followed by an id.

    (i.e. sensor 7 ping)

    """

    def __init__(self, dev_type, bus, dev_id, *args, **kwargs):
        CommandLineBase.__init__(self, *args, **kwargs)
        self.dev_type = dev_type
        self.bus = bus
        self.dev_id = dev_id
        self.dev = Device(bus, dev_id, log=self.log)
        self.add_completion_funcs(("get", "get-raw", "set", "set-raw",
                                   "read-data", "rd", "write-data", "wd",
                                   "reg-write", "rw", "reg", "reg-raw"),
                                  "cb_complete_reg_name")

    def cb_complete_reg_name(self, text, line, begin_idx, end_idx):
        """Provides completion for register names."""
        return [rn for rn in self.dev_type.get_register_names()
                if rn.startswith(text)]

    def do_ping(self, _):
        """bioloid> device-type id ping

        Sends a PING command to the indicated device.

        """
        if self.dev.ping():
            self.log.info("device %d status normal", self.dev.get_dev_id())
        else:
            self.log.error("device %d not responding", self.dev.get_dev_id())

    def get_reg(self, reg_name, raw):
        """Retrieves a (or all) register from the device and prints the
        value.

        If 'raw' is true then raw register values will be printed,
        otherwise formatted values will be printed.

        """
        if self.dev_id == packet.Id.BROADCAST:
            self.log.error("Broadcast ID not valid with get command")
            return
        if reg_name != "all":
            reg = self.dev_type.get_register_by_name(reg_name)
            if not reg:
                self.log.error("Register '%s' not defined.", reg_name)
                return
            val = self.dev.read_reg(reg)
            if raw:
                self.log.info(reg.fmt_raw(val))
            else:
                self.log.info(reg.fmt(val))
            return
        lines = [['Addr', 'Size', 'Value', 'Type', 'Name'], '-']
        for reg in self.dev_type.get_registers_ordered_by_offset():
            #print('Reading reg @ {:#04x}'.format(reg.offset()))
            val = self.dev.read_reg(reg)
            if raw:
                val_str = reg.fmt_raw(val)
            else:
                val_str = reg.fmt(val)
            lines.append(["0x%02x" % reg.offset(),
                          "%s %d" % (reg.access(), reg.size()),
                          val_str,
                          reg.type(),
                          reg.name()])
        column_print("<<>< ", lines, print_func=self.log.info)

    def set_reg(self, line, raw, deferred=False):
        """Sets a register to a value. 'raw' determines if the value is a raw
        register value, or a "formatted" value.

        """
        args = line.split()
        if len(args) != 2:
            raise ValueError("Expecting 2 arguments, found %d" % len(args))
        reg = self.dev_type.get_register_by_name(args[0])
        if reg is None:
            raise ValueError("Expecting register-name or numeric offset. " +
                             "Found '%s'" % args[0])
        if raw:
            val = reg.parse_raw(args[1])
        else:
            val = reg.parse(args[1])
        self.dev.write_reg(reg, val, deferred)

    def parse_offset_and_data(self, line):
        """Parses a register offset (or name) and raw bytes to write into
        the control table.

        """
        args = line.split()
        if len(args) < 2:
            raise ValueError("Expecting offset and at least 1 " +
                             "additional value.")
        offset = self.dev_type.get_offset_by_name(args[0])
        if offset is None:
            raise ValueError("Expecting register-name or numeric offset. " +
                             "Found '%s'" % args[0])
        data = parse_byte_array(args[1:])
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

    def do_deferred_set(self, line):
        """bioloid> dev-type id deferrd_set offset-or-register-name value

        Sets the value of a register using the natural units of the
        register type (degrees, volts, etc).

        The write of the data will be deferred until an ACTION command is
        received.

        """
        self.set_reg(line, raw=False, deferred=True)

    def do_set_raw(self, line):
        """bioloid> device-type id set offset-or-register-name value

        Sets the raw value of a register.

        """
        self.set_reg(line, raw=True)

    def do_read_data(self, line):
        """bioloid> device-type id read-data offset-or-register-name len

        Issues the READ_DATA command to the inidcated device. The data
        which is read is formatted as hex bytes.

        Note that multi-byte data is little-endian.

        > servo 15 read-data 0x1e 4
        Read: 001e: AA 02 00 00

        """
        args = line.split()
        if len(args) != 2:
            raise ValueError("Expecting offset and length.")
        offset = self.dev_type.get_offset_by_name(args[0])
        if offset is None:
            raise ValueError("Expecting register name or numeric offset. " +
                             "Found '%s'", args[0])
        data_len = parse_int(args[1], "length")
        if data_len < 0 or data_len > 255:
            raise ValueError("Expecting length to be betweeen 0 and 255. " +
                             "Found: %d" % data_len)
        data = self.dev.read(offset, data_len)
        dump_mem(data, prefix="Read", show_ascii=False,
                 print_func=self.log.info)

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

        Note that multi-byte data is little-endian.

        """
        offset, data = self.parse_offset_and_data(line)
        self.dev.write(offset, data)

    def do_wd(self, line):
        """bioloid> device-type id wd offset-or-register-name data ...

        Alias for write-data.

        """
        return self.do_write_data(line)

    def do_deferred_write(self, line):
        """bioloid> device-type id deferred-write offset-or-reg-name data ...

        Issues the REG_WRITE command to the indicated device. The data
        is parsed as individual bytes, and may be in decimal, octal (if
        prefixed with a 0), or hexadecimal (if prefixed with a 0x).

        The write of the data will be deferred until an ACTION command is
        received.

        """
        offset, data = self.parse_offset_and_data(line)
        self.dev.write(offset, data, deferred=True)

    def do_dw(self, line):
        """bioloid> device-type id dw offset data ...

        Alias for deferred-write.

        """
        return self.do_deferred_write(line)

    def do_reset(self, _):
        """bioloid> device-type id reset

        Issues the RESET command to the indicated device. This causes the
        device to reset all of the control table values to their default
        values.

        """
        self.dev.reset()

    def do_reg(self, _):
        """bioloid> dev-type id reg

        Alias for reg command at the device type level (you're currently
        at the device level).

        """
        self.dev_type.dump_regs()

    def do_reg_raw(self, _):
        """bioloid> dev-type id reg-raw

        Alias for reg-raw command at the device type level (you're
        currently at the device level).

        """
        self.dev_type.dump_regs_raw()


def calc_checksum(data):
    """Calculates the checksum for the packet."""
    checksum = 0
    for byte in data[2:]:
        checksum += byte
    return bytes([~checksum & 0xff])


class TestCommandLine(CommandLineBase):
    """Implements commmands used for testing.

    You can queue up command packets, response packets, or timeouts.
    Whenever the TestBus is asked to send a packet, it will compare the
    packet to send against the top of the queue, and if it doesn't match
    then it will generate a failure message and quit.

    Each time read_status_packet is called, it looks for a response packet
    or timeout at the front of the queue, and returns the corresponding
    response.

    """

    def __init__(self, bus, dev_types, *args, **kwargs):
        CommandLineBase.__init__(self, *args, **kwargs)
        self.bus = bus
        self.dev_types = dev_types

    def do_cmd(self, line):
        """bioloid> test cmd <hex-id> <command> <hex-data> ...

        Queues up an expected command packet. The command will be an ascii
        version of the command, and data is assumed to be hexadecimal bytes
        making up the rest of the packet (i.e. without the 0x prefix).
        The packet preamble (2 0xff's), length, and checksum will all be
        calculated autmatically.

        """
        args = line.split()
        if len(args) < 2:
            raise ValueError("Expecting at least id and command")
        dev_id = parse_int(args.pop(0), "hex-id", base=16)
        cmd_str = args.pop(0)
        cmd_id = packet.Command.parse(cmd_str)
        data = bytes([0xff, 0xff, dev_id, len(args) + 2, cmd_id])
        data += parse_byte_array(args, base=16)
        data += calc_checksum(data)
        self.bus.queue(TestPacket(TestPacket.COMMAND, data))

    def do_cmd_raw(self, line):
        """bioloid> test cmd-raw <hex-data> ...

        Queues up an expected command packet. The <data> is expected to
        include the preamble, id, length, command, data, and checksum.

        """
        args = line.split()
        if len(args) < 5:
            raise ValueError("Expecting at least 5 bytes (smallest packet)")
        self.bus.queue(TestPacket(TestPacket.COMMAND,
                                  parse_byte_array(args, base=16)))

    def do_rsp(self, line):
        """bioloid> test rsp <hex-id> <error> <hex-data> ...

        Queues up an expected response packet. The error will be an ascii
        version of the error code, and data is assumed to be hexadecimal
        bytes making up the rest of the packet (i.e. without the 0x prefx).
        The packet preamble (2 0xff's), length, and checksum will all be
        calculated autmatically.

        """
        args = line.split()
        if len(args) < 2:
            raise ValueError("Expecting at least id and error")
        dev_id = parse_int(args.pop(0), "hex-id", base=16)
        error_str = args.pop(0)
        error_code = packet.ErrorCode.parse(error_str)
        data = bytes([0xff, 0xff, dev_id, len(args) + 2, error_code])
        data += parse_byte_array(args, base=16)
        data += calc_checksum(data)
        self.bus.queue(TestPacket(TestPacket.RESPONSE, data))

    def do_rsp_raw(self, line):
        """bioloid> test rsp-raw <hex-data> ...

        Queues up an expected response packet. The <hex-data> is expected to
        include the preamble, id, error code, length, data, and checksum.

        """
        args = line.split()
        if len(args) < 5:
            raise ValueError("Expecting at least 5 bytes (smallest packet)")
        self.bus.queue(TestPacket(TestPacket.RESPONSE,
                                  parse_byte_array(args, base=16)))

    def do_rsp_timeout(self, _):
        """bioloid> test rsp-timeout

        Queues up a timeout response.

        """
        self.bus.queue(TestPacket(TestPacket.TIMEOUT))

    def do_output(self, line):
        """bioloid> test output "output-compare" <command>

        Executes <command> and verified that the output is "output-compare"

        """
        words = shlex.split(line)
        cmd_line = CommandLine(self.bus, self.dev_types, capture_output=True)
        cmd_line.auto_cmdloop('  '.join(words[1:]))
        CommandLineBase.quitting = False
        test_output = CommandLineBase.output.get_captured_output()
        if CommandLineBase.output.get_fatal_count() > 0:
            self.log.fatal("Unexpected fatal error encountered.")
            self.bus.test_failed()
        elif len(test_output) != 1 or test_output[0][1] != words[0]:
            self.log.error("Test Failed. Expected '%s' got '%s'",
                           words[0], test_output[0][1])
            self.bus.test_failed()
        else:
            self.bus.test_passed()

    def do_error(self, line):
        """bioloid> test error <command>

        Executes <command> and verifies that an error occurred."

        """
        cmd_line = CommandLine(self.bus, self.dev_types, capture_output=True)
        cmd_line.auto_cmdloop(line)
        CommandLineBase.quitting = False
        if CommandLineBase.output.get_fatal_count() > 0:
            self.log.fatal("Unexpected fatal error encountered.")
            self.bus.test_failed()
        elif CommandLineBase.output.get_error_count() == 0:
            self.log.error("Test Failed. Expected an error, but none found.")
            self.bus.test_failed()
        else:
            self.bus.test_passed()

    def do_success(self, line):
        """bioloid> test success <command>

        Executes <command> and verifies that no error occurred."

        """
        cmd_line = CommandLine(self.bus, self.dev_types, capture_output=True)
        cmd_line.auto_cmdloop(line)
        CommandLineBase.quitting = False
        if CommandLineBase.output.get_fatal_count() > 0:
            self.log.fatal("Unexpected fatal error encountered.")
            self.bus.test_failed()
        elif CommandLineBase.output.get_error_count() > 0:
            self.log.error("Test Failed. Unexpected error encountered.")
            self.bus.test_failed()
        else:
            self.bus.test_passed()
