#!/usr/bin/env python
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
        self.links = nocsheet.get_shelf(NocSheetHelper.SHELF_LINKS)

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

                    device_role_id = DEVICE_ROLE_OVERRIDES[
                        hostname] if hostname in DEVICE_ROLE_OVERRIDES else DEVICE_ROLE_DEFAULT

                    nb_switch = self.helper.create_switch(hostname, device_type_id, device_role_id, device['Location'])

                    # For now hardcode a /24
                    # TODO just get the prefix that has already been created
                    if 'Mgmt-IP' in device:
                        self.helper.create_inband_mgmt(nb_switch)
                        self.helper.set_inband_mgmt_ip(nb_switch,
                                                       device["Mgmt-IP"] + self.helper.config.get('mgmt_subnet_length'))
                    # TODO remove any SVIs that are not the mgmt vlan

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

                    if 'Reserved-Ports' in device:
                        port_index -= int(device['Reserved-Ports'])

                    # Allocate the special-VLAN ports from the top down
                    for key in reversed(device.keys()):
                        if key[0] == "#":
                            vlan = self.helper.get_vlan(vlan_lut[key[1:]])
                            for i in range(int(device[key])):
                                if port_index <= port_start:
                                    print('More special ports allocated on %s than actually exist' % hostname)
                                    sys.exit(1)
                                self.helper.set_interface_access(
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
                        self.helper.set_interface_access(
                            nb_switch, port_prefix + str(k), camper_vlan
                        )

    # This creates a direct cable for every logical link even if it's getting coupled.
    # TODO for a future year, we could model the physical fibre by adding couplers as "patch panels" - this would
    # also serve to validate the design and enable the production of a physical diagram
    def populate_links(self):

        # all switches with the leafs last. this assumes the links tab is in such an order
        # all_switches = []
        # the switches' uplink ports, switchname->(uplink interface or lag from switch, downlink from parent switch)
        # uplinks = {}

        # "next lag offset" per switchname
        lag_counter = {}

        with click.progressbar(self.links, label='Links',
                               item_show_func=lambda item: '%s-%s' %
                                                           (item['Switch1'], item['Switch2']) if item else None) as bar:
            for link in bar:
                switch1 = self.helper.get_switch(link['Switch1'])
                switch2 = self.helper.get_switch(link['Switch2'])

                # if switch1 not in all_switches:
                #     all_switches.append(switch1)
                # if switch2 not in all_switches:
                #     all_switches.append(switch2)

                switch1_int1 = self.helper.get_interface_for_device(switch1, link['Switch1-Port1'])
                switch2_int1 = self.helper.get_interface_for_device(switch2, link['Switch2-Port1'])

                self.helper.link_two_interfaces(switch1_int1, switch2_int1, f"{switch1} - {switch2}")

                # If there is a second port, we need to make a LAG:
                if 'Switch1-Port2' in link:
                    switch1_int2 = self.helper.get_interface_for_device(switch1, link['Switch1-Port2'])
                    switch2_int2 = self.helper.get_interface_for_device(switch2, link['Switch2-Port2'])

                    switch1_int1.description = 'LAG member: downlink to %s port %s' % (switch2, switch2_int1)
                    switch1_int1.save()
                    switch2_int1.description = 'LAG member: uplink to %s port %s' % (switch1, switch1_int1)
                    switch2_int1.save()
                    switch1_int2.description = 'LAG member: downlink to %s port %s' % (switch2, switch2_int2)
                    switch1_int2.save()
                    switch2_int2.description = 'LAG member: uplink to %s port %s' % (switch1, switch1_int2)
                    switch2_int2.save()

                    self.helper.link_two_interfaces(switch1_int2, switch2_int2, f"{switch1} - {switch2}")

                    switch1_lag_num = self._get_next_lag_num(switch1, lag_counter)
                    switch2_lag_num = self._get_next_lag_num(switch2, lag_counter)

                    switch1_lag = self.helper.create_lag(switch1, switch1_lag_num, [switch1_int1, switch1_int2])
                    switch2_lag = self.helper.create_lag(switch2, switch2_lag_num, [switch2_int1, switch2_int2])

                    switch1_trunk = switch1_lag
                    switch2_trunk = switch2_lag
                else:
                    switch1_trunk = switch1_int1
                    switch2_trunk = switch2_int1

                switch1_trunk.description = 'DOWNLINK: %s port %s' % (switch2, switch2_trunk.name)
                switch2_trunk.description = 'UPLINK: %s port %s' % (switch1, switch1_trunk.name)

                switch1_trunk.mode = 'tagged'
                switch2_trunk.mode = 'tagged'
                switch1_trunk.untagged_vlan = {'vid': self.helper.mgmt_vlan}
                switch2_trunk.untagged_vlan = {'vid': self.helper.mgmt_vlan}

                switch1_trunk.save()
                switch2_trunk.save()

                # uplinks[switch2.name] = (switch2_trunk, switch1_trunk)
            #
            # # Assign uplinks, starting with the leafs
            # all_switches.reverse()
            # with click.progressbar(all_switches, label='Uplinks',
            #                        item_show_func=lambda item: item.name if item else None) as bar:
            #
            #     for switch in bar:
            #         uplink_int = uplinks[switch.name][0]
            #         downlink_int = uplinks[switch.name][1]
            #
            #         # What VLANs do we need?
            #         switch_vlans = self.helper.get_vlans_for_switch(switch, uplink_int)
            #         # todo add any ports needed by children
            #         # TODO: add non sitewide downstream vlans
            #
            #         self.helper.set_interface_trunk(uplink_int, switch_vlans)
            #         self.helper.set_interface_trunk(downlink_int, switch_vlans)

    def _get_next_lag_num(self, switch, lag_counter):
        switch_lag_num = lag_counter[switch.name] if switch.name in lag_counter else 0
        lag_counter[switch.name] = switch_lag_num + 1
        return switch_lag_num


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
    parser.add_argument("--populate-links", action="store_true", help="Populate links between switches")
    # parser.add_argument("--populate-trunks", action="store_true", help="Assigns trunks to uplinks and downlinks")

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

    if args.populate_all or args.populate_links:
        populator.populate_links()
        done_something = True

    # if args.populate_all or args.populate_trunks:
    #     populator.populate_trunks()
    #     done_something = True
    # TODO move from fixup-vlans.py

    # populator.populate_core_svis()

    if not done_something:
        print("Nothing to do, try " + sys.argv[0] + " --help")
