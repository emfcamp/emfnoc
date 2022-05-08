#!/usr/bin/env python3

import shelve
import pprint
import sys
import functools
import re
import yaml
from nbh import NetboxHelper
import ipaddr

MGMT_VLAN = 132


def get_vlans_for_device(device):
    vlans = set()
    for interface in helper.netbox.dcim.interfaces.filter(device_id=device.id):
        if interface.untagged_vlan:
            vlans.add(interface.untagged_vlan)
        elif interface.mode and interface.mode.value == "tagged":
            vlans.update(interface.tagged_vlans)
    return set(map(lambda x: x.id, vlans))


def walk_tree_r(path, vlans=[], cables=[]):
    cur_vlans = get_vlans_for_device(path[-1])
    vlans = vlans.copy()
    vlans.append(cur_vlans)
    if path[-1] in path[:-1]:
        print(path[:-1], vlans[1:-1], cables[-1])
        if len(cables[:-1]) != 0:
            rvlan = set()
            for cable, vlan in zip(reversed(cables[:-1]), reversed(vlans[1:-1])):
                rvlan = rvlan.union(vlan)
                a_tagged = rvlan.union(cable.termination_a.tagged_vlans)
                b_tagged = rvlan.union(cable.termination_b.tagged_vlans)
                i1 = cable.termination_a
                i2 = cable.termination_b
                i1.tagged_vlans = list(a_tagged)
                i1.save()
                i2.tagged_vlans = list(b_tagged)
                i2.save()
                rvlan = rvlan.union(a_tagged, b_tagged)
        return
    device = helper.netbox.dcim.devices.get(name=path[-1])
    cur_vlans = get_vlans_for_device(path[-1])
    for interface in helper.netbox.dcim.interfaces.filter(device_id=device.id):
        if interface.connected_endpoint_reachable:
            npath = path.copy()
            npath.append(interface.link_peer.device)
            ncables = cables.copy()
            ncables.append(interface.cable)
            walk_tree_r(npath, vlans, ncables)


if __name__ == "__main__":

    with open("netbox.yml") as netbox_cfg_file:
        try:
            netbox_cfg = yaml.safe_load(netbox_cfg_file)
        except yaml.YAMLError as yamlerror:
            print(yamlerror)
            sys.exit(1)

    switches = shelve.open("data/switches")["list"]
    port_types = shelve.open("data/port_types")["list"]
    links = shelve.open("data/links")["list"]
    addressing = shelve.open("data/addressing")["list"]
    helper = NetboxHelper(
        url=netbox_cfg["url"], token=netbox_cfg["token"], mgmt_vlan=MGMT_VLAN
    )

    startpoint = "ESNORE"
    device = helper.netbox.dcim.devices.get(name=startpoint)
    walk_tree_r([device])
