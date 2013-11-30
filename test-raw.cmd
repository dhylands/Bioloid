echo Test some raw packets taken from the AX-12 manual
echo

echo Set the ID of a connected Dynamixel actuator to 1
test cmd-raw ff ff fe 04 03 03 01 f6
test success servo 254 set id 1

echo Read the internal temperature of the Dynamixel actuator with an ID of 1
test cmd-raw ff ff 01 04 02 2b 01 cc
test rsp-raw ff ff 01 03 00 20 db
test output "32C" servo 1 get present-temp

echo Obtain the status packet of the Dynamixel actuator with an ID of 1
test cmd-raw ff ff 01 02 01 fb
test rsp-raw ff ff 01 02 00 fc
test success servo 1 ping

echo Reset the Dynamixel actuator with an ID of 0
test cmd-raw ff ff 00 02 06 f7
test rsp-raw ff ff 00 02 00 fd
test success servo 0 reset

# We don't currently have a sync-write command
# Sync Write example - Set multiple positions and velocities
# Dynamixel actuator with an ID of 0: to position 0x010 with a speed of 0x150
# Dynamixel actuator with an ID of 1: to position 0x220 with a speed of 0x360
# Dynamixel actuator with an ID of 2: to position 0x030 with a speed of 0x170
# Dynamixel actuator with an ID of 0: to position 0x220 with a speed of 0x380

# ff ff fe 18 83 1e 04 
# 00 10 00 50 01 
# 01 20 02 60 03 
# 02 30 00 70 01 
# 03 20 02 80 03 
# 12

# FF FF FE 18 83 1E 04 00 10 00 50
# 01 01 20 02 60 03 02 30 00 70 01 03 20 02 80
# 03 e2

echo Reading the Model Number and Firmware Version for ID of 1
# Model 0x74 = 116 which corresponds to a DX-116
test cmd-raw ff ff 01 04 02 00 03 f5
test rsp-raw ff ff 01 05 00 74 00 08 7d
test output "Read: 0000: 74 00 08" servo 1 read-data model 3

echo Changing the ID to 0 for ID of 1
test cmd-raw FF FF 01 04 03 03 00 F4
test rsp-raw FF FF 01 02 00 FC
test success servo 1 set id 0

echo Changing the Baud Rate to 1M bps
test cmd-raw FF FF 00 04 03 04 01 F3
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set baud-rate 1000000

echo Resetting the Return Delay Time to 4 uSec for an ID of 0
test cmd-raw FF FF 00 04 03 05 02 F1
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set return-delay-time 4

echo Limiting the operating angle range to 0~150 for an ID of 0
test cmd-raw FF FF 00 05 03 08 FF 01 EF
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set ccw-angle-limit 150

echo Resetting the upper limit for the operating temperature to 80C for an ID of 0
test cmd-raw FF FF 00 04 03 0B 50 9D
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set high-limit-temp 80

#echo  Setting the operating voltage to 10V ~ 17V for a Dynamixel actuator with an ID of 0
#test cmd-raw FF FF 00 05 03 0C 64 AA DD
#test rsp-raw FF FF 00 02 00 FD
#test success servo 0 set low-limit-voltage

echo Setting the maximum torque to 50% of its maximum possible value for an ID of 0
test cmd-raw FF FF 00 05 03 0E FF 01 E9
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set max-torque 511

echo Set the Dynamixel actuator with an ID of 0 to never return a Status Packet
test cmd-raw FF FF 00 04 03 10 00 E8
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set status-level none

echo Set the Alarm to blink the LED and Shutdown (Torque off) the actuator when the operating temperature goes over the set limit
test cmd-raw FF FF 00 05 03 11 04 04 DE
test rsp-raw FF FF 00 02 00 FD
#test success servo 0 set alarm-led 4 4
test success servo 0 write-data alarm-led 4 4

echo Turn on the LED and Enable Torque for a Dynamixel actuator with an ID of 0
test cmd-raw FF FF 00 05 03 18 01 01 DD
test rsp-raw FF FF 00 02 00 FD
#test success servo 0 set torque-enable 1 1
test success servo 0 write-data torque-enable 1 1

echo Setting the Compliance Margin to 1 and Compliance Slope to 0x40 for a Dynamixel actuator with an ID of 0
test cmd-raw FF FF 00 07 03 1A 01 01 40 40 59
test rsp-raw FF FF 00 02 00 FD
#test success servo 0 set cw-comp-margin 1 1 0x40 0x40
test success servo 0 write-data cw-comp-margin 1 1 0x40 0x40

echo Position the output of a Dynamixel actuator with an ID of 0 to 180 with an angular velocity of 057RPM
test cmd-raw FF FF 00 07 03 1E 00 02 00 02 D3
test rsp-raw FF FF 00 02 00 FD
#test success servo 0 set goal-position 180 57
test success servo 0 write-data goal-position 0x00 0x02 0x00 0x02

echo Deferred set goal-position of ID=0 to 0
test cmd-raw FF FF 00 05 04 1E 00 00 D8
test rsp-raw FF FF 00 02 00 FD
test success servo 0 deferred-set goal-position 0

echo Deferred set goal-position of ID=1 to 300
test cmd-raw FF FF 01 05 04 1E FF 03 D5
test rsp-raw FF FF 01 02 00 FC
test success servo 1 deferred-set goal-position 300

echo Broadcast Action
test cmd-raw FF FF FE 02 05 FA
test success action

echo Lock all addresses except for Address 0x18 ~ Address0x23 for a Dynamixel actuator with an ID of 0
test cmd-raw FF FF 00 04 03 2F 01 C8
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set lock 1

echo Sample error with trying to change locked actuator
test cmd-raw FF FF 00 05 03 30 40 00 87
test rsp-raw FF FF 00 02 08 F5
test error servo 0 set punch 64

echo Set the minimum power (Punch) to 0x40 for a Dynamixel actuator with an ID of 0
test cmd-raw FF FF 00 05 03 30 40 00 87
test rsp-raw FF FF 00 02 00 FD
test success servo 0 set punch 64


