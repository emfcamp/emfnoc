#!/usr/bin/env python

#
# Generate EMF zone files from Netbox
#

# TODO ipv6 reverse
# TODO auto codenames for dhcp sections of dhcp-enabled prefixes
import argparse
import getpass
import ipaddress
import os
import re
import shutil
import sys
import time
from pprint import pprint
from typing import Dict, Set

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

from emfnoc import EmfNoc
from nbh import NetboxHelper

SOA_NS = 'ns1.emfcamp.org'
SOA_ADMIN = 'noc.emfcamp.org'
SOA_REFRESH = 3600
SOA_RETRY = 120
SOA_EXPIRE = 1 * 60 * 60

TTL = 30 * 60

FWD_DOMAINS = ['gchq.org.uk.', 'emf.camp.']

NS_LIST = ['ns1.emfcamp.org.', 'auth1.ns.sargasso.net.', 'auth2.ns.sargasso.net.', 'auth3.ns.sargasso.net.']

NS_LIST_HACK_EMF_CAMP = ['ns1.emfcamp.org.', 'A.AUTHNS.BITFOLK.COM.', 'B.AUTHNS.BITFOLK.COM.', 'C.AUTHNS.BITFOLK.COM.']


def get_rev_zone(address):
    return str(reversename.from_address(str(address)).parent())


def add_soa_and_ns(zone):
    # Add SOA
    serial = 123  # TODO
    soa_rdataset = zone.find_rdataset('@', dns.rdatatype.SOA, create=True)
    soa_rdataset.add(dns.rdtypes.ANY.SOA.SOA(dns.rdataclass.IN, dns.rdatatype.SOA, SOA_NS, SOA_ADMIN,
                                             serial, SOA_REFRESH, SOA_RETRY, SOA_EXPIRE, TTL), TTL)

    ns_rdataset = zone.find_rdataset('@', dns.rdatatype.NS, create=True)

    for ns in NS_LIST_HACK_EMF_CAMP if zone.origin.to_text(omit_final_dot=True) == 'emf.camp' else NS_LIST:
        ns_rdataset.add(dns.rdtypes.ANY.NS.NS(dns.rdataclass.IN, dns.rdatatype.NS, ns), TTL)


def generate_zones():
    # global zones, aggregates, subnet, zone, name, address
    zones: Dict[str, dns.zone.Zone] = {}
    reverse_supernets: Set[ipaddress._BaseNetwork] = set()
    aggregates = helper.netbox.ipam.aggregates.all()
    for aggregate in aggregates:
        supernet = ipaddress.ip_network(aggregate)
        reverse_supernets.add(supernet)
        if supernet.version == 4:
            for subnet in supernet.subnets(new_prefix=24):
                rev_zone_name = get_rev_zone(subnet.network_address)
                zone = dns.zone.Zone(rev_zone_name)
                add_soa_and_ns(zone)
                zones[rev_zone_name] = zone
        elif supernet.version == 6:
            # rev_zone = reversename.from_address(str(subnet.network_address)).parent()
            # TODO get a zone name of the length of this agggregate (mod 4 bits)
            pass
    for zone_name in FWD_DOMAINS:
        zone = dns.zone.Zone(zone_name)
        add_soa_and_ns(zone)
        zones[zone_name] = zone
    addresses = helper.netbox.ipam.ip_addresses.all()
    for nb_address in addresses:
        name = dns.name.from_text(nb_address.dns_name)
        address = ipaddress.ip_address(nb_address.address.split('/')[0])

        forward_parent = None
        for zone in zones.values():
            if name.is_subdomain(zone.origin):
                forward_parent = zone

        if forward_parent:
            record_type = dns.rdatatype.A if address.version == 4 else dns.rdatatype.AAAA
            forward_rdataset = forward_parent.find_rdataset(name, record_type, create=True)

            if address.version == 4:
                forward_rdataset.add(dns.rdtypes.IN.A.A(dns.rdataclass.IN, dns.rdatatype.A, str(address)), TTL)
            else:
                forward_rdataset.add(dns.rdtypes.IN.AAAA.AAAA(dns.rdataclass.IN, dns.rdatatype.AAAA, str(address)), TTL)

        do_reverse: bool = False
        for supernet in reverse_supernets:
            if address in supernet:
                do_reverse = True
                break

        if do_reverse:
            if address.version == 4:
                # zones[get_fwd_zone(address)] = dns.rdtypes.IN.A()
                # zones[get_rev_zone(address)][address.]
                rev_name = reversename.from_address(str(address))

                ptr_rdataset = zones[get_rev_zone(address)].find_rdataset(rev_name, dns.rdatatype.PTR, create=True)

                # ns_rdataset.add(dns.rdtypes.ANY.NS.NS(dns.rdataclass.IN, dns.rdatatype.NS, ns), TTL)
                ptr_rdataset.add(dns.rdtypes.ANY.PTR.PTR(dns.rdataclass.IN, dns.rdatatype.PTR, nb_address.dns_name),
                                 TTL)
                # zones[get_rev_zone(address)][rev_name] = value

    # Add extras
    with open('dns-extra.yaml', 'r') as f:
        dns_extra = yaml.safe_load(f)
    for zone_name, records in dns_extra.items():
        zone = zones[zone_name + '.']
        for record in records:
            rrsets = dns.zonefile.read_rrsets(record, rdclass=None, default_ttl=TTL, origin=zone.origin)
            for rrset in rrsets:
                zone.replace_rdataset(rrset.name, rrset)

    return zones


