#!/usr/bin/env python3
import argparse
import sys

import click

from nbh import NetboxHelper
from nocsheet import NocSheetHelper

# TODO should warn about things that exist on this tenant that we didn't create (old stuff that probably needs removing)

# no time to do this in a better way right now
DEVICE_ROLE_DEFAULT = 3
DEVICE_ROLE_OVERRIDES = {'ESNORE': 2, 'LATVIA': 1}


class NetboxPopulator:
    nocsheet: NocSheetHelper
    helper: NetboxHelper
    verbose: bool

    def __init__(self, nocsheet: NocSheetHelper, verbose: bool = False):
        self.nocsheet = nocsheet
        self.verbose = verbose
        self.helper = NetboxHelper.getInstance()
        self.helper.set_verbose(verbose)

        self.devices = nocsheet.get_shelf(NocSheetHelper.SHELF_DEVICES)
        self.port_types = nocsheet.get_shelf(NocSheetHelper.SHELF_PORT_TYPES)
        self.vlans = nocsheet.get_shelf(NocSheetHelper.SHELF_VLANS)
        self.locations = nocsheet.get_shelf(NocSheetHelper.SHELF_LOCATIONS)

    def populate_locations(self):
        with click.progressbar(self.locations, label='Locations',
                               item_show_func=lambda item: item['Location-Name'] if item else None) as bar:
            for locationdef in bar:
                self.helper.create_location(locationdef['Location-Name'])

    def populate_vlans(self):
        with click.progressbar(self.vlans, label='VLANs and Prefixes',
                               item_show_func=lambda item: item['Name'] if item else None) as bar:
            for vlandef in bar:
                vlan = self.helper.create_vlan(int(vlandef['VLAN']), vlandef['Name'],
                                               vlandef['Description'] if 'Description' in vlandef else '')

                dhcp = vlandef['DHCP'] == 'y' if 'DHCP' in vlandef else False
                dhcp_reserved = int(vlandef['DHCP-Reserved']) if 'DHCP-Reserved' in vlandef else None

                if 'IPv4-Prefix' in vlandef:
                    self.helper.create_prefix(vlandef['IPv4-Prefix'], vlandef['Name'], vlan,
                                              dhcp, dhcp_reserved)
                if 'IPv6-Prefix' in vlandef:
                    self.helper.create_prefix(vlandef['IPv6-Prefix'], vlandef['Name'], vlan,
                                              dhcp, dhcp_reserved)

    def populate_switches(self):
        with click.progressbar(self.devices, label='Switches',
                               item_show_func=lambda item: item['Hostname'] if item else None) as bar:

            for device in bar:
                if "Model" in device.keys():
                    device_type = self.helper.get_device_type(device["Model"])
                    hostname = device['Hostname']
                    if not device_type:
                        print('Warning: device type %s for %s does not exist, skipping!' %
                              (device['Model'], hostname))
                        continue

                    device_type_id = device_type.id

                    device_role_id = DEVICE_ROLE_OVERRIDES[hostname] if hostname in DEVICE_ROLE_OVERRIDES else DEVICE_ROLE_DEFAULT

                    nb_switch = self.helper.create_switch(hostname, device_type_id, device_role_id, device['Location'])

                    # For now hardcode a /24
                    # TODO just get the prefix that has already been created
                    if 'Mgmt-IP' in device:
                        self.helper.create_inband_mgmt(nb_switch)
                        self.helper.set_inband_mgmt_ip(nb_switch,
                                                       device["Mgmt-IP"] + self.helper.config.get('mgmt_subnet_length'))

    def populate_switch_ports(self):
        vlan_lut = {}
        for port_type in self.port_types:
            vlan_lut[port_type["Port-Type"]] = port_type["VLAN"]

        with click.progressbar(self.devices, label='Switch Ports',
                               item_show_func=lambda item: item['Hostname'] if item else None) as bar:
            for device in bar:
                if 'Model' in device.keys():
                    hostname = device['Hostname']
                    if not 'Port-Prefix' in device.keys():
                        if self.verbose:
                            print('Warning: not doing ports on %s because no Port-Prefix set' % hostname)
                        continue

                    nb_switch = self.helper.get_switch(hostname)

                    port_start = int(device['Port-Start']) - 1
                    copper_ports = self.helper.get_sum_copper_ports(device['Model'])
                    port_prefix = device['Port-Prefix']
                    port_index = copper_ports + port_start

                    # Allocate the special-VLAN ports from the top down
                    for key in device.keys():
                        if key[0] == "#":
                            vlan = self.helper.get_vlan(vlan_lut[key[1:]])
                            for i in range(int(device[key])):
                                self.helper.set_interface_vlan(
                                    nb_switch, port_prefix + str(port_index), vlan
                                )
                                port_index -= 1

                    # See if it needs a camper VLAN, look for a VLAN with camper='y' and this switch name in the Switch column
                    camper_vlan_id = None
                    for vlandef in self.vlans:
                        if 'Camper' in vlandef and vlandef['Camper'] == 'y':
                            vlandef_switches = vlandef['Switch'].split(',')
                            if hostname in vlandef_switches:
                                if camper_vlan_id is not None:
                                    print('Warning: multiple matching Camper-VLANs for %s' % hostname,
                                          file=sys.stderr)
                                camper_vlan_id = int(vlandef['VLAN'])

                    if camper_vlan_id is None:
                        print('Warning: no Camper-VLAN found for %s' % hostname)

                    if self.verbose: print('Camper-VLAN for %s is %d' % (hostname, camper_vlan_id))

                    camper_vlan = self.helper.get_vlan(camper_vlan_id)

                    for k in range(port_start + 1, port_index + 1):
                        self.helper.set_interface_vlan(
                            nb_switch, port_prefix + str(k), camper_vlan
                        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate Netbox with summary data from google sheets."
    )

    nocsheet = NocSheetHelper()
    nocsheet.add_arguments(parser)

    parser.add_argument("--verbose", action="store_true", help="Print what it's doing")
    parser.add_argument("--populate-all", action="store_true", help="Populate EVERYTHING into Netbox")
    parser.add_argument("--populate-locations", action="store_true", help="Populate locations")
    parser.add_argument("--populate-vlans", action="store_true", help="Populate VLANs and prefixes")
    parser.add_argument("--populate-switches", action="store_true", help="Populate switches")
    parser.add_argument("--populate-switch-ports", action="store_true", help="Populate switch ports")

    args = parser.parse_args()

    done_something = nocsheet.process_arguments(args)

    populator = NetboxPopulator(nocsheet, args.verbose)

    if args.populate_all or args.populate_locations:
        populator.populate_locations()
        done_something = True

    if args.populate_all or args.populate_vlans:
        populator.populate_vlans()
        done_something = True

    if args.populate_all or args.populate_switches:
        populator.populate_switches()
        done_something = True

    if args.populate_all or args.populate_switch_ports:
        populator.populate_switch_ports()
        done_something = True

    # populator.populate_core_svis()

    if not done_something:
        print("Nothing to do, try " + sys.argv[0] + " --help")
