Bioloid
=======

Python code for working with bioloid devices.

cli.py is a command line program which communicates with devices on the
bioloid bus.

Currently, only serial based interfaces are supported. I have a homebrewed serial
interface created using an FTDI chip and a couple logic chips. The software is
also compatible with Robotis serial interfaces like the USB2Dynamixel
http://support.robotis.com/en/product/auxdevice/interface/usb2dxl_manual.htm

I originally wrote a tool similar to this in C. My C version can be found here:
https://github.com/dhylands/projects/tree/master/bioloid/cli

# Installation

```bash
git clone https://github.com/dhylands/Bioloid
cd Bioloid
pip install -e .
export BIOLOID_PORT=/dev/ttyUSB0   # or whatever is appropriate
./cli.py
```

## Usage

```bash
./cli.py --help
usage: bioloid [options] [command]

Send commands to bioloid devices

positional arguments:
  cmd                   Optional command to execute

optional arguments:
  -h, --help            show this help message and exit
  -b BAUD, --baud BAUD  Set the baudrate used (default = 1000000)
  -p PORT, --port PORT  Set the serial port to use
  -n NET, --net NET     Set the network host (and optionally port) to use
  -t, --test            Uses the TestBus rather than communicating with real
                        devices.
  -f FILENAME, --file FILENAME
                        Specifies a file of commands to process.
  -d, --debug           Enable debug features
  -v, --verbose         Turn on verbose messages

You can specify the default serial port using the BIOLOID_PORT environment
variable.
```

The debug command will print out information about parsing the bld files, and
will also show packets sent to and from the devices.

If you just want to play with the commands, you can use the --test mode which
doesn't require any real hardware to be connected. If you enter any commands
which require a response from a bioloid device you will most likely see the
following error:
```
Error: TestBus: packet queue is empty (unexpected)
```
This is becuase the test framework expects the response to have been queued
up already.

## Direct usage

You can take a look at the test-servo.py script to see how to use these classes
directly, without using the command line.

## Commands

Once you've started the cli, you should get a ```bioloid> ``` prompt. The help
command will show all of the available commands:

### CLI Commands

#### help

Displays the available commands. You can type in any of the commands followed
by help to get more detailed information about that command.

```
bioloid> help

Documented commands (type help <topic>):
========================================
action  args  dev-types  echo  help  mini-io  quit  scan  sensor  servo  test
```

#### quit

Exits the CLI. You can also use Control-D from the ```bioloid>``` prompt to quit.

### Bus commands

#### scan

Scans the bioloid device and prints out a summary of the devices found. For
example, if I had 2 servos, with IDs of 8 and 10, then I would see something
like this:
```
bioloid> scan
ID:   8 Model:    12 Version:    22
ID:  10 Model:    12 Version:    22
```

#### action

Broadcasts an ACTION command to the bus. This causes all deferred writes to be
triggered. Deferred writes can be performed using the deferred-write servo
sub-command.

### Device Commands

#### dev-types

Shows the registered device types. Each device type is represented by a file
which is named reg-devtype.bld, so the device types shown may vary. The default
device types are shown:
```
bioloid> dev-types
mini-io    Model: 17420 with 29 registers
sensor     Model:    13 with 32 registers
servo      Model:    12 with 34 registers
```

The device types themselves can be treated like commands. And for each device
type there are device generic commands, and device specific commands. The
device generic and device specific commands are the same for each device type.
What varies is the register set.

For example, the output of servo help shows the commands which are
```
bioloid> servo help

Documented commands (type help <topic>):
========================================
help  quit  reg  reg-raw  sync-write
```

Also note, that you can enter a device type with no arguments and that will
then treat all subsequent commands as if you had typed the device type. The
prompt will be changed to reflect which device type is current. You can exit
a sub-level by using Control-D.

### Device Generic Commands

#### quit

Quits this level of the command line.

#### reg

Prints the registers associated with this device type. The min and
max values are formatted based on their type.
```
bioloid> servo reg
Addr Size         Min       Max Type            Name
---- ---- ----------- --------- --------------- ------------------
0x00 ro 2                                       model
0x02 ro 1                                       version
0x03 rw 1           0       253                 id
0x04 rw 1 2000000 bps  7843 bps BaudRate        baud-rate
0x05 rw 1      0 usec  508 usec RDT             return-delay-time
0x06 rw 2     0.0 deg 300.0 deg Angle           cw-angle-limit
0x08 rw 2     0.0 deg 300.0 deg Angle           ccw-angle-limit
...
0x2f rw 1           0         1                 lock
0x30 rw 2           0      1023                 punch
```

#### reg-raw

Prints the registers associated with this device type. The min and
max values are formatted using their raw values.

```
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
```

#### sync-write <num-ids> <id1> ... <reg-name> <num-regs> <val1> ...

Sends a synchronous write command, which writes multiple register
values to multiple devices simultaneously.

For example:
```
bioloid> servo sync_write 2 5 7 goal-position 2 45 15 90 10
```
writes to 2 id's (5 and 7), and writes 2 registers (goal-position)
and the moving-speed (the next register higher than goal-position). In the
above example servo 5 would have it's goal-position set to 45 and the moving
speed set to 15, while servo 7 would have its goal poisiton set to 90 and its
moving speed set to 10.

#### device id

### Device Specific Commands

You can also target commands to a specific device by including the device id
after the device type.

#### help

Shows the commands which can be directed to a specific device.

```
bioloid> servo 8 help

Documented commands (type help <topic>):
========================================
deferred-set    get      ping  read-data  reset    wd
deferred-write  get-raw  quit  reg        set      write-data
dw              help     rd    reg-raw    set-raw
```

#### ping