def is_zone_signed(zone):
    if os.path.isdir("/etc/bind/signed-zones/%s" % zone):
        return True
    else:
        return False


def live_zone_file(zone):
    #  /etc/bind/signed-zones/emf.camp
    if is_zone_signed(zone):
        return "/etc/bind/signed-zones/%s/zone.db" % zone
    else:
        return "/etc/bind/master/%s" % zone


def write_zone(zone, tempfile):
    if os.path.exists(tempfile) == True:
        os.remove(tempfile)
    with open(tempfile, 'w') as f:
        f.write(";\n")
        f.write("; zone file built by gen-zones.py from EMF NOC Google Spreadsheet\n")
        f.write("; %s\n" % (zone.origin))
        f.write(";\n")
        f.write("; DO NOT EDIT THIS FILE!\n")
        f.write("; This file is automatically generated and changes will be lost next time it is built.\n")
        # f.write("      IN      NS  ns1.emfcamp.org.\n")
        # if domainname == "emf.camp":
        #     f.write("      IN      NS  A.AUTHNS.BITFOLK.COM.\n")
        #     f.write("      IN      NS  B.AUTHNS.BITFOLK.COM.\n")
        #     f.write("      IN      NS  C.AUTHNS.BITFOLK.COM.\n")
        # else:
        #     f.write("      IN      NS  auth1.ns.sargasso.net.\n")
        #     f.write("      IN      NS  auth2.ns.sargasso.net.\n")
        #     f.write("      IN      NS  auth3.ns.sargasso.net.\n")
        f.write(";\n")

        zone.to_file(f, sorted=True)

        f.write(";\n")
        f.write("; DO NOT EDIT THIS FILE!\n")
        f.write("; This file is automatically generated and changes will be lost next time it is built.\n")
        f.close()
        return


def check_zone(zone, file):
    checkcmd = '/usr/sbin/named-checkzone %s %s' % (zone, file)
    checkresult = os.popen(checkcmd).read()
    return checkresult.endswith("OK\n")


def get_temp_file(zone):
    zone_name = zone.origin.to_text(omit_final_dot=True)
    return 'out/zones/%s' % (zone_name)


if __name__ == "__main__":
    helper = NetboxHelper.getInstance()

    parser = argparse.ArgumentParser(description='Generate Oxidized config.')

    args = parser.parse_args()

    config = EmfNoc.load_config()

    if not os.path.exists('out'):
        os.mkdir('out')
    if not os.path.exists('out/zones'):
        os.mkdir('out/zones')

    print("Generating zones")

    zones = generate_zones()

    print("Outputting zones")

    for zone_name, zone in zones.items():
        tempfile = get_temp_file(zone)
        # zoneserial = get_serial(zonename)
        # print("* %s" % (zone_name))
        write_zone(zone, tempfile)

    if os.name != 'nt':
        print("Verifying zones")

        ok = not_ok = 0
        for zone_name, zone in zones.items():
            tempfile = get_temp_file(zone)
            if check_zone(zone_name, tempfile):
                ok += 1
            else:
                print("VALIDATION FAILED: %s for %s" % (tempfile, zone_name))
                not_ok += 1

        print("Zone validation: %d ok, %d not ok" % (ok, not_ok))

        if not_ok > 0:
            print("Validation failed, aborting")
            sys.exit(1)

    sys.exit(0)

    if args.deploy:
        print("Signing...")
        # tell zkt-signer that the zones have changed
        os.system("zkt-signer -v -r")

        print("zones deployed: %d successfully, %d failed" % (success, failed))

