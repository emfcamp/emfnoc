import logging
import re
from dataclasses import dataclass
from functools import lru_cache

import pynetbox

from emfnoc import EmfNoc


@dataclass
class NetboxHelper:
    mgmt_vlan: int
    tenant_id: int
    vlan_group_id: int
    site_id: int
    verbose: bool = False

    __vlan_interfaces = {
        "Arista": "Vlan{0}",
        "Aruba": "Vlan-Interface{0}",
        "Cumulus Networks": "Vlan{0}",
        "HPE": "Vlan{0}",
        "Cisco": "Vlan {0}",
        "Juniper": "vlan.{0}",
        "JuniperELS": "irb.{0}",
        "Brocade": "ve {0}",
        "MikroTik": "vlan{0}",
    }

    __lag_interfaces = {
        "Arista": "Port-Channel{0}",
        "Cisco": "Port-Channel{0}",
        "Juniper": "ae{0}"
    }

    __lag_interface_offsets = {
        "Arista": 1,
        "Cisco": 1,
        "Juniper": 0
    }

    def __init__(self, netbox_cfg):
        url = netbox_cfg['url']
        token = netbox_cfg['token']

        self.config = netbox_cfg
        self.mgmt_vlan = netbox_cfg['mgmt_vlan']

        self.netbox = pynetbox.api(url, token)
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.INFO)
            ch = logging.StreamHandler()
            self.logger.addHandler(ch)

        # Do a noop to make sure we connected successfully
        self.netbox.dcim.sites.all()

        # Look up the tenant to create everything under
        tenant = self.netbox.tenancy.tenants.get(slug=netbox_cfg['tenant'])
        if tenant is None:
            raise ValueError('Tenant with slug %s not found in Netbox' % netbox_cfg['tenant'])
        self.tenant_id = tenant.id

        # Look up the site
        site = self.netbox.dcim.sites.get(slug=netbox_cfg['site'])
        if site is None:
            raise ValueError('Site with slug %s not found in Netbox' % netbox_cfg['site'])
        self.site_id = site.id

        # Look up the VLAN group
        vlan_group = self.netbox.ipam.vlan_groups.get(slug=netbox_cfg['vlan_group'])
        if vlan_group is None:
            raise ValueError('VLAN Group with slug %s not found in Netbox' % netbox_cfg['vlan_group'])
        self.vlan_group_id = vlan_group.id
        self.vlan_group_slug = netbox_cfg['vlan_group']

    def set_verbose(self, verbose):
        self.verbose = verbose

    def set_interface_trunk(self, interface, vlan_ids):
        # TODO broken
        # vlan_ids = map(lambda x: x.id, vlans)

        interface.mode = 'tagged'
        interface.save()
        interface.untagged_vlan = self.mgmt_vlan
        interface.tagged_vlans = list(vlan_ids)
        interface.save()
        self.logger.info(f"{interface.device.name} -  {interface.name}, to vlans {vlan_ids}")
        return interface

    def link_two_interfaces(self, i1, i2, description):
        c1 = i1.cable
        c2 = i2.cable
        cable = None
        if c1 and c2:
            if i1.link_peer.id != i2.id or i2.link_peer.id != i1.id:
                c1.delete()
                c2.delete()
                c1 = None
                c2 = None
        elif c1:
            c1.delete()
            c1 = None
        elif c2:
            c2.delete()
            c2 = None
        if not c1 and not c2:
            # Connect magic
            cable = self.netbox.dcim.cables.create(termination_a_type="dcim.interface",
                                                   termination_b_type="dcim.interface",
                                                   termination_a_id=i1.id,
                                                   termination_b_id=i2.id,
                                                   label=description)
        self.logger.info(f"linking {i1} with {i2}")
        if c1:
            return c1
        else:
            return cable

    # here the lag_num is 0 for the first interface (which we might pump up to Port-Channel1 for cisco etc)
    def create_lag(self, device, lag_num, members):
        manufacturer = device.device_type.manufacturer.name
        interface_name = self.__lag_interfaces[manufacturer].format(
            self.__lag_interface_offsets[manufacturer] + lag_num
        )

        interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=interface_name
        )
        if interface:
            interface.tenant = self.tenant_id
            interface.type = 'lag'
            interface.save()
        else:
            interface = self.netbox.dcim.interfaces.create(device=device.id, name=interface_name,
                                                           type='lag')

        # Now make sure the interfaces are in this LAG
        # TODO we should probably make sure no OTHER interfaces remain in this lag
        for member in members:
            member.lag = interface.id
            member.save()

        return interface

    def get_interfaces_for_device(self, device):
        interfaces = self.netbox.dcim.interfaces.filter(
            device_id=device.id
        )
        return interfaces

    def _get_interface_for_device(self, device, interface_name):
        interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=interface_name
        )
        if interface is None:
            raise ValueError('Interface %s does not exist on device %s' % (interface_name, device.name))
        return interface

    def get_interface_for_device(self, device, interface_name):
        return self._get_interface_for_device(device, interface_name)

    def set_interface_access(self, device, interface_name, vlan):
        interface = self._get_interface_for_device(device, interface_name)

        interface.mode = 'access'
        interface.untagged_vlan = vlan.id
        interface.description = vlan.name + ' port'
        interface.save()
        self.logger.info(f"{device} - {interface_name}, to vlan {vlan}")
        return interface

    # Return all VLAN IDs that are present on access ports on this switch or are on trunk ports
    # EXCLUDING the passed in interface
    def get_vlans_for_switch(self, device, exclude_interface=None):
        vlan_ids = set()
        interfaces = self.get_interfaces_for_device(device)
        for interface in interfaces:
            if interface == exclude_interface:
                print("Excluding %s" % exclude_interface.name)
                continue
            if interface.mode == 'access' and interface.untagged_vlan:
                vlan_ids.add(interface.untagged_vlan.id)
                print("Access %d" % interface.untagged_vlan.id)
            if interface.mode == 'tagged':
                if interface.untagged_vlan:
                    vlan_ids.add(interface.untagged_vlan.id)
                    print("Trunk untagged %d" % interface.untagged_vlan.id)
                if interface.tagged_vlans:
                    for tagged_vlan in interface.tagged_vlans:
                        vlan_ids.add(tagged_vlan.id)
                        print("Trunk tagged %d" % tagged_vlan.id)

        print('Device %s requires VLANs %s' % (device.name, str(vlan_ids)))
        return list(vlan_ids)

    def create_inband_mgmt(self, device):
        return self.create_svi(device, self.mgmt_vlan, 'Management')

    def set_inband_mgmt_ip(self, device, ip, dns, dhcp_mac=None):
        mgmt_interface = self.create_inband_mgmt(device)
        mgmt_ip = self.set_svi_ip(mgmt_interface, ip, dns, dhcp_mac)
        device.primary_ip4 = mgmt_ip.id
        device.save()
        self.logger.info(
            f"setting {device} primary ip to {mgmt_ip} on {mgmt_interface} "
        )
        return mgmt_ip

    def set_svi_ip(self, interface, ip, dns, dhcp_mac=None):
        mgmt_ip = self.netbox.ipam.ip_addresses.get(address=ip)
        if not mgmt_ip:
            mgmt_ip = self.netbox.ipam.ip_addresses.create(address=ip, tenant=self.tenant_id)
        mgmt_ip.assigned_object_type = "dcim.interface"
        mgmt_ip.assigned_object_id = interface.id
        mgmt_ip.tenant = self.tenant_id
        mgmt_ip.dns_name = dns
        mgmt_ip.custom_fields['dhcp_mac'] = dhcp_mac
        mgmt_ip.save()
        return mgmt_ip

    def create_svi(self, device, vlan_id, interface_description):
        manufacturer = device.device_type.manufacturer.name
        model = device.device_type.model
        if re.match("EX(2300|3400|4300|4600|9200).*", model):
            manufacturer = "JuniperELS"
        vlan_interface = self.__vlan_interfaces[manufacturer].format(vlan_id)
        vlan = self.get_vlan(vlan_id)
        nb_vlan_interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=vlan_interface
        )
        if nb_vlan_interface:
            nb_vlan_interface.type = 'virtual'
            nb_vlan_interface.description = interface_description
            nb_vlan_interface.mode = 'access'
            nb_vlan_interface.untagged_vlan = vlan
            nb_vlan_interface.save()
        else:
            nb_vlan_interface = self.netbox.dcim.interfaces.create(
                device=device.id,
                name=vlan_interface,
                type="virtual",
                description=interface_description,
                mode="access",
                untagged_vlan=vlan.id,
            )
        self.logger.info(f"{device} -  {vlan_interface}")
        return nb_vlan_interface

    @staticmethod
    @lru_cache(maxsize=100)
    def _get_device_type(netbox, model_type):
        device_type = netbox.dcim.device_types.get(model=model_type)
        if device_type or (
                device_type := netbox.dcim.device_types.get(part_number=model_type)
        ):
            return device_type
        return None

    def get_device_type(self, model_type):
        return NetboxHelper._get_device_type(self.netbox, model_type)

    def get_sum_copper_ports(self, model_type):
        return NetboxHelper._get_sum_copper_ports(self.netbox, model_type, self.logger)

    @staticmethod
    @lru_cache(maxsize=100)
    def _get_sum_copper_ports(netbox, model_type, logger):
        copper_ports = {
            "100base-tx",
            "1000base-t",
            "2.5gbase-t",
            "5gbase-t",
            "10gbase-t",
        }
        sum_copper = None
        if device_type := NetboxHelper._get_device_type(netbox, model_type):
            sum_copper = -1
            for interface in netbox.dcim.interface_templates.filter(
                    devicetype_id=device_type.id
            ):
                if interface.type.value in copper_ports:
                    sum_copper += 1
        logger.info(str(device_type) + " " + str(sum_copper))
        return sum_copper

    def create_vlan(self, vlan_id, vlan_name, description):
        vlan = self.netbox.ipam.vlans.get(vid=vlan_id, group=self.vlan_group_slug)
        if vlan:
            # We can just make these changes and save(), since that already does nothing if nothing has changed
            vlan.tenant = self.tenant_id
            vlan.name = vlan_name
            vlan.description = description
            vlan.save()
            return vlan
        else:
            return self.netbox.ipam.vlans.create(vid=vlan_id, name=vlan_name, description=description,
                                                 tenant=self.tenant_id, group={'id': self.vlan_group_id})

    def get_vlan(self, vlan_id):  # TODO cache
        vlan = self.netbox.ipam.vlans.get(vid=vlan_id, vlan_group=self.vlan_group_id)
        if not vlan:
            raise ValueError('Tried to use VLAN ID %d but does not exist fool' % vlan_id)

        return vlan

    def create_prefix(self, prefix_str: str, description: str, vlan, dhcp: bool, dhcp_reserved: int):
        prefix = self.netbox.ipam.prefixes.get(prefix=prefix_str)
        if prefix:
            # We can just make these changes and save(), since that already does nothing if nothing has changed
            prefix.tenant = self.tenant_id
            prefix.site = self.site_id
            prefix.description = description
            prefix.vlan = vlan
            prefix.dhcp = dhcp
            prefix.custom_fields['dhcp'] = dhcp
            prefix.custom_fields['dhcp_reserved'] = dhcp_reserved
            prefix.save()
            return prefix
        else:
            return self.netbox.ipam.prefixes.create(prefix=prefix_str, tenant=self.tenant_id, site=self.site_id,
                                                    vlan=vlan.id, description=description,
                                                    custom_fields={'dhcp': dhcp, 'dhcp_reserved': dhcp_reserved})

    @staticmethod
    @lru_cache(maxsize=500)
    def _get_device(netbox, hostname):
        device = netbox.dcim.devices.get(name=hostname)
        if device:
            return device
        return None

    def get_switch(self, hostname):
        device = NetboxHelper._get_device(self.netbox, hostname)
        if not device:
            raise ValueError('Tried to use device with hostname %s but does not exist fool' % hostname)
        return device

    def create_switch(self, hostname, model_id, device_role_id, location_name, asset_tag, serial):
        device = NetboxHelper._get_device(self.netbox, hostname)
        location = self.get_location(location_name)

        if device and device.device_type.id != model_id:
            self.logger.warning("WARNING MODEL DOES NOT MATCH, deleting")
            device.delete()
            device = None
            NetboxHelper._get_device.cache_clear()

        if device:
            device.tenant = self.tenant_id
            device.site = self.site_id
            device.device_role = device_role_id
            device.location = location
            device.serial = serial
            device.asset_tag = asset_tag
            if device.updates():
                if self.verbose:
                    print("Device %s has changed, saving" % hostname)
                device.save()  # TODO should we be checking return value?
                NetboxHelper._get_device.cache_clear()
        else:
            device = self.netbox.dcim.devices.create(
                name=hostname,
                device_type=model_id,
                device_role=device_role_id,
                tenant=self.tenant_id,
                site=self.site_id,
                location={'id': location.id},
                serial=serial,
                asset_tag=asset_tag
            )
            NetboxHelper._get_device.cache_clear()
        return device

    @staticmethod
    @lru_cache(maxsize=100)
    def _get_location(netbox, name):
        return netbox.dcim.locations.get(name=name)

    def get_location(self, name):
        location = NetboxHelper._get_location(self.netbox, name)
        if not location:
            raise ValueError('Tried to use location %s but does not exist fool' % name)
        return location

    def create_location(self, name):
        location = NetboxHelper._get_location(self.netbox, name)
        if location:
            location.slug = name.lower()
            location.tenant = self.tenant_id
            location.site = self.site_id
            if location.updates():
                if self.verbose:
                    print("Location %s has changed, saving" % name)
                location.save()  # TODO should we be checking return value?
                NetboxHelper._get_location.cache_clear()
        else:
            location = self.netbox.dcim.locations.create(
                name=name,
                slug=name.lower(),
                tenant=self.tenant_id,
                site=self.site_id,
            )
            NetboxHelper._get_location.cache_clear()
        return location

    __instance = None

    @staticmethod
    def getInstance():
        if NetboxHelper.__instance is None:
            netbox_cfg = dict(EmfNoc.load_config().items('netbox'))
            NetboxHelper.__instance = NetboxHelper(netbox_cfg)

        return NetboxHelper.__instance
