#!/usr/bin/env python3
import ipaddr, jinja2, configparser, argparse, shelve, gdata, code, shelve, os, sys, pprint

switches = shelve.open("data/switches")["list"]
links = shelve.open("data/links")["list"]

switch = {}
for sw in switches:
    switch[sw['Hostname']] = sw


for link in links:
    if link['Switch1'] != "ESNORE":
        continue
    if not 'Switch1-Port1' in link:
        continue
    print("interface port-channel", link['Switch1-Port1'].replace("Ethernet", ""))
    print(" description Downlink to", link['Switch2'])
    print(" switchport mode trunk")
    print(" switchport trunk allowed vlan 132,2000-2004," + switch[link['Switch2']]['Camper-VLAN'])
    print(" mtu 9214")
    print(" load-interval 30")
    print(" no shutdown")
    print("")
    print("interface", link['Switch1-Port1'])
    print(" description Downlink to", link['Switch2'], "port", link['Switch2-Port1'])
    print(" channel-group", link['Switch1-Port1'].replace("Ethernet", "") ,"mode active")
    print(" mtu 9214")
    print(" load-interval 30")
    print(" lldp receive")
    print(" lldp transmit")
    print(" no shutdown")
    print("")