sys.exit(0)

codenamepos = 0


def ip6_arpa(octets, therange):
    out = ""
    for i in therange:
        if out != "":
            out = "." + out
        out = "%x.%x" % (ord(octets[i]) & 0xf, ord(octets[i]) >> 4) + out
    return out


def reverse_zone(address):
    octets = address.packed
    if isinstance(address, ipaddress.IPv4Address):
        return "%s.%s.%s.in-addr.arpa" % (ord(octets[2]), ord(octets[1]), ord(octets[0]))
    elif isinstance(address, ipaddress.IPv6Address):
        # it's a /32, so we want bytes 0-3 (nibbles 0-7)
        return ip6_arpa(octets, range(0, 4)) + ".ip6.arpa"


# x"c.8.0.0.8.f.7.0.1.0.0.2.ip6.arpa"
# x = ipaddr.IPAddress("2001:7f8:8c:57::11")
# print reverse_zone(x)
# print ip6_arpa(x.packed, range(6,16)) # it's a /48 so we want bytes 6-15
# exit()

def add_record(zonename, record):
    if zonename not in zones.keys():
        zones[zonename] = []
    zones[zonename].append(record)


def add_ipv4_host(hostname, fwd_zonename, ipv4, forward_only, reverse_only):
    if not reverse_only:
        # v4 forward
        record = "%s\tIN\tA\t%s" % (hostname, ipv4.compressed)
        add_record(fwd_zonename, record)

        if hostname in sshfps:
            for r in sshfps[hostname]:
                add_record(fwd_zonename, r)

    if forward_only:
        return

    # v4 reverse
    rev4_zonename = reverse_zone(ipv4)

    # remove any existing reverse if it exists
    if rev4_zonename in zones.keys():
        for record in zones[rev4_zonename]:
            if record.startswith("%s\tIN\tPTR\t" % (ord(ipv4.packed[3]))):
                zones[rev4_zonename].remove(record)
                break

    record = "%s\tIN\tPTR\t%s.%s." % (ord(ipv4.packed[3]), hostname, fwd_zonename)
    add_record(rev4_zonename, record)


def add_ipv6_host(hostname, fwd_zonename, ipv6, forward_only, reverse_only):
    if not reverse_only:
        # v6 forward
        record = "%s\tIN\tAAAA\t%s" % (hostname, ipv6.compressed)
        add_record(fwd_zonename, record)

    if forward_only:
        return

    # v6 reverse
    rev6_zonename = reverse_zone(ipv6)
    rev6_hostname = ip6_arpa(ipv6.packed, range(4, 16))  # it's a /32 so we want bytes 4-15

    record = "%s\tIN\tPTR\t%s.%s." % (rev6_hostname, hostname, fwd_zonename)
    add_record(rev6_zonename, record)


def pretty_host(zonename, ipv4):
    if (zonename == "emf.camp"):
        octets = ipv4.packed
        return "host-%s-%s-%s-%s" % (ord(octets[0]), ord(octets[1]), ord(octets[2]), ord(octets[3]))
    else:
        global codenamepos
        if (codenamepos % len(codenames) == codenamepos / len(codenames)):
            codenamepos += 1
        code1 = codenamepos / len(codenames)
        code2 = codenamepos % len(codenames)
        if code1 >= len(codenames):
            print("RUN OUT OF CODENAMES AT POS %d" % codenamepos)
            exit(1)

        codename1 = codenames[code1]["Codename"].strip().replace(" ", "")
        codename2 = codenames[code2]["Codename"].strip().replace(" ", "")
        codenamepos += 1
        return codename1 + "-" + codename2


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


