#!/usr/bin/python

#
# generate zone files from google spreadsheet
#
# Updated by JasperW to handle DNSSEC
# Updated by DavidC for 2014 spreadsheet format and more automation
#

import ipaddr
import time
import string
import os, pprint, ConfigParser, argparse
import shutil, sys, getpass

from subprocess import Popen, PIPE
from nocsheet import login, get_worksheets, get_worksheet_data

def hostin4net(network,hostoctet):
  ssubnet = network.split('/')
  asubnet = ssubnet[0].split('.')
  asubnet[3] = hostoctet
  return string.join(asubnet,'.')

def hostin6net(network,hostaddr):
  ssubnet = network.split('/')

  return "%s%s" % (ssubnet[0],hostaddr)

def subnet4tozone(network):
  ssubnet = network.split('/')
  asubnet = ssubnet[0].split('.')
  zonename = "%s.%s.%s.in-addr.arpa" % (asubnet[2],asubnet[1],asubnet[0])
  return zonename

def ip6_arpa(octets, therange):
  out = ""
  for i in therange:
    if out != "":
      out = "." + out
    out = "%x.%x" % (ord(octets[i]) & 0xf, ord(octets[i]) >> 4) + out
  return out

def reverse_zone(address):
  octets = address.packed
  if isinstance(address, ipaddr._BaseV4):
    return "%s.%s.%s.in-addr.arpa" % (ord(octets[2]), ord(octets[1]), ord(octets[0]))
  elif isinstance(address, ipaddr._BaseV6):
    # it's a /48, so we want bytes 0-5 (nibbles 0-11)
    return ip6_arpa(octets, range(0, 6)) + ".ip6.arpa"
    return zone

#x"c.8.0.0.8.f.7.0.1.0.0.2.ip6.arpa"
#x = ipaddr.IPAddress("2001:7f8:8c:57::11")
#print reverse_zone(x)
#print ip6_arpa(x.packed, range(6,16)) # it's a /48 so we want bytes 6-15
#exit()

def add_record(zonename, record):
  if zonename not in zones.keys():
    zones[zonename] = []
  zones[zonename].append(record)

def add_ipv4_host(hostname, fwd_zonename, ipv4):
  #v4 forward
  record = "%s\tIN\tA\t%s" % (hostname, ipv4.compressed)
  add_record(fwd_zonename, record)

  if hostname in sshfps:
    for r in sshfps[hostname]:
      add_record(fwd_zonename, r)

  #v4 reverse
  rev4_zonename = reverse_zone(ipv4)

  record = "%s\tIN\tPTR\t%s.%s." % (ord(ipv4.packed[3]), hostname, fwd_zonename)
  add_record(rev4_zonename, record)

def add_ipv6_host(hostname, fwd_zonename, ipv6):
  #v6 forward
  record = "%s\tIN\tAAAA\t%s" % (hostname, ipv6.compressed)
  add_record(fwd_zonename, record)

  #v6 reverse
  rev6_zonename = reverse_zone(ipv6)
  rev6_hostname = ip6_arpa(ipv6.packed, range(6,16)) # it's a /48 so we want bytes 6-15

  record = "%s\tIN\tPTR\t%s.%s." % (rev6_hostname, hostname, fwd_zonename)
  add_record(rev6_zonename, record)

def pretty_host(ipv4):
  octets = ipv4.packed
  return "host-%s-%s-%s-%s" % (ord(octets[0]), ord(octets[1]), ord(octets[2]), ord(octets[3]))



def writezone(domainname,serial,entries,tempfile):
  if os.path.exists(tempfile) == True:
    os.remove(tempfile)
  f = open(tempfile, "w")
  f.write("\n")
  f.write("; zone file built by gen-zones.py from EMF2014 Google Spreadsheet\n")
  f.write("; %s.\n" % (domainname))
  f.write("\n")
  f.write("$TTL    1h\n")
  f.write("$ORIGIN %s.\n" % (domainname))
  f.write("@   IN  SOA ns1.emfcamp.org.    noc.emfcamp.org (\n")
  f.write("            %s ; serial\n" % (serial))
  f.write("            3H ; refresh\n")
  f.write("            15 ; retry\n")
  f.write("            1w ; expire\n")
  f.write("            3h ; minimum\n")
  f.write("        )\n")
  f.write("\n")
  f.write("      IN      NS  ns1.emfcamp.org.\n")
  f.write("      IN      NS  auth1.ns.sargasso.net.\n")
  f.write("      IN      NS  auth2.ns.sargasso.net.\n")
  f.write("      IN      NS  auth3.ns.sargasso.net.\n")
  f.write("\n")
  for row in entries:
    f.write("%s\n" % (row))
  f.close()
  return

def checkzone(domain, file):
  checkcmd = "/usr/sbin/named-checkzone %s %s" % (domain,file)
  checkresult = os.popen(checkcmd).read()
  if checkresult.endswith("OK\n") == True:
    return True
  else:
    return False

