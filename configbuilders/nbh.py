import logging
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pprint import pprint

import pynetbox

from emfnoc import EmfNoc


@dataclass
class NetboxHelper:
    mgmt_vlan: int
    tenant_id: int
    vlan_group_id: int
    site: int = 1
    device_role: int = 1
    verbose: bool = True

    __vlan_interfaces = {
        "Arista": "Vlan{0}",
        "Aruba": "Vlan-Interface{0}",
        "Cumulus Networks": "Vlan{0}",
        "HPE": "Vlan{0}",
        "Cisco": "Vlan {0}",
        "Juniper": "vlan.{0}",
        "JuniperELS": "irb.{0}",
        "Brocade": "ve {0}",
    }

    def __init__(self, netbox_cfg):
        url = netbox_cfg['url']
        token = netbox_cfg['token']

        self.config = netbox_cfg
        self.mgmt_vlan = netbox_cfg['mgmt_vlan']
        self.verbose = netbox_cfg['verbose'] if 'verbose' in netbox_cfg else False

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

        # Look up the VLAN group
        vlan_group = self.netbox.ipam.vlan_groups.get(slug=netbox_cfg['vlan_group'])
        if vlan_group is None:
            raise ValueError('VLAN Group with slug %s not found in Netbox' % netbox_cfg['vlan_group'])
        self.vlan_group_id = vlan_group.id
        pprint(vlan_group)
        pprint(dir(vlan_group))
        pprint(self.vlan_group_id)
        self.vlan_group_slug = netbox_cfg['vlan_group']

    def set_interface_tagged_vlan(self, device, interface_name, vlans):
        interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=interface_name
        )

        vlan_ids = map(lambda x: x.id, vlans)

        interface.mode = "tagged"
        interface.save()
        interface.tagged_vlans = list(vlan_ids)
        interface.save()
        self.logger.info(f"{device} -  {interface_name}, to vlans {vlans}")
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

    def get_interface_for_device(self, device, interface_name):
        interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=interface_name
        )
        return interface

    def set_interface_vlan(self, device, interface_name, vlan):
        interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=interface_name
        )
        if interface is None:
            print('Interface %s does not exist on device %s' % (interface_name, device.name), file=sys.stderr)
            sys.exit(1)

        interface.mode = "access"
        interface.untagged_vlan = vlan.id
        interface.save()
        self.logger.info(f"{device} -  {interface_name}, to vlan {vlan}")
        return interface

    def create_inband_mgmt(self, device):
        return self.create_svi(device, self.mgmt_vlan)

    def set_inband_mgmt_ip(self, device, ip):
        mgmt_ip = self.netbox.ipam.ip_addresses.get(address=ip)
        if not mgmt_ip:
            mgmt_ip = self.netbox.ipam.ip_addresses.create(address=ip)
        mgmt_interface = self.create_inband_mgmt(device)
        mgmt_ip.assigned_object_type = "dcim.interface"
        mgmt_ip.assigned_object_id = mgmt_interface.id
        mgmt_ip.save()
        device.primary_ip4 = mgmt_ip.id
        device.save()
        self.logger.info(
            f"setting {device} primary ip to {mgmt_ip} on {mgmt_interface} "
        )
        return mgmt_ip

    def create_svi(self, device, vlan_id):
        manufacturer = device.device_type.manufacturer.name
        model = device.device_type.model
        if re.match("EX(2300|3400|4300|4600|9200).*", model):
            manufacturer = "JuniperELS"
        vlan_interface = self.__vlan_interfaces[manufacturer].format(vlan_id)
        vlan = self.get_vlan(vlan_id, "mangement")
        nb_vlan_interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=vlan_interface
        )
        if not nb_vlan_interface:
            nb_vlan_interface = self.netbox.dcim.interfaces.create(
                device=device.id,
                name=vlan_interface,
                type="virtual",
                description="Management",
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

    def create_vlan(self, vlan_id, vlan_name):
        vlan = self.netbox.ipam.vlans.get(vid=vlan_id, group=self.vlan_group_slug)
        if vlan:
            if vlan.tenant.id != self.tenant_id:
                print("Moving vlan %d to correct tenant (%d to %d)" % (vlan_id, vlan.tenant_id, self.tenant_id))
                vlan.tenant_id = self.tenant_id
                vlan.save()
            if vlan.name != vlan_name:
                print("Renaming vlan %d to %s" % (vlan_id, vlan_name))
                vlan.name = vlan_name
                vlan.save()
            return vlan
        else:
            return self.netbox.ipam.vlans.create(vid=vlan_id, name=vlan_name, tenant=self.tenant_id,
                                                 group={'id': self.vlan_group_id})

    def get_vlan(self, vlan_id):
        vlan = self.netbox.ipam.vlans.get(vid=vlan_id, vlan_group=self.vlan_group_id)
        if not vlan:
            raise ValueError('Tried to use VLAN ID %d but does not exist fool' % vlan_id)

        return vlan

    def get_switch(self, hostname, model_id):
        device = self.netbox.dcim.devices.get(name=hostname)
        if device and device.device_type.id != model_id:
            self.logger.warning("WARNING MODEL DOES NOT MATCH, deleting")
            device.delete()
            device = None
        if not device:
            device = self.netbox.dcim.devices.create(
                name=hostname,
                device_type=model_id,
                device_role=self.device_role,
                tenant=self.tenant_id,
                site=self.site,
            )
        return device

    __instance = None

    @staticmethod
    def getInstance():
        if NetboxHelper.__instance is None:
            netbox_cfg = dict(EmfNoc.load_config().items('netbox'))
            NetboxHelper.__instance = NetboxHelper(netbox_cfg)

        return NetboxHelper.__instance
