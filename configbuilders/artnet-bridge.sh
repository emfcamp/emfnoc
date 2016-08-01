#!/bin/bash
# Upload to arista switch using copy sftp://user@ip/path/to/artnet-bridge.sh flash:artnet-bridge.sh

brctl addbr artnet
brctl addif artnet ma1
brctl addif artnet vlan2001
ip link set up dev artnet