def makezonelive(domain,file):
  if getpass.getuser() != "root":
    print "  - Cannot put zone live, must be run as root"
    return False
  livepath = "/etc/bind/master/%s" % (domain)
  shutil.copyfile(file,livepath)
  os.remove(file)

  # tell zkt-signer that the zone has changed
  if os.path.exists("/etc/bind/signed-zones/" + domain + "/zone.db"):
    os.utime("/etc/bind/signed-zones/" + domain + "/zone.db", None)
    os.system("zkt-signer -v " + domain)

  reloadzone(domain)
  return True

def reloadzone(domain):
  print "  - Reloading"
  reloadcmd = "rndc reload %s" % (domain)
  reloadresult = os.popen(reloadcmd).read()
  return

def get_sshfps():
  #
  # There is a way of getting puppet to grab the keys
  # from the hosts it manages and then generating the records
  # but this was quicker
  #
  fps = {}
  if not os.path.exists("sshfps"):
    print "no sshfps records"
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

if not os.path.exists('out'):
  os.mkdir('out')
if not os.path.exists('out/zones'):
  os.mkdir('out/zones')

config = ConfigParser.ConfigParser()
if not config.read("/etc/emf-gdata.conf"):
  print "Warning: config file /etc/emf-gdata.conf could not be found or read"


parser = argparse.ArgumentParser(description='Generate cisco IOS config files from gdocs.')

parser.add_argument('--deploy', action='store_true',
                    help='deploy zone files after generating')

args = parser.parse_args()


spreadsheet = config.get('gdata', 'noc_combined')

spr_client = login("emfcamp DNS zone generator", config)

print "downloading Addressing"
addressing = get_worksheet_data(spr_client, spreadsheet, "Addressing")

sshfps = get_sshfps()
zones = {}



for row in addressing:
  if "Domain" in row:
    fwd_zonename = row["Domain"];
  else:
    fwd_zonename = default_domain

  # is it a host?
  if "Hostname" in row and "dns" in row and row["dns"] == "y":
    hostname = row["Hostname"]
    if "Subdomain" in row:
      hostname += "." + row["Subdomain"]

    if "IPv4" in row:
      ipv4 = ipaddr.IPv4Address(row["IPv4"])
      add_ipv4_host(hostname, fwd_zonename, ipv4)

    if "IPv6" in row:
      ipv6 = ipaddr.IPv6Address(row["IPv6"])
      add_ipv6_host(hostname, fwd_zonename, ipv6)

  # is it a subnet with auto dns?
  elif "IPv4-Subnet" in row and "dns" in row and row["dns"] == "auto":
    subnet = ipaddr.IPv4Network(row["IPv4-Subnet"])
    # router entry
    if "VLAN" in row:
      vlan = row["VLAN"]
      add_ipv4_host("vlan" + vlan + ".SWCORE", "emf.camp", subnet.network + 1)
#      if "IPv6" in row:
      ipv6 = ipaddr.IPv6Network(row["IPv6"])
      add_ipv6_host("vlan" + vlan + ".SWCORE", "emf.camp", ipv6.network + 1)

    # host entries
    for ipv4 in subnet.iterhosts():
      if ipv4 == subnet.network + 1: # first host is the gateway
        continue
      hostname = pretty_host(ipv4)
      if "Subdomain" in row:
        hostname += "." + row["Subdomain"]
      add_ipv4_host(hostname, fwd_zonename, ipv4)

  # is it a cname?
  elif "dns" in row and row["dns"] == "record":
    hostname = row["Hostname"]
    if "Subdomain" in row:
      hostname += "." + row["Subdomain"]
    add_record(fwd_zonename, hostname + "\t" + row["Description"])

#print "ZONES:"
#pprint.pprint(zones)

# write out  zone files

oserial = None
zoneserial = time.strftime("%Y%m%d%H")
zoneserial = int(time.time())

def get_serial(zonename):
  realzone = "/etc/bind/master/" + zonename
  if not os.path.exists(realzone):
    print "Can't open " + realzone + ", using default serial number"
    return int(time.time())
  zfh = open(realzone, "r")
  got = False
  for line in zfh:
    if got:
      line = line.strip()
      line = line.split()[0]
      zoneserial = int(line)
      zoneserial += 1
      got = False
      break
    if "SOA ns1.emfcamp.org" in line:
      got = True
  zfh.close()
  return zoneserial


print "Generating zones"
for zonename in zones.keys():
  tempfile = "out/zones/%s" % (zonename)
  zoneserial = get_serial(zonename)
  print "* %s" % (zonename),
  writezone(zonename, zoneserial, zones[zonename], tempfile)
  if checkzone(zonename, tempfile) == True:
    print " ok"
    if args.deploy:
      makezonelive(zonename, tempfile)
  else:
    print " VALIDATION FAILED: %s" % (tempfile)
