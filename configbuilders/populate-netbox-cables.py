#!/usr/bin/env python

import shelve
import pprint
import sys
import functools
import re
import yaml
from nbh import NetboxHelper
import ipaddr


def get_vlans(addressing):
    vlans = {}

    for line in addressing:
        if "VLAN" in line:
            if "Description" not in line:
                sys.exit(1)
            desc = ""

            if line["Description"] == "(Temp Staging pre event)":
                line["Description"] = "Temp Staging pre event"
            for c in line["Description"]:
                if c.isalnum():
                    desc += c
                elif c == "(":
                    break
                else:
                    if len(desc) > 0 and desc[len(desc) - 1] != "-":
                        desc += "-"

            vlans[line["VLAN"]] = {
                "ipv4": line["IPv4-Subnet"],
                "ipv4_subnet": ipaddr.IPv4Network(line["IPv4-Subnet"]),
                "name": desc,
                "vlan": int(line["VLAN"]),
                "dhcp": ("dhcp" in line and line["dhcp"] == "y"),
                "sitewide": ("Sitewide" in line and line["Sitewide"] == "y"),
            }

            if "IPv6" in line:
                vlans[line["VLAN"]]["ipv6"] = line["IPv6"]
                vlans[line["VLAN"]]["ipv6_subnet"] = ipaddr.IPv6Network(line["IPv6"])

    return vlans


if __name__ == "__main__":

    helper = NetboxHelper.getInstance()

    switches = shelve.open("data/switches")["list"]
    port_types = shelve.open("data/port_types")["list"]
    links = shelve.open("data/links")["list"]
    addressing = shelve.open("data/addressing")["list"]

    vlans = get_vlans(addressing)
    sidewide = []
    for k, v in vlans.items():
        if v["sitewide"]:
            sidewide.append(k)

    nb_vlans = []
    for v in sidewide:
        nb_vlans.append(helper.get_vlan(v))

    model_dict = {}
    for switch in switches:
        if "Model" in switch:
            model_dict[switch["Hostname"]] = switch["Model"]
    model_dict["ESNORE"] = "DCS-7280SE-68"
    for link in links:
        switch1_type = None
        switch2_type = None
        switch1 = None
        switch2 = None
        i1 = None
        i2 = None
        if link["Switch1"] in model_dict and link["Switch2"] in model_dict:
            switch1_type = helper.get_device_type(model_dict[link["Switch1"]])
            switch2_type = helper.get_device_type(model_dict[link["Switch2"]])
        if switch1_type and switch2_type:
            switch1 = helper.get_switch(link["Switch1"], switch1_type.id)
            switch2 = helper.get_switch(link["Switch2"], switch2_type.id)
        if switch1 and switch2:
            i1 = helper.get_interface_for_device(switch1, link["Switch1-Port1"])
            i2 = helper.get_interface_for_device(switch2, link["Switch2-Port1"])
        if i1 and i2:
            helper.link_two_interfaces(
                i1, i2, f"{switch1} - {switch2}"
            )  # TODO: add non sitewide downstream vlans
            helper.set_interface_tagged_vlan(switch1, str(i1), nb_vlans)
            helper.set_interface_tagged_vlan(switch2, str(i2), nb_vlans)
