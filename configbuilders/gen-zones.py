#!/usr/bin/env python

#
# Generate EMF zone files from Netbox
#

# TODO some way of making codenames deterministic based on actual IP if we change prefixes during the event
import argparse
import getpass
import ipaddress
import os
import re
import shutil
import sys
import time
from ipaddress import _BaseAddress
from pprint import pprint
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
    zones: Dict[str, dns.zone.Zone] = {}

    SOA_NS = 'ns1.emfcamp.org'
    SOA_ADMIN = 'noc.emfcamp.org'
    SOA_REFRESH = 3600
    SOA_RETRY = 120
    SOA_EXPIRE = 1 * 60 * 60

    TTL = 30 * 60

    FWD_DOMAINS = ['gchq.org.uk.', 'emf.camp.']

    NS_LIST = ['ns1.emfcamp.org.', 'auth1.ns.sargasso.net.', 'auth2.ns.sargasso.net.', 'auth3.ns.sargasso.net.']

    NS_LIST_HACK_EMF_CAMP = ['ns1.emfcamp.org.', 'A.AUTHNS.BITFOLK.COM.', 'B.AUTHNS.BITFOLK.COM.',
                             'C.AUTHNS.BITFOLK.COM.']

    codenames: list[str] = []
    codenamepos: int = 0

    reverse_zones: dict[ipaddress._BaseNetwork, dns.zone.Zone]

    def __init__(self, config, helper):

        self.config = config
        self.domain_campers = config['dhcpd']['domain_campers']
        self.domain_orga = config['dhcpd']['domain_orga']

        self.helper = helper

        with open('dns-codenames.txt', 'r') as file:
            for line in file:
                line = line.strip().replace(' ', '')
                if line:
                    self.codenames.append(line)

    def _get_rev_zone(self, address):
        return reversename.from_address(str(address)).parent()

    def _add_soa_and_ns(self, zone):
        # Add SOA
        serial = 123  # TODO
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
            supernet = ipaddress.ip_network(aggregate)
            if supernet.version == 4:
                for subnet in supernet.subnets(new_prefix=24):
                    rev_zone_name = str(self._get_rev_zone(subnet.network_address))
                    zone = dns.zone.Zone(rev_zone_name)
                    self._add_soa_and_ns(zone)
                    self.zones[rev_zone_name] = zone
                    self.reverse_zones[subnet] = zone
            elif supernet.version == 6:
                rev_zone_name = str(self.rev_zone_for_ipv6_prefix(supernet))
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
            address: _BaseAddress = ipaddress.ip_interface(nb_address.address).ip
            self._add_host_records(address, dns_name)

        self._add_dhcp_hostnames()
        self._add_dns_extras()

    def _add_host_records(self, address: _BaseAddress, dns_name: str):
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

                fqdn = '%s.%s' % (self._pretty_hostname(address, domain), domain)
                # TODO this needs to only overwrite the PTR if it doesn't exist.
                # e.g. if we assign address 63 on video vlan via netbox, that record should take priority
                # even though the address is part of the dhcp range.
                # Note: It should still "use up" that codename, so that things following it are not automatically
                # renumbered!
                self._add_host_records(address, fqdn)
                address += 1

    def _pretty_hostname(self, address, domain):
        if domain == "emf.camp":
            octets = address.packed
            return "host-%s-%s-%s-%s" % (str(octets[0]), str(octets[1]), str(octets[2]), str(octets[3]))
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

    def rev_zone_for_ipv6_prefix(self, prefix):
        # Find the shortest prefix that covers this and is a multiple of 4 and return the .ip6.arpa reverse zone
        parts: list[str] = []
        length = prefix.prefixlen
        pos = 0
        all_bytes = prefix.network_address.packed
        while length > 0:
            parts.append(format((all_bytes[pos] >> 4) & 0xf, 'x'))
            if length > 4:
                parts.append(format(all_bytes[pos] & 0xf, 'x'))
            length -= 8
            pos += 1

        return dns.name.from_text('.'.join(reversed(parts)), origin=reversename.ipv6_reverse_domain)

    def is_zone_signed(self, zone):
        if os.path.isdir("/etc/bind/signed-zones/%s" % zone):
            return True
        else:
            return False

    def live_zone_file(self, zone):
        #  /etc/bind/signed-zones/emf.camp
        if self.is_zone_signed(zone):
            return "/etc/bind/signed-zones/%s/zone.db" % zone
        else:
            return "/etc/bind/master/%s" % zone

    def _write_zone(self, zone, tempfile):
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
            f.close()
            return

    def _check_zone(self, zone, file):
        checkcmd = '/usr/sbin/named-checkzone %s %s' % (zone, file)
        checkresult = os.popen(checkcmd).read()
        return checkresult.endswith("OK\n")

    def _get_temp_file(self, zone):
        zone_name = zone.origin.to_text(omit_final_dot=True)
        return 'out/zones/%s' % (zone_name)

    def output_zones(self):

        for zone_name, zone in self.zones.items():
            tempfile = self._get_temp_file(zone)
            # zoneserial = get_serial(zonename)
            # print("* %s" % (zone_name))
            self._write_zone(zone, tempfile)

    def verify_zones(self):
        if os.name == 'nt':
            print("Unable to verify zones under Windows - skipping")
            return

        ok = not_ok = 0
        for zone_name, zone in zones.items():
            tempfile = self._get_temp_file(zone)
            if self._check_zone(zone_name, tempfile):
                ok += 1
            else:
                print("VALIDATION FAILED: %s for %s" % (tempfile, zone_name))
                not_ok += 1

        print("Zone validation: %d ok, %d not ok" % (ok, not_ok))

        if not_ok > 0:
            print("Validation failed, aborting")
            sys.exit(1)


