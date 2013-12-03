echo Testing Register (raw values)
test error servo 1 set-raw punch -1
test cmd 1 write 30 0 0
test rsp 1 none
test success servo 1 set-raw punch 0
test cmd 1 write 30 ff 3
test rsp 1 none
test success servo 1 set-raw punch 1023
test error servo 1 set-raw punch 1024
test cmd 1 read 30 2
test rsp 1 none 0 0
test output "0" servo 1 get-raw punch
test cmd 1 read 30 2
test rsp 1 none ff 03
test output "1023" servo 1 get-raw punch

echo Testing Register
test error servo 1 set punch -1
test cmd 1 write 30 0 0
test rsp 1 none
test success servo 1 set punch 0
test cmd 1 write 30 ff 3
test rsp 1 none
test success servo 1 set punch 1023
test error servo 1 set punch 1024
test cmd 1 read 30 2
test rsp 1 none ff 03
test output "1023" servo 1 get punch

echo Testing RegisterOnOff
test error servo 1 set led foo
test cmd 1 write 19 1
test rsp 1 none
test success servo 1 set led on
test cmd 1 write 19 0
test rsp 1 none
test success servo 1 set led off
test error servo 1 set-raw led 2
test cmd 1 read 19 1
test rsp 1 none 0
test output "off" servo 1 get led
test cmd 1 read 19 1
test rsp 1 none 1
test output "on" servo 1 get led

echo Testing RegisterDirection
test error mini-io 1 set control_digital_dir_0 foo
test cmd 1 write 19 1
test rsp 1 none
test success mini-io 1 set led on
test cmd 1 write 6 0
test rsp 1 none
test success mini-io 1 set control_digital_dir_0 off
test error mini-io 1 set-raw control_digital_dir_0 2
test cmd 1 read 6 1
test rsp 1 none 0
test output "input" mini-io 1 get control_digital_dir_0
test cmd 1 read 6 1
test rsp 1 none 1
test output "output" mini-io 1 get control_digital_dir_0

echo Testing RegisterBaudRate
test error servo 1 set baud-rate foo
test error servo 1 set baud-rate 0
test error servo 1 set baud-rate 1
test error servo 1 set baud-rate 7842
test cmd 1 write 04 fe
test rsp 1 none
test success servo 1 set baud-rate 7843
test cmd 1 write 04 0
test rsp 1 none
test success servo 1 set baud-rate 2000000
test error servo 1 set baud-rate 2000001
test cmd 1 read 04 1
test rsp 1 none 1
test output "1000000 bps" servo 1 get baud-rate

echo Testing RegisterAngle
test error servo 1 set goal-position foo
test cmd 1 write 1e 0 0
test rsp 1 none
test success servo 1 set goal-position 0
test cmd 1 write 1e 1 0
test rsp 1 none
test success servo 1 set goal-position 0.3
test cmd 1 write 1e ff 3
test rsp 1 none
test success servo 1 set goal-position 300
test error servo 1 set goal-position 300.2
test cmd 1 read 1e 2
test rsp 1 none 0 0
test output "0.0 deg" servo 1 get goal-position
test cmd 1 read 1e 2
test rsp 1 none ff 3
test output "300.0 deg" servo 1 get goal-position

echo Testing RegisterTemperature
test error servo 1 set high-limit-temp foo
test error servo 1 set high-limit-temp 10.3
test cmd 1 write 0b 0
test rsp 1 none
test success servo 1 set high-limit-temp 0
test cmd 1 write 0b 1
test rsp 1 none
test success servo 1 set high-limit-temp 1
test cmd 1 write 0b 95
test rsp 1 none
test success servo 1 set high-limit-temp 149
test cmd 1 write 0b 96
test rsp 1 none
test success servo 1 set high-limit-temp 150
test cmd 1 write 0b 97
test rsp 1 none
test error servo 1 set high-limit-temp 151
test cmd 1 read 0b 1
test rsp 1 none 0
test output "0C" servo 1 get high-limit-temp
test cmd 1 read 0b 1
test rsp 1 none 96
test output "150C" servo 1 get high-limit-temp

