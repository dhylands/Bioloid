#!/usr/bin/python

import argparse, os, sys
import serial
import logging
from bioloid.command_line import CommandLine
from bioloid.serial_bus import SerialPort, SerialBus
from bioloid.device_type_parser import DeviceTypeParser
from bioloid.device_type import DeviceTypes
from bioloid.log_setup import log_setup


def main():
    defaultBaud = 1000000
    defaultPort = os.getenv("BIOLOID_PORT")
    parser = argparse.ArgumentParser(
        prog = "bioloid",
        usage = "%(prog)s [options] [command]",
        description = "Send commands to bioloid devices",
        epilog = ("You can specify the default serial port using the " +
                  "BIOLOID_PORT environment variable.")
    )
    parser.add_argument("-b", "--baud",
        dest = "baud",
        action = "store",
        type = int,
        help = "Set the baudrate used (default = %d)" % defaultBaud,
        default = defaultBaud
    )
    defaultPortHelp = ""
    if defaultPort:
        defaultPortHelp = " (default '%s')" % defaultPort
    parser.add_argument("-p", "--port",
        dest = "port",
        help = "Set the serial port to use" + defaultPortHelp,
        default = defaultPort
    )
    parser.add_argument("-n", "--net",
        dest = "net",
        help = "Set the network host (and optionally port) to use"
    )
    parser.add_argument("-d", "--debug",
        dest = "debug",
        action = "store_true",
        help = "Enable debug features",
        default = False
    )
    parser.add_argument("-v", "--verbose",
        dest = "verbose",
        action = "store_true",
        help = "Turn on verbose messages",
        default = False
    )
    parser.add_argument("cmd",
        nargs = "*",
        help = "Optional command to execute"
    )
    args = parser.parse_args(sys.argv[1:])
    verbose = args.verbose
    debug = args.debug;

    script_dir = os.path.dirname(os.path.realpath(__file__))

    log_setup()
    log = logging.getLogger()
    if args.debug:
        log.setLevel(logging.DEBUG)

    if verbose:
        log.info("Baud = %d" % args.baud)
        log.info("Port = %s" % args.port)
        log.info("Net = %s" % args.net)
        log.info("Debug = %s" % args.debug)
        log.info("Cmd = [%s]" % ', '.join(args.cmd))
        log.info("script_dir = %s" % script_dir)

    if not args.port and not args.net:
        log.error("Must specify one of network or serial")
        sys.exit(1)

    if args.net:
        log.error("network option not supported yet")
        sys.exit(1)

    dev_types = DeviceTypes()
    parser = DeviceTypeParser(dev_types)
    parser.parse_dev_type_files(script_dir)

    if args.port:
        try:
            serial_port = SerialPort(port=args.port, baudrate=args.baud)
        except serial.serialutil.SerialException:
            log.error("Unable to open port '%s'", args.port)
            sys.exit(1)
        serial_bus = SerialBus(serial_port, show_packets=args.debug)
        cmd_line = CommandLine(serial_bus, dev_types)
    cmd_line.auto_cmdloop(' '.join(args.cmd))

if __name__ == "__main__":
    main()
