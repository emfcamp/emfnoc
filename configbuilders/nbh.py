import shelve
import pprint
import sys
import functools
import re
import pynetbox
from dataclasses import dataclass
import logging
from functools import cached_property
from functools import lru_cache


@dataclass
class NetboxHelper:
    url: str
    token: str
    mgmt_vlan: int
    tenant: int = 1
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

    def __post_init__(self):
        self.netbox = pynetbox.api(self.url, self.token)
        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.INFO)
            ch = logging.StreamHandler()
            self.logger.addHandler(ch)

    def set_interface_vlan(self, device, interface_name, vlan):
        interface = self.netbox.dcim.interfaces.get(
            device_id=device.id, name=interface_name
        )
        interface.mode = "access"
        interface.untagged_vlan = vlan.id
        interface.save()
        self.logger.info(f"{device} -  {interface_name}, to vlan {vlan}")
        return interface

    def create_inband_mgmt(self, device):
        return self.create_svi(device, self.mgmt_vlan)

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
            nb_vlan_interface = netbox.dcim.interfaces.create(
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

    def get_vlan(self, vlan_id, prefix):
        vlan = self.netbox.ipam.vlans.get(vid=vlan_id)
        if not vlan:
            vlan = self.netbox.ipam.vlans.create(
                vid=vlan_id, name=prefix + "-" + vlan_id, tenant=self.tenant
            )
        vlan.tenant = self.tenant
        vlan.save()
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
                tenant=self.tenant,
                site=self.site,
            )
        return device


import yaml

with open("netbox.yml") as netbox_cfg_file:
    try:
        netbox_cfg = yaml.safe_load(netbox_cfg_file)
    except yaml.YAMLError as yamlerror:
        print(yamlerror)
        sys.exit(1)

switches = shelve.open("data/switches")["list"]
port_types = shelve.open("data/port_types")["list"]
helper = NetboxHelper(url=netbox_cfg["url"], token=netbox_cfg["token"], mgmt_vlan=132)

vlan_lut = {}
vlan_order = []
for port_type in port_types:
    vlan_lut[port_type["Port-Type"]] = port_type["VLAN"]
    vlan_order.append(port_type["Port-Type"])

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
                helper.set_interface_vlan(nb_switch, port_prefix + str(k), camper_vlan)