echo Testing RegisterVoltage
test error servo 1 set high-limit-voltage foo
test error servo 1 set high-limit-voltage 4.9
test cmd 1 write 0d 32
test rsp 1 none
test success servo 1 set high-limit-voltage 5.0
test cmd 1 write 0d 95
test rsp 1 none
test success servo 1 set high-limit-voltage 14.9
test cmd 1 write 0d 96
test rsp 1 none
test success servo 1 set high-limit-voltage 15.0
test error servo1 set high-limit-voltage 15.1
test cmd 1 read 0d 1
test rsp 1 none 32
test output "5.0V" servo 1 get high-limit-voltage
test cmd 1 read 0d 1
test rsp 1 none 96
test output "15.0V" servo 1 get high-limit-voltage

echo Testing RegisterStatusRet
test error servo 1 set status-level foo
test cmd 1 write 10 0
test rsp 1 none
test success servo 1 set status-level none
test cmd 1 write 10 1
test rsp 1 none
test success servo 1 set status-level read
test cmd 1 write 10 2
test rsp 1 none
test success servo 1 set status-level all
test cmd 1 read 10 1
test rsp 1 none 0
test output "none" servo 1 get status-level
test cmd 1 read 10 1
test rsp 1 none 1
test output "read" servo 1 get status-level
test cmd 1 read 10 1
test rsp 1 none 2
test output "all" servo 1 get status-level

echo Testing RegisterAlarm
test error servo 1 set alarm-led foo
test cmd 1 write 11 0
test rsp 1 none
test success servo 1 set alarm-led none
test cmd 1 write 11 1
test rsp 1 none
test success servo 1 set alarm-led inputvoltage
test cmd 1 write 11 2
test rsp 1 none
test success servo 1 set alarm-led anglelimit
test cmd 1 write 11 4
test rsp 1 none
test success servo 1 set alarm-led overheating
test cmd 1 write 11 8
test rsp 1 none
test success servo 1 set alarm-led range
test cmd 1 write 11 10
test rsp 1 none
test success servo 1 set alarm-led checksum
test cmd 1 write 11 20
test rsp 1 none
test success servo 1 set alarm-led overload
test cmd 1 write 11 40
test rsp 1 none
test success servo 1 set alarm-led instruction
test cmd 1 write 11 3
test rsp 1 none
test success servo 1 set alarm-led inputvoltage,anglelimit
test cmd 1 write 11 30
test rsp 1 none
test success servo 1 set alarm-led overload,checksum
test cmd 1 write 11 33
test rsp 1 none
test success servo 1 set alarm-led overload,checksum,inputvoltage,anglelimit
test cmd 1 write 11 7f
test rsp 1 none
test success servo 1 set alarm-led all
test cmd 1 read 11 1
test rsp 1 none 0
test output "None" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 1
test output "InputVoltage" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 2
test output "AngleLimit" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 4
test output "OverHeating" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 8
test output "Range" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 10
test output "Checksum" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 20
test output "Overload" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 40
test output "Instruction" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 03
test output "InputVoltage,AngleLimit" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 30
test output "Checksum,Overload" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 33
test output "InputVoltage,AngleLimit,Checksum,Overload" servo 1 get alarm-led
test cmd 1 read 11 1
test rsp 1 none 7f
test output "All" servo 1 get alarm-led

echo Testing RegisterAngularVelocity
test error servo 1 set moving-speed foo
test cmd 1 write 20 0 0
test rsp 1 none
test success servo 1 set moving-speed 0
test cmd 1 write 20 fe 03
test rsp 1 none
test success servo 1 set moving-speed 113.9
test cmd 1 write 20 ff 03
test rsp 1 none
test success servo 1 set moving-speed 114
test error servo 1 set moving-speed 114.1
test cmd 1 read 20 2
test rsp 1 none 0 0
test output "0.0 RPM" servo 1 get moving-speed
test cmd 1 read 20 2
test rsp 1 none ff 03
test output "114.0 RPM" servo 1 get moving-speed

echo Testing RegisterLoad
test cmd 1 read 28 2
test rsp 1 none 00 00
test output "CCW 0" servo 1 get present-load
test cmd 1 read 28 2
test rsp 1 none 01 00
test output "CCW 1" servo 1 get present-load
test cmd 1 read 28 2
test rsp 1 none ff 03
test output "CCW 1023" servo 1 get present-load
test cmd 1 read 28 2
test rsp 1 none 00 04
test output "CW 0" servo 1 get present-load
test cmd 1 read 28 2
test rsp 1 none 01 04
test output "CW 1" servo 1 get present-load
test cmd 1 read 28 2
test rsp 1 none ff 07
test output "CW 1023" servo 1 get present-load

