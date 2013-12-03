#!/usr/bin/env python

"""This file contains the main program for the bioloid command line
interface.

"""

import argparse
import os
import sys
import serial
import logging
from bioloid.command_line import CommandLine
from bioloid.serial_bus import SerialPort, SerialBus
from bioloid.device_type_parser import DeviceTypeParser
from bioloid.device_type import DeviceTypes
from bioloid.log_setup import log_setup
from bioloid.test_bus import TestBus


def main():
    """The main program."""
    default_baud = 1000000
    default_port = os.getenv("BIOLOID_PORT")
    parser = argparse.ArgumentParser(
        prog="bioloid",
        usage="%(prog)s [options] [command]",
        description="Send commands to bioloid devices",
        epilog=("You can specify the default serial port using the " +
                "BIOLOID_PORT environment variable.")
    )
    parser.add_argument(
        "-b", "--baud",
        dest="baud",
        action="store",
        type=int,
        help="Set the baudrate used (default = %d)" % default_baud,
        default=default_baud
    )
    default_port_help = ""
    if default_port:
        default_port_help = " (default '%s')" % default_port
    parser.add_argument(
        "-p", "--port",
        dest="port",
        help="Set the serial port to use" + default_port_help,
        default=default_port
    )
    parser.add_argument(
        "-n", "--net",
        dest="net",
        help="Set the network host (and optionally port) to use"
    )
    parser.add_argument(
        "-t", "--test",
        dest="test",
        action="store_true",
        help="Uses the TestBus rather than communicating with real devices."
    )
    parser.add_argument(
        "-f", "--file",
        dest="filename",
        help="Specifies a file of commands to process."
    )
    parser.add_argument(
        "-d", "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug features",
        default=False
    )
    parser.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        help="Turn on verbose messages",
        default=False
    )
    parser.add_argument(
        "cmd",
        nargs="*",
        help="Optional command to execute"
    )
    args = parser.parse_args(sys.argv[1:])

    script_dir = os.path.dirname(os.path.realpath(__file__))

    log_setup()
    log = logging.getLogger()
    if args.debug:
        log.setLevel(logging.DEBUG)

    if args.verbose:
        log.info("Baud = %d", args.baud)
        log.info("Port = %s", args.port)
        log.info("Net = %s", args.net)
        log.info("Test = %s", args.test)
        log.info("Debug = %s", args.debug)
        log.info("Cmd = [%s]", ', '.join(args.cmd))
        log.info("script_dir = %s", script_dir)

    if not args.port and not args.net and not args.test:
        log.error("Must specify one of network, serial, or test")
        sys.exit(1)

    if args.net:
        log.error("network option not supported yet")
        sys.exit(1)

    dev_types = DeviceTypes()
    parser = DeviceTypeParser(dev_types)
    parser.parse_dev_type_files(script_dir)
    bus = None

    if args.test:
        bus = TestBus(show_packets=args.debug)
    elif args.port:
        try:
            serial_port = SerialPort(port=args.port, baudrate=args.baud)
        except serial.serialutil.SerialException:
            log.error("Unable to open port '%s'", args.port)
            sys.exit(1)
        bus = SerialBus(serial_port, show_packets=args.debug)
    if args.filename:
        with open(args.filename) as cmd_file:
            cmd_line = CommandLine(bus, dev_types, stdin=cmd_file,
                                   filename=args.filename)
            cmd_line.auto_cmdloop('')
    else:
        cmd_line = CommandLine(bus, dev_types)
        cmd_line.auto_cmdloop(' '.join(args.cmd))
    if args.test:
        log.info("--------------------------")
        log.info("Passed: %d Failed: %d",
                 bus.get_pass_count(), bus.get_fail_count())


main()
