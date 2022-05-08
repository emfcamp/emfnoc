import shelve
import pprint
import sys
import functools
import re
import yaml
from nbh import NetboxHelper

MGMT_VLAN = 132


if __name__ == "__main__":

    with open("netbox.yml") as netbox_cfg_file:
        try:
            netbox_cfg = yaml.safe_load(netbox_cfg_file)
        except yaml.YAMLError as yamlerror:
            print(yamlerror)
            sys.exit(1)

    switches = shelve.open("data/switches")["list"]
    port_types = shelve.open("data/port_types")["list"]
    helper = NetboxHelper(
        url=netbox_cfg["url"], token=netbox_cfg["token"], mgmt_vlan=MGMT_VLAN
    )

    vlan_lut = {}
    for port_type in port_types:
        vlan_lut[port_type["Port-Type"]] = port_type["VLAN"]

    for switch in switches:
        if "Model" in switch.keys():
            device_type = helper.get_device_type(switch["Model"])
            if not device_type:
                continue
            device_type_id = device_type.id
            port_prefix = switch.get("Port-Prefix", "")
            port_start = int(switch.get("Port-Start", "1")) - 1
            copper_ports = helper.get_sum_copper_ports(switch["Model"])
            port_index = copper_ports + port_start
            nb_switch = helper.get_switch(switch["Hostname"], device_type_id)

            helper.create_inband_mgmt(nb_switch)
            # For now hardcode a /24
            if "Mgmt-IP" in switch:
                helper.set_inband_mgmt_ip(nb_switch, switch["Mgmt-IP"] + "/24")
            for key in switch.keys():
                if key[0] == "#":
                    vlan = helper.get_vlan(vlan_lut[key[1:]], key[1:])
                    for i in range(int(switch[key])):
                        helper.set_interface_vlan(
                            nb_switch, port_prefix + str(port_index), vlan
                        )
                        port_index -= 1
            if "Camper-VLAN" in switch:
                camper_vlan = helper.get_vlan(switch["Camper-VLAN"], "Camper-vlan")
                for k in range(port_start + 1, port_index + 1):
                    helper.set_interface_vlan(
                        nb_switch, port_prefix + str(k), camper_vlan
                    )