if __name__ == "__main__":
    helper = NetboxHelper.getInstance()

    parser = argparse.ArgumentParser(description='Generate DNS zone files.')

    args = parser.parse_args()

    config = EmfNoc.load_config()

    if not os.path.exists('out'):
        os.mkdir('out')
    if not os.path.exists('out/zones'):
        os.mkdir('out/zones')

    zonegen = ZonesGenerator(config, helper)

    print("Generating zones")

    zonegen.generate_zones()

    print("Outputting zones")

    zonegen.output_zones()

    print("Verifying zones")

    zonegen.verify_zones()

    sys.exit(0)

    if args.deploy:
        print("Signing...")
        # tell zkt-signer that the zones have changed
        os.system("zkt-signer -v -r")

        print("zones deployed: %d successfully, %d failed" % (success, failed))

sys.exit(0)


def makezonelive(domain, file):
    if getpass.getuser() != "root":
        print("  - Cannot put zone live, must be run as root")
        return False
    livefile = live_zone_file(domain)
    shutil.copyfile(file, livefile)

    ret = True

    if is_zone_signed(domain):
        # append to end of file
        with open(livefile, "a") as f:
            f.write("\n$INCLUDE dnskey.db\n")
        return True
    else:
        ret = reloadzone(domain)

    return ret


def reloadzone(domain):
    # zkt pokes bind to reload the zone, so don't do it ourselves.
    if not is_zone_signed(domain):
        reloadcmd = "rndc reload %s" % (domain)
        process = os.popen(reloadcmd)
        reloadresult = process.read()
        ret = process.close()
        # should process ret a bit?
        if ret != None:
            print("reload failed? %s" % (str(ret),))
            print(reloadresult)
            return False
        else:
            return True
    else:
        return True


parser = argparse.ArgumentParser(description='Generate cisco IOS config files from gdocs.')

parser.add_argument('--deploy', action='store_true',
                    help='deploy zone files after generating')

parser.add_argument('--diff', action='store_true',
                    help='diff zone files against live versions after generating')

args = parser.parse_args()

spreadsheet = config.get('gdata', 'noc_combined')

spr_client = login("emfcamp DNS zone generator", config)


def get_serial(zonename):
    realzone = live_zone_file(zonename)
    if not os.path.exists(realzone):
        print("Can't open " + realzone + ", using default serial number")
        return int(time.time())
    zfh = open(realzone, "r")
    got = False

    zoneserial = None
    for line in zfh:
        if got:
            line = line.strip()
            line = line.split()[0]
            zoneserial = int(line)
            zoneserial += 1
            got = False
            break
        if re.search("SOA\s+ns1\.emfcamp\.org", line):
            got = True
    zfh.close()

    if zoneserial == None:
        print("Couldn't find serial for " + zonename + " - using default")
        return int(time.time())
    return zoneserial


if args.deploy and args.diff:
    print("only one of --deploy and --diff can be specified")
    raise SystemExit
