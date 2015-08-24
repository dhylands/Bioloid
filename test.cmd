echo Testing ping to servo 1
test cmd 1 ping
test rsp 1 none
test success servo 1 ping

echo Testing ping to servo 1 (timeout)
test cmd 1 ping
test rsp-timeout
test error servo 1 ping

echo Testing ping to servo 1 (other error)
test cmd 1 ping
test rsp 1 overheating
test error servo 1 ping
