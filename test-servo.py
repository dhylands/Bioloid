#!/usr/bin/env python

"""Sample program which shows how to talk to a bioloid servo."""

import argparse
import os
import sys
import serial
import logging
import time

from bioloid.serial_bus import SerialPort, SerialBus
from bioloid.device_type_parser import DeviceTypeParser
from bioloid.device_type import DeviceTypes
from bioloid.device import Device
from bioloid.log_setup import log_setup


def main():
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
        "-i", "--id",
        dest="dev_id",
        type=int,
        help="Sets the id of the servo to use",
        default=1
    )
    parser.add_argument(
        "-d", "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug features",
        default=False
    )
    args = parser.parse_args(sys.argv[1:])
    script_dir = os.path.dirname(os.path.realpath(__file__))

    log_setup()
    log = logging.getLogger()
    if args.debug:
        log.setLevel(logging.DEBUG)

    if not args.port:
        log.error("No serial port specified")
        sys.exit(1) 

    log.info("Port = %s", args.port)
    log.info("Baud = %d", args.baud)
    log.info("ID   = %d", args.dev_id)

    dev_types = DeviceTypes()
    parser = DeviceTypeParser(dev_types)
    parser.parse_dev_type_files(script_dir)
    try:
        serial_port = SerialPort(port=args.port, baudrate=args.baud)
    except serial.serialutil.SerialException:
        log.error("Unable to open port '%s'", args.port)
        sys.exit(1)
    bus = SerialBus(serial_port, show_packets=args.debug)

    servo_type = dev_types.get("servo")
    if not servo_type:
        log.error("Unable to find device type 'servo'")
        sys.exit(1)
    dev = Device(bus, args.dev_id, servo_type)
    led = dev.get_dev_reg("led")
    if not led:
        log.error("Unable to retrieve register 'led'")
        sys.exit(1)
    goal_position = dev.get_dev_reg("goal-position")
    if not goal_position:
        log.error("Unable to retrieve register 'goal-position'")
        sys.exit(1)
    moving_speed = dev.get_dev_reg("moving-speed")
    if not moving_speed:
        log.error("Unable to retrieve register 'moving-speed'")
        sys.exit(1)

    if not dev.ping():
        log.error("Device %d doesn't seem to be responding", args.dev_id)
        sys.exit(1)
    moving_speed.set(20)
    log.info("Speed = %.1f", moving_speed.get())

    try:
        for _ in range(10):
            log.info("led on - position 0")
            led.set(1)
            goal_position.set(0)
            time.sleep(2)
            log.info("led off - position 100")
            led.set(0)
            goal_position.set(300)
            time.sleep(2)
    except KeyboardInterrupt:
        pass

main()
