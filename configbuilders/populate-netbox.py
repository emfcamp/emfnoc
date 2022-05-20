#!/usr/bin/env python3
import argparse
import sys

from nocsheet import NocSheetHelper
from nbh import NetboxHelper


def populate_netbox(nocsheet, verbose):
    helper = NetboxHelper.getInstance()

    devices = nocsheet.get_shelf(NocSheetHelper.SHELF_DEVICES)
    port_types = nocsheet.get_shelf(NocSheetHelper.SHELF_PORT_TYPES)
    vlans = nocsheet.get_shelf(NocSheetHelper.SHELF_VLANS)

    vlan_lut = {}
    for port_type in port_types:
        vlan_lut[port_type["Port-Type"]] = port_type["VLAN"]

    for device in devices:
        if verbose: print('Checking %s' % device['Hostname'])
        if "Model" in device.keys():
            if verbose: print('Doing %s' % device['Hostname'])

            device_type = helper.get_device_type(device["Model"])
            if not device_type:
                print('Warning, device type %s for %s does not exist, skipping!' % (device['Model'], device['Hostname']))
                continue

            device_type_id = device_type.id
            port_prefix = device.get("Port-Prefix")
            port_start = int(device.get("Port-Start", "1")) - 1
            copper_ports = helper.get_sum_copper_ports(device["Model"])
            port_index = copper_ports + port_start
            nb_switch = helper.get_switch(device["Hostname"], device_type_id)

            helper.create_inband_mgmt(nb_switch)
            # For now hardcode a /24
            if "Mgmt-IP" in device:
                helper.set_inband_mgmt_ip(nb_switch, device["Mgmt-IP"] + "/24")

            # Allocate the special-VLAN ports from the top down
            for key in device.keys():
                if key[0] == "#":
                    vlan = helper.get_vlan(vlan_lut[key[1:]], key[1:])
                    for i in range(int(device[key])):
                        helper.set_interface_vlan(
                            nb_switch, port_prefix + str(port_index), vlan
                        )
                        port_index -= 1

            # See if it needs a camper VLAN, look for a VLAN with camper='y' and this switch name in the Switch column
            camper_vlan_id = None
            for vlandef in vlans:
                if 'Camper' in vlandef and vlandef['Camper'] == 'y':
                    vlandef_switches = vlandef['Switch'].split(',')
                    if device['Hostname'] in vlandef_switches:
                        if camper_vlan_id is not None:
                            print('Warning: multiple matching Camper-VLANs for %s' % device['Hostname'], file=sys.stderr)
                        camper_vlan_id = int(vlandef['VLAN'])

            if camper_vlan_id is None:
                print('Warning: no Camper-VLAN found for %s' % device['Hostname'])

            if verbose: print('Camper-VLAN for %s is %d' % (device['Hostname'], camper_vlan_id))

            for k in range(port_start + 1, port_index + 1):
                helper.set_interface_vlan(
                    nb_switch, port_prefix + str(k), camper_vlan_id if camper_vlan_id is not None else 1
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate Netbox with summary data from google sheets."
    )

    nocsheet = NocSheetHelper()
    nocsheet.add_arguments(parser)

    parser.add_argument("--populate", action="store_true", help="Populate data into Netbox")
    parser.add_argument("--verbose", action="store_true", help="Print what it's doing")

    args = parser.parse_args()

    done_something = nocsheet.process_arguments(args)

    if args.populate:
        populate_netbox(nocsheet, args.verbose)
        done_something = True

    if not done_something:
        print("Nothing to do, try " + sys.argv[0] + " --help")
