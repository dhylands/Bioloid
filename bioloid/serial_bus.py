"""This module implements a serial bus class which talks to bioloid
devices through a serial port.

"""

import serial
from bioloid.bus import Bus


class SerialPort(serial.Serial):
    """Encapsulates serial port communicatons."""

    def __init__(self, *args, **kwargs):
        # Ensure that a reasonable timeout is set
        timeout = kwargs.get('timeout', 0.05)
        if timeout < 0.05:
            timeout = 0.05
        kwargs['timeout'] = timeout
        kwargs['bytesize'] = serial.EIGHTBITS
        kwargs['parity'] = serial.PARITY_NONE
        kwargs['stopbits'] = serial.STOPBITS_ONE
        kwargs['xonxoff'] = False
        kwargs['rtscts'] = False
        kwargs['dsrdtr'] = False
        serial.Serial.__init__(self, *args, **kwargs)


class SerialBus(Bus):
    """Implements a BioloidBus which sends commands to a bioloid device
    via a BioloidSerialPort.

    """

    def __init__(self, serial_port, show_packets=False):
        Bus.__init__(self, show_packets)
        self._serial_port = serial_port

    def read_byte(self):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.

        """
        data = self._serial_port.read()
        if data:
            return ord(data[0])
        return None

    def write_buffered_data(self, data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        """
        self._serial_port.write(data)
