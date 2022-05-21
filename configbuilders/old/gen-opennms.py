#!/usr/bin/python

# EMF opennms config generator

import ipaddr, time, os, sys, ConfigParser, shelve

from nocsheet import login, get_worksheets, get_worksheet_data
from gen_switch import get_vlans

if not os.path.exists('out'):
  os.mkdir('out')

if not os.path.exists('out/opennms'):
  os.mkdir('out/opennms')

addressing = shelve.open("data/addressing")["list"]
print "generating VLANs"
vlans = get_vlans(addressing)

config = ConfigParser.ConfigParser()
if not config.read("/etc/emf-gdata.conf"):
  print "Warning: config file /etc/emf-gdata.conf could not be found or read"

#spreadsheet = config.get('gdata', 'noc_combined')

#spr_client = login("emfcamp DHCP config generator", config)

#print "downloading Addressing"
#ipv4 = get_worksheet_data(spr_client, spreadsheet, "Addressing")

ofh = open("out/opennms/import.sh", "w")

ofh.write("#!/bin/sh\n\n")

for row in addressing:
  if 'Hostname' in row and 'IPv4' in row:
    for t in ('Hostname', 'IPv4'):
      if t in row:
        print row[t],
    ofh.write("# " + row['Hostname'] + "\n")
    ofh.write("/usr/share/opennms/bin/send-event.pl  --interface " + row['IPv4'] + " uei.opennms.org/internal/discovery/newSuspect\n")
    print

ofh.close()
