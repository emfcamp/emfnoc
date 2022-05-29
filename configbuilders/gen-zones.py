#!/usr/bin/env python

#
# Generate EMF zone files from Netbox
#

# TODO some way of making codenames deterministic based on actual IP if we change prefixes during the event
import argparse
import ipaddress
import os
import sys
import time
from configparser import ConfigParser
from typing import Dict

import dns.rdata
import dns.rdataclass
import dns.rdtypes
import dns.rdtypes.ANY
import dns.rdtypes.ANY.NS
import dns.rdtypes.ANY.PTR
import dns.rdtypes.IN
import dns.rdtypes.IN.A
import dns.rdtypes.IN.AAAA
import dns.zone
import yaml
from dns import reversename
from dns.name import Name

from emfnoc import EmfNoc
from nbh import NetboxHelper


class ZonesGenerator:
    SOA_NS = 'ns1.emfcamp.org'
    SOA_ADMIN = 'noc.emfcamp.org'
    SOA_REFRESH = 3600
    SOA_RETRY = 120
    SOA_EXPIRE = 4 * 60 * 60

    TTL = 1 * 60 * 60  # 1 hour

    FWD_DOMAINS = ['gchq.org.uk.', 'emf.camp.']

    SIGNED_ZONES = ['emf.camp']

    NS_LIST = ['ns1.emfcamp.org.', 'auth1.ns.sargasso.net.', 'auth2.ns.sargasso.net.', 'auth3.ns.sargasso.net.']

    NS_LIST_HACK_EMF_CAMP = ['ns1.emfcamp.org.', 'A.AUTHNS.BITFOLK.COM.', 'B.AUTHNS.BITFOLK.COM.',
                             'C.AUTHNS.BITFOLK.COM.']

    # All zones including reverse
    zones: Dict[str, dns.zone.Zone] = {}
    # Reverse only
    reverse_zones: Dict[ipaddress._BaseNetwork, dns.zone.Zone]

    codenames: list[str] = []
    codenamepos: int = 0

    def __init__(self, config: ConfigParser, helper: NetboxHelper):
        self.config = config
        self.domain_campers = config['dhcpd']['domain_campers']
        self.domain_orga = config['dhcpd']['domain_orga']

        self.helper = helper

        with open('dns-codenames.txt', 'r') as file:
            for line in file:
                line = line.strip().replace(' ', '')
                if line:
                    self.codenames.append(line)

    def _get_rev_zone_for_ipv4(self, prefix: ipaddress.IPv4Network) -> dns.name.Name:
        return reversename.from_address(str(prefix.network_address)).parent()

    def _get_rev_zone_for_ipv6(self, prefix: ipaddress.IPv6Network) -> dns.name.Name:
        # Find the shortest prefix that covers this and is a multiple of 4 and return the .ip6.arpa reverse zone
        parts: list[str] = []
        length = prefix.prefixlen
        pos: int = 0
        all_bytes = prefix.network_address.packed
        while length > 0:
            parts.append(format((all_bytes[pos] >> 4) & 0xf, 'x'))
            if length > 4:
                parts.append(format(all_bytes[pos] & 0xf, 'x'))
            length -= 8
            pos += 1

        return dns.name.from_text('.'.join(reversed(parts)), origin=reversename.ipv6_reverse_domain)

    def _add_soa_and_ns(self, zone: dns.zone.Zone):
        # Add SOA
        serial = int(time.time())
        soa_rdataset = zone.find_rdataset('@', dns.rdatatype.SOA, create=True)
        soa_rdataset.add(dns.rdtypes.ANY.SOA.SOA(dns.rdataclass.IN, dns.rdatatype.SOA, self.SOA_NS, self.SOA_ADMIN,
                                                 serial, self.SOA_REFRESH, self.SOA_RETRY, self.SOA_EXPIRE, self.TTL),
                         self.TTL)

        ns_rdataset = zone.find_rdataset('@', dns.rdatatype.NS, create=True)

        for ns in self.NS_LIST_HACK_EMF_CAMP if zone.origin.to_text(
                omit_final_dot=True) == 'emf.camp' else self.NS_LIST:
            ns_rdataset.add(dns.rdtypes.ANY.NS.NS(dns.rdataclass.IN, dns.rdatatype.NS, ns), self.TTL)

    def generate_zones(self):
        self.reverse_zones = {}
        aggregates = self.helper.netbox.ipam.aggregates.all()
        for aggregate in aggregates:
            supernet: ipaddress._BaseNetwork = ipaddress.ip_network(aggregate)
            if supernet.version == 4:
                for subnet in supernet.subnets(new_prefix=24):
                    rev_zone_name = str(self._get_rev_zone_for_ipv4(subnet))
                    zone = dns.zone.Zone(rev_zone_name)
                    self._add_soa_and_ns(zone)
                    self.zones[rev_zone_name] = zone
                    self.reverse_zones[subnet] = zone
            elif supernet.version == 6:
                rev_zone_name = str(self._get_rev_zone_for_ipv6(supernet))
                zone = dns.zone.Zone(rev_zone_name)
                self._add_soa_and_ns(zone)
                self.zones[rev_zone_name] = zone
                self.reverse_zones[supernet] = zone

        for zone_name in self.FWD_DOMAINS:
            zone = dns.zone.Zone(zone_name)
            self._add_soa_and_ns(zone)
            self.zones[zone_name] = zone

        addresses = self.helper.netbox.ipam.ip_addresses.all()
        for nb_address in addresses:
            dns_name = nb_address.dns_name
            address: ipaddress._BaseAddress = ipaddress.ip_interface(nb_address.address).ip
            self._add_host_records(address, dns_name)

        self._add_dhcp_hostnames()
        self._add_dns_extras()

    def _add_host_records(self, address: ipaddress._BaseAddress, dns_name: str):
        name: Name = dns.name.from_text(dns_name)
        forward_zone = None
        for zone in self.zones.values():
            if name.is_subdomain(zone.origin):
                forward_zone = zone
        if forward_zone:
            record_type = dns.rdatatype.A if address.version == 4 else dns.rdatatype.AAAA
            forward_rdataset = forward_zone.find_rdataset(name, record_type, create=True)

            if address.version == 4:
                forward_rdataset.add(dns.rdtypes.IN.A.A(dns.rdataclass.IN, dns.rdatatype.A, str(address)), self.TTL)
            else:
                forward_rdataset.add(dns.rdtypes.IN.AAAA.AAAA(dns.rdataclass.IN, dns.rdatatype.AAAA, str(address)),
                                     self.TTL)
        reverse_zone: dns.zone.Zone = None
        for supernet, zone in self.reverse_zones.items():
            if address in supernet:
                reverse_zone = zone
                break
        if reverse_zone:
            rev_name = reversename.from_address(str(address))

            ptr_rdataset = reverse_zone.find_rdataset(rev_name, dns.rdatatype.PTR, create=True)
            ptr_rdataset.add(dns.rdtypes.ANY.PTR.PTR(dns.rdataclass.IN, dns.rdatatype.PTR, dns_name),
                             self.TTL)

    def _add_dhcp_hostnames(self):
        prefixes = helper.netbox.ipam.prefixes.filter(cf_dhcp=True, family=4)

        for prefix in prefixes:
            reserved = prefix.dhcp_reserved if 'dhcp_reserved' in prefix else 10
            network = ipaddress.IPv4Network(prefix.prefix)
            pool_start = network.network_address + 1 + reserved
            pool_end = network.broadcast_address - 1

            address = pool_start
            while address <= pool_end:
                domain = self.domain_campers if 'Camper-' in prefix.description else self.domain_orga

                fqdn = '%s.%s' % (self._pretty_hostname_ipv4(address, domain), domain)
                # TODO this needs to only overwrite the PTR if it doesn't exist.
                # e.g. if we assign address 63 on video vlan via netbox, that record should take priority
                # even though the address is part of the dhcp range.
                # Note: It should still "use up" that codename, so that things following it are not automatically
                # renumbered!
                self._add_host_records(address, fqdn)
                address += 1

    def _pretty_hostname_ipv4(self, address: ipaddress.IPv4Address, domain: str) -> str:
        if domain == self.domain_orga:
            octets = address.packed
            return 'host-%s-%s-%s-%s' % (str(octets[0]), str(octets[1]), str(octets[2]), str(octets[3]))
        else:
            if (self.codenamepos % len(self.codenames) == self.codenamepos / len(self.codenames)):
                self.codenamepos += 1
            code1 = self.codenamepos // len(self.codenames)
            code2 = self.codenamepos % len(self.codenames)
            if code1 >= len(self.codenames):
                print("RUN OUT OF self.codenames AT POS %d" % self.codenamepos, file=sys.stderr)
                exit(1)

            codename1 = self.codenames[code1]
            codename2 = self.codenames[code2]
            self.codenamepos += 1
            return codename1 + "-" + codename2

    def _add_dns_extras(self):
        # Add extras
        with open('dns-extra.yaml', 'r') as f:
            dns_extra = yaml.safe_load(f)
        for zone_name, records in dns_extra.items():
            zone = self.zones[zone_name + '.']
            for record in records:
                rrsets = dns.zonefile.read_rrsets(record, rdclass=None, default_ttl=self.TTL, origin=zone.origin)
                for rrset in rrsets:
                    zone.replace_rdataset(rrset.name, rrset)

    def _is_zone_signed(self, zone: dns.zone.Zone) -> bool:
        zone_name = zone.origin.to_text(omit_final_dot=True)
        for signed_zone_name in self.SIGNED_ZONES:
            if zone_name.endswith(signed_zone_name):
                return True
        return False

    # def live_zone_file(self, zone):
    #     if self.is_zone_signed(zone):
    #         return "/etc/bind/signed-zones/%s/zone.db" % zone
    #     else:
    #         return "/etc/bind/master/%s" % zone

    def _write_zone(self, zone: dns.zone.Zone, tempfile: str):
        if os.path.exists(tempfile) == True:
            os.remove(tempfile)
        with open(tempfile, 'w') as f:
            f.write(";\n")
            f.write("; zone file built by gen-zones.py from EMF NOC Google Spreadsheet\n")
            f.write("; %s\n" % (zone.origin))
            f.write(";\n")
            f.write("; DO NOT EDIT THIS FILE!\n")
            f.write("; This file is automatically generated and changes will be lost next time it is built.\n")
            f.write(";\n")

            zone.to_file(f, sorted=True)

            f.write(";\n")
            f.write("; DO NOT EDIT THIS FILE!\n")
            f.write("; This file is automatically generated and changes will be lost next time it is built.\n")

    def _get_temp_file(self, zone: dns.zone.Zone) -> str:
        zone_name = zone.origin.to_text(omit_final_dot=True)
        if self._is_zone_signed(zone):
            return 'out/signed-zones/%s' % (zone_name)
        else:
            return 'out/zones/%s' % (zone_name)

    def output_zones(self):
        for zone_name, zone in self.zones.items():
            tempfile = self._get_temp_file(zone)
            self._write_zone(zone, tempfile)

    def _check_zone(self, zone: str, file: str) -> bool:
        checkcmd = '/usr/sbin/named-checkzone %s %s' % (zone, file)
        checkresult = os.popen(checkcmd).read()
        return checkresult.endswith("OK\n")

    def verify_zones(self):
        if os.name == 'nt':
            print('Unable to verify zones under Windows - skipping')
            return

        ok = not_ok = 0
        for zone_name, zone in self.zones.items():
            tempfile = self._get_temp_file(zone)
            if self._check_zone(zone_name, tempfile):
                ok += 1
            else:
                print('VALIDATION FAILED: %s for %s' % (tempfile, zone_name))
                not_ok += 1

        print('Zone validation: %d ok, %d not ok' % (ok, not_ok))

        if not_ok > 0:
            print('Validation failed, aborting', file=sys.stderr)
            sys.exit(1)

    def finalise_zones(self):
        for zone_name, zone in self.zones.items():
            if self._is_zone_signed(zone):
                tempfile = self._get_temp_file(zone)
                with open(tempfile, 'a') as f:
                    f.write("\n$INCLUDE dnskey.db\n")


if __name__ == "__main__":
    helper = NetboxHelper.getInstance()

    parser = argparse.ArgumentParser(description='Generate DNS zone files.')

    args = parser.parse_args()

    config = EmfNoc.load_config()

    if not os.path.exists('out'):
        os.mkdir('out')
    if not os.path.exists('out/zones'):
        os.mkdir('out/zones')
    if not os.path.exists('out/signed-zones'):
        os.mkdir('out/signed-zones')

    zonegen = ZonesGenerator(config, helper)

    print("Generating zones")

    zonegen.generate_zones()

    print("Outputting zones")

    zonegen.output_zones()

    print("Verifying zones")

    zonegen.verify_zones()
    zonegen.finalise_zones()