Tests to see if the given device is present or not. If the device responds
successfully to the ping, then you'll see something like this:
```
bioloid> servo 8 ping
device 8 status normal
```

If the device doesn't respond to the ping, then you'll see something like:
```
bioloid> servo 11 ping
device 11 not responding
```

And finally, if the device is present, but isn't in a normal status, then you'll
see something like this:
```
bioloid> servo 8 ping
Rcvd Status: OverHeating
```

#### reg

Alias for reg command at the device type level (you're currently
at the device level).

#### reg-raw

Alias for reg-raw command at the device type level (you're
currently at the device level).

#### reset

Issues the RESET command to the indicated device. This causes the
device to reset all of the control table values to their default
values.

#### get offset-or-register-name

Retrieves the named register from the device indicated by 'id',
and formats the result based on the register type. There is a
special register name called 'all' which will cause all of the
registers to be retrieved and printed.

```
bioloid> servo 15 get present-voltage
Read: 11.7 volts
bioloid> servo 15 get all
Addr Size Value           Name
---- ---- --------------- --------------------
0x00 ro 2 12              model
0x02 ro 1 22              version
0x03 rw 1 15              id
0x04 rw 1 1000000 baud    baud-rate
...
```

#### get-raw offset-or-register-name

Retrieves the named register from the device indicated by 'id',
and prints the raw register value. There is a special register
name called 'all' which will cause all of the registers to be
retrieved and printed.

```
bioloid> servo 15 get-raw present-voltage
Read:   117
bioloid> servo 8 get-raw all
Addr Size Value Type            Name
---- ---- ----- --------------- ------------------
0x00 ro 2    12                 model
0x02 ro 1    22                 version
0x03 rw 1     8                 id
0x04 rw 1     1 BaudRate        baud-rate
```

#### read-data offset-or-register-name len

Issues the READ_DATA command to the inidcated device. The data
which is read is formatted as hex bytes.

Note that multi-byte data is little-endian.

```
bioloid> servo 8 read-data 0x1e 4
Read: 0000: 00 02 00 00
```

#### rd offset-or-register-name len

Alias for read-data.

#### set offset-or-register-name value

Sets the value of a register using the natural units of the
register type (degrees, volts, etc).

```
bioloid> servo 8 set goal-position 150
```

#### set-raw offset-or-register-name value

Sets the raw value of a register.

```
bioloid> servo 8 set-raw goal-position 0x200
bioloid> servo 8 get goal-position
150.1 deg
```

#### write-data offset-or-register-name data ...

Issues the WRITE_DATA command to the indicated device. The data
is parsed as individual bytes, and may be in decimal, octal (if
prefixed with a 0), or hexadecimal (if prefixed with a 0x).

Note that multi-byte data is little-endian.
```
bioloid> servo 8 get goal-position
150.1 deg
bioloid> servo 8 write-data goal-position 0xaa 0x02
bioloid> servo 8 get-raw goal-position
682
bioloid> servo 8 get goal-position
200.0 deg
```
Note that 682 = 0x2aa

#### wd offset-or-register-name data ...

Alias for write-data.

#### deferred-write offset-or-reg-name data ...

Issues the REG_WRITE command to the indicated device. The data
is parsed as individual bytes, and may be in decimal, octal (if
prefixed with a 0), or hexadecimal (if prefixed with a 0x).

The write of the data will be deferred until an ACTION command is
received.

#### dw offset-or-reg-name data ...

Alias for deferred-write.

#### deferred-set offset-or-register-name value

Sets the value of a register using the natural units of the
register type (degrees, volts, etc).

The write of the data will be deferred until an ACTION command is
received.

### Test Commands

These commands are typically only used in test scripts, which can be run by
using:
```
./cli.py -t -f test.cmd
```

#### echo

Prints the rest of the line to the output.

This is mostly useful when processing from a script.

#### test cmd <hex-id> <command> <hex-data> ...

Queues up an expected command packet. The command will be an ascii
version of the command, and data is assumed to be hexadecimal bytes
making up the rest of the packet (i.e. without the 0x prefix).
The packet preamble (2 0xff's), length, and checksum will all be
calculated autmatically.

#### test cmd-raw <hex-data> ...

Queues up an expected command packet. The <data> is expected to
include the preamble, id, length, command, data, and checksum.

#### test rsp <hex-id> <error> <hex-data> ...

Queues up an expected response packet. The error will be an ascii
version of the error code, and data is assumed to be hexadecimal
bytes making up the rest of the packet (i.e. without the 0x prefx).
The packet preamble (2 0xff's), length, and checksum will all be
calculated autmatically.

#### test rsp-raw <hex-data> ...

Queues up an expected response packet. The <hex-data> is expected to
include the preamble, id, error code, length, data, and checksum.

#### test rsp-timeout

Queues up a timeout response.

#### test output "output-compare" <command>

Executes <command> and verified that the output is "output-compare"

#### test error <command>

Executes <command> and verifies that an error occurred.

#### test success <command>

Executes <command> and verifies that no error occurred.

## BeagleBoneBlack Installation

I did up the BeagleBoneBlack installation instructions below and decided to
keep them around as they might prove useful.

To install on a BeagleBone Black:

```bash
wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py

sudo python ez_setup.py
sudo python get-pip.py

sudo pip install virtualenv
sudo pip install virtualenvwrapper

export WORKON_HOME="${HOME}/.venv"
source /usr/local/bin/virtualenvwrapper.sh

mkvirtualenv bioloid
git clone https://github.com/dhylands/Bioloid
cd Bioloid
pip install -e .
export BIOLOID_PORT=/dev/ttyUSB0
./cli.py
help
```

scan will show detected devices
