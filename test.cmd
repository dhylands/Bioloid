echo Test some raw packets taken from the AX-12 manual

echo Set the ID of a connected Dynamixel actuator to 1
test cmd-raw ff ff fe 04 03 03 01 f6
servo 254 set id 1

echo Read the internal temperature of the Dynamixel actuator with an ID of 1
test cmd-raw ff ff 01 04 02 2b 01 cc
test rsp-raw ff ff 01 03 00 20 db
servo 1 get present-temp

echo Obtain the status packet of the Dynamixel actuator with an ID of 1
test cmd-raw ff ff 01 02 01 fb
test rsp-raw ff ff 01 02 00 fc
servo 1 ping

echo Reset the Dynamixel actuator with an ID of 0
test cmd-raw ff ff 00 02 06 f7
test rsp-raw ff ff 00 02 00 fd
servo 0 reset

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

echo Reading the Model Number and Firmware Version of the Dynamixel actuator with an ID of 1
# Model 0x74 = 116 which corresponds to a DX-116
test cmd-raw ff ff 01 04 02 00 03 f5
test rsp-raw ff ff 01 05 00 74 00 08 7d
servo 1 read-data model 3

echo Changing the ID to 0 for a Dynamixel actuator with an ID of 1
test cmd-raw FF FF 01 04 03 03 00 F4
test rsp-raw FF FF 01 02 00 FC
servo 1 set id 0

echo Changing the Baud Rate of a Dynamixel actuator to 1M bps
test cmd-raw FF FF 00 04 03 04 01 F3
test rsp-raw FF FF 00 02 00 FD
servo 0 set baud-rate 1000000

echo Resetting the Return Delay Time to 4 uSec for a Dynamixel actuator with an ID of 0
test cmd-raw FF FF 00 04 03 05 02 F1
test rsp-raw FF FF 00 02 00 FD
servo 0 set return-delay-time 4

#echo Limiting the operating angle range to 0°~150° for a Dynamixel actuator with an ID of 0
#test cmd-raw FF FF 00 05 03 08 FF 01 EF
#test rsp-raw FF FF 00 02 00 FD
#servo 0 

echo Testing ping to servo 1
test cmd 1 ping
test rsp 1 none
servo 1 ping

echo Testing ping to servo 1 (timeout)
test cmd 1 ping
test rsp-timeout
servo 1 ping