def get_sshfps():
    #
    # There is a way of getting puppet to grab the keys
    # from the hosts it manages and then generating the records
    # but this was quicker
    #
    fps = {}
    if not os.path.exists("sshfps"):
        print("no sshfps records")
        return fps

    fh = open("sshfps", "r")
    for line in fh:
        host = line.split()[0]
        if host not in fps:
            fps[host] = []
        fps[host].append(line.strip())
    fh.close()
    return fps


default_domain = "emf.camp"

config = ConfigParser.ConfigParser()
if not config.read("/etc/emf-gdata.conf"):
    print("Warning: config file /etc/emf-gdata.conf could not be found or read")

parser = argparse.ArgumentParser(description='Generate cisco IOS config files from gdocs.')

parser.add_argument('--deploy', action='store_true',
                    help='deploy zone files after generating')

parser.add_argument('--diff', action='store_true',
                    help='diff zone files against live versions after generating')

args = parser.parse_args()

spreadsheet = config.get('gdata', 'noc_combined')

spr_client = login("emfcamp DNS zone generator", config)
#
# print( "downloading Addressing")
# addressing = get_worksheet_data(spr_client, spreadsheet, "Addressing")
#
# print "downloading codenames"
# codenames = get_worksheet_data(spr_client, spreadsheet, "Codenames")

# for x in range(0, 2560000):
#  print pretty_host("gchq.org.uk", None)

sshfps = get_sshfps()
zones = {}

for row in addressing:
    if "Domain" in row:
        fwd_zonename = row["Domain"];
    else:
        fwd_zonename = default_domain

    # is it a host?
    if "Hostname" in row and "dns" in row and (row["dns"] == "y" or row["dns"] == "fwd" or row["dns"] == "rev"):
        hostname = row["Hostname"]
        if "Subdomain" in row:
            hostname += "." + row["Subdomain"]

        if "IPv4" in row:
            ipv4 = ipaddr.IPv4Address(row["IPv4"])
            add_ipv4_host(hostname, fwd_zonename, ipv4, (row["dns"] == "fwd"), (row["dns"] == "rev"))

        if "IPv6" in row:
            ipv6 = ipaddr.IPv6Address(row["IPv6"])
            add_ipv6_host(hostname, fwd_zonename, ipv6, (row["dns"] == "fwd"), (row["dns"] == "rev"))

    # is it a subnet with auto dns?
    elif "IPv4-Subnet" in row and "dns" in row and row["dns"] == "auto":
        subnet = ipaddr.IPv4Network(row["IPv4-Subnet"])
        # router entry
        if "VLAN" in row:
            vlan = row["VLAN"]
            add_ipv4_host("vlan" + vlan + ".ESNORE", "emf.camp", subnet.network + 1, False, False)
            #      if "IPv6" in row:
            ipv6 = ipaddr.IPv6Network(row["IPv6"])
            add_ipv6_host("vlan" + vlan + ".ESNORE", "emf.camp", ipv6.network + 1, False, False)

        # host entries
        for ipv4 in subnet.iterhosts():
            if ipv4 == subnet.network + 1:  # first host is the gateway
                continue
            hostname = pretty_host(fwd_zonename, ipv4)
            if "Subdomain" in row:
                hostname += "." + row["Subdomain"]
            add_ipv4_host(hostname, fwd_zonename, ipv4, False, False)

    # is it a cname or other fixed record?
    elif "dns" in row and row["dns"] == "record":
        hostname = row["Hostname"]
        if "Subdomain" in row:
            hostname += "." + row["Subdomain"]
        add_record(fwd_zonename, hostname + "\t" + row["Description"])

    # if it's a Network with dns='y', we need to 'touch' all the reverse dns to make sure
    # every individual zone exists
    elif "Network" in row and "dns" in row and row["dns"] == "y":
        net = ipaddr.IPv4Network(row["Network"])
        for subnet in net.iter_subnets(new_prefix=24):
            zone_name = reverse_zone(subnet)
            if zone_name not in zones.keys():
                zones[zone_name] = []


# print "ZONES:"
# pprint.pprint(zones)

# write out zone files

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
