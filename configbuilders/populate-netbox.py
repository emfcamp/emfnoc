#!/usr/bin/env python
import argparse
import ipaddress
import re
import sys
from textwrap import wrap
import pprint
import click

from nbh import NetboxHelper
from nocsheet import NocSheetHelper

# TODO should warn about things that exist on this tenant that we didn't create (old stuff that probably needs removing)

# no time to do this in a better way right now
DEVICE_ROLE_ACCESS_SWITCH = 3
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
        mgmt_domain = self.helper.config.get('mgmt_domain')

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
                        hostname] if hostname in DEVICE_ROLE_OVERRIDES else DEVICE_ROLE_ACCESS_SWITCH

                    asset_tag = device['Asset-Tag'] if 'Asset-Tag' in device else None
                    serial = device['Serial'] if 'Serial' in device else ''

                    camper_vlan_vid = self._get_camper_vlan(hostname)

                    if device_role_id == DEVICE_ROLE_ACCESS_SWITCH and camper_vlan_vid is None:
                        print('Warning: no Camper-VLAN found for %s' % hostname)

                    nb_switch = self.helper.create_switch(hostname, device_type_id, device_role_id, device['Location'],
                                                          asset_tag, serial, camper_vlan_vid=camper_vlan_vid)

                    dns = '%s.%s' % (hostname, mgmt_domain)
                    mgmt_mac = device['MAC-Address'].lower() if 'MAC-Address' in device else None
                    if mgmt_mac:
                        mgmt_mac = mgmt_mac.replace('.', '')
                        if re.search('^[0-9a-f]{12}$', mgmt_mac):
                            mgmt_mac = ':'.join(wrap(mgmt_mac, 2))

                    # For now hardcode a /24
                    # TODO just get the prefix that has already been created
                    if 'Mgmt-IP' in device:
                        self.helper.create_inband_mgmt(nb_switch)
                        self.helper.set_inband_mgmt_ip(nb_switch,
                                                       device["Mgmt-IP"] + self.helper.config.get('mgmt_subnet_length'),
                                                       dns, mgmt_mac)
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

                    port_start = int(device['Port-Start'])
                    copper_ports = self.helper.get_sum_copper_ports(device['Model'])
                    port_prefix = device['Port-Prefix']
                    port_index = copper_ports + port_start - 1

                    if 'Reserved-Ports' in device:
                        port_index -= int(device['Reserved-Ports'])

                    # Allocate the special-VLAN ports from the top down
                    for key in reversed(device.keys()):
                        if key[0] == "#":
                            vlan = self.helper.get_vlan(vlan_lut[key[1:]])
                            for i in range(int(device[key])):
                                if port_index < port_start:
                                    print('More special ports allocated on %s than actually exist' % hostname)
                                    sys.exit(1)
                                self.helper.set_interface_access(
                                    nb_switch, port_prefix + str(port_index), vlan
                                )
                                port_index -= 1

                    camper_vlan_vid = nb_switch.custom_fields['camper_vlan_vid']

                    if camper_vlan_vid is None:
                        print('Warning: no Camper-VLAN found for %s' % hostname)

                    if self.verbose: print('Camper-VLAN for %s is %d' % (hostname, camper_vlan_vid))

                    camper_vlan = self.helper.get_vlan(camper_vlan_vid)

                    for k in range(port_start, port_index + 1):
                        self.helper.set_interface_access(
                            nb_switch, port_prefix + str(k), camper_vlan
                        )

    def _get_camper_vlan(self, switch_hostname):
        # See if it needs a camper VLAN, look for a VLAN with camper='y' and this switch name in the Switch column
        camper_vlan_vid = None
        for vlandef in self.vlans:
            if 'Camper' in vlandef and vlandef['Camper'] == 'y':
                vlandef_switches = vlandef['Switch'].split(',')
                if switch_hostname in vlandef_switches:
                    if camper_vlan_vid is not None:
                        print('Warning: multiple matching Camper-VLANs for %s' % switch_hostname,
                              file=sys.stderr)
                    camper_vlan_vid = int(vlandef['VLAN'])
        return camper_vlan_vid

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

                    switch1_int1.description = 'DOWNLINK: %s port %s (LAG member)' % (switch2, switch2_int1)
                    switch1_int1.save()
                    switch2_int1.description = 'UPLINK: %s port %s (LAG member)' % (switch1, switch1_int1)
                    switch2_int1.save()
                    switch1_int2.description = 'DOWNLINK: %s port %s (LAG member)' % (switch2, switch2_int2)
                    switch1_int2.save()
                    switch2_int2.description = 'UPLINK: %s port %s (LAG member)' % (switch1, switch1_int2)
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

    def populate_trunks(self):
        startpoint = "ESNORE"
        device = self.helper.netbox.dcim.devices.get(name=startpoint)
        self._walk_tree_r([device])

    def _get_vlans_for_device(self, device, end=False):
        vlans = set()
        for interface in self.helper.netbox.dcim.interfaces.filter(device_id=device.id):
            if interface.untagged_vlan:
                vlans.add(interface.untagged_vlan)
            elif interface.mode and interface.mode.value == "tagged" and not interface.connected_endpoint_reachable:
                vlans.update(interface.tagged_vlans)

        return set(map(lambda x: x.id, vlans))

    def _walk_tree_r(self, path, vlans=[], cables=[]):
        cur_vlans = self._get_vlans_for_device(path[-1])
        vlans = vlans.copy()
        vlans.append(cur_vlans)
        if path[-1] in path[:-1]:
            print(path[:-1], vlans[1:-1], cables[-1])
            if len(cables[:-1]) != 0:
                rvlan = set()
                for cable, vlan in zip(reversed(cables[:-1]), reversed(vlans[1:-1])):
                    rvlan = rvlan.union(vlan)
                    a_tagged = list(
                        rvlan.union(map(lambda x: x if type(x) == int else x.id, cable.termination_a.tagged_vlans)))
                    b_tagged = list(
                        rvlan.union(map(lambda x: x if type(x) == int else x.id, cable.termination_b.tagged_vlans)))
                    i1 = cable.termination_a
                    i2 = cable.termination_b
                    if i1.untagged_vlan and i1.untagged_vlan.id in a_tagged:
                        a_tagged.remove(i1.untagged_vlan.id)
                    i1.tagged_vlans = a_tagged
                    if i1.lag:
                        lag_id = i1.lag.id
                        lag_int = self.helper.netbox.dcim.interfaces.get(lag_id)
                        if lag_int.untagged_vlan and lag_int.untagged_vlan.id in a_tagged:
                            a_tagged.remove(lag_int.untagged_vlan.id)
                        lag_int.tagged_vlans = a_tagged
                        lag_int.save()
                        i1.tagged_vlans = []
                        i1.mode = None
                    i1.save()
                    if i2.untagged_vlan and i2.untagged_vlan.id in b_tagged:
                        b_tagged.remove(i2.untagged_vlan.id)
                    i2.tagged_vlans = b_tagged
                    if i2.lag:
                        lag_id = i2.lag.id
                        lag_int = self.helper.netbox.dcim.interfaces.get(lag_id)
                        if lag_int.untagged_vlan and lag_int.untagged_vlan.id in b_tagged:
                            b_tagged.remove(lag_int.untagged_vlan.id)
                        lag_int.tagged_vlans = b_tagged
                        lag_int.save()
                        i2.tagged_vlans = []
                        i2.mode = None
                    i2.save()
                    rvlan = rvlan.union(a_tagged, b_tagged)
            return
        device = self.helper.netbox.dcim.devices.get(name=path[-1])
        cur_vlans = self._get_vlans_for_device(path[-1])
        for interface in self.helper.netbox.dcim.interfaces.filter(device_id=device.id):
            if interface.connected_endpoint_reachable:
                npath = path.copy()
                npath.append(interface.link_peer.device)
                ncables = cables.copy()
                ncables.append(interface.cable)
                self._walk_tree_r(npath, vlans, ncables)

    def populate_gateways(self):
        mgmt_domain = self.helper.config.get('mgmt_domain')

        with click.progressbar(self.vlans, label='Gateways',
                               item_show_func=lambda item: item['Name'] if item else None) as bar:
            for vlandef in bar:
                if not 'Routed-On' in vlandef:
                    continue

                router = self.helper.get_switch(vlandef['Routed-On'])

                vid = int(vlandef['VLAN'])
                svi = self.helper.create_svi(router, vid, 'Gateway for %s' % vlandef['Name'])
                dns = 'vlan%d.%s.%s' % (vid, router.name, mgmt_domain)

                if 'IPv4-Prefix' in vlandef:
                    ipv4_prefix = ipaddress.IPv4Network(vlandef['IPv4-Prefix'])
                    ipv4 = '%s/%d' % (str(ipv4_prefix.network_address + 1), ipv4_prefix.prefixlen)
                    self.helper.set_svi_ip(svi, ipv4, dns)

                if 'IPv6-Prefix' in vlandef:
                    ipv6_prefix = ipaddress.IPv6Network(vlandef['IPv6-Prefix'])
                    ipv6 = '%s/%d' % (ipv6_prefix.network_address + 0xff00, ipv6_prefix.prefixlen)
                    self.helper.set_svi_ip(svi, ipv6, dns)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Netbox with summary data from google sheets.")

    nocsheet = NocSheetHelper()
    nocsheet.add_arguments(parser)

    parser.add_argument("--verbose", action="store_true", help="Print what it's doing")
    parser.add_argument("--populate-all", action="store_true", help="Populate EVERYTHING into Netbox")
    parser.add_argument("--populate-locations", action="store_true", help="Populate locations")
    parser.add_argument("--populate-vlans", action="store_true", help="Populate VLANs and prefixes")
    parser.add_argument("--populate-switches", action="store_true", help="Populate switches")
    parser.add_argument("--populate-switch-ports", action="store_true", help="Populate switch ports")
    parser.add_argument("--populate-links", action="store_true", help="Populate links between switches")
    parser.add_argument("--populate-trunks", action="store_true", help="Assigns trunks to uplinks and downlinks")
    parser.add_argument("--populate-gateways", action="store_true", help="Populate gateways on each VLAN")

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

    if args.populate_all or args.populate_trunks:
        populator.populate_trunks()
        done_something = True

    if args.populate_all or args.populate_gateways:
        populator.populate_gateways()
        done_something = True

    if not done_something:
        print("Nothing to do, try " + sys.argv[0] + " --help")
