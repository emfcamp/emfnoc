#!/usr/bin/python

# EMF icinga config generator

import ipaddr, time, os, sys, ConfigParser

from nocsheet import login, get_worksheets, get_worksheet_data

if not os.path.exists('out'):
  os.mkdir('out')

if not os.path.exists('out/icinga'):
  os.mkdir('out/icinga')

config = ConfigParser.ConfigParser()
if not config.read("/etc/emf-gdata.conf"):
  print "Warning: config file /etc/emf-gdata.conf could not be found or read"

spreadsheet = config.get('gdata', 'noc_combined')

spr_client = login("emfcamp DHCP config generator", config)

print "downloading Switches"
switches = get_worksheet_data(spr_client, spreadsheet, "Switches")

print "downloading Links"
links = get_worksheet_data(spr_client, spreadsheet, "Links")

print "downloading VMs"
vms = get_worksheet_data(spr_client, spreadsheet, "VMs")

po_index = {}

def short_port(port):
  return port.replace("TenGigabitEthernet", "Te").replace("GigabitEthernet", "Gi").replace("FastEthernet", "Fa")

def add_host(hostname, ip, parent):
  global f
  f.write("define host {\n")
  f.write("  use generic-host\n")
  f.write("  host_name " + hostname + "\n")
  f.write("  alias " + hostname + ".emf.camp\n")
  f.write("  address " + ip + "\n")
  if parent:
    f.write("  parents " + parent + "\n")
  f.write("}\n\n")


def add_port(f, switch1, switch1port, switch2, servicegroup):
  f.write("define service {\n")
  f.write("  use              generic-ifoperstatus\n")
  f.write("  host_name       " + switch1 + "\n")
  f.write("  service_description " + short_port(switch1port) + " to " + switch2 + "\n")
  tag = switch1port
  if "SWDIST" in switch1:
    tag = "X650-24x\(SSns\) Port " + tag
  f.write("  check_command    check_ifoperstatus!\"" + tag + "\"\n")
  f.write("  servicegroups    " + servicegroup + "\n")
  f.write("}\n\n")


# unique list of vmhosts
vmhosts = {}
monitorparent = None
for vm in vms:
  if 'Hostname' in vm and vm['Hostname'] == "!end":
    break
  if "Parent" in vm:
    vmhosts[vm['Parent']] = vm['Parent']
#    if vm['Hostname'] == "monitor1.emf.camp":
#      monitorparent = vm['Parent']

with open("out/icinga/vmhosts.cfg", "w") as f:
  # all the vmhosts
  for vmhost in vmhosts:
    # or maybe LOSELEY
    parent = "SWNOC-DC"
    # the host holding monitor1 has a parent of monitor1
#    if monitorparent == vmhost:
#      parent = "monitor1"
    add_host(vmhost, vmhost + ".emf.camp", parent)

with open("out/icinga/vms.cfg", "w") as f:
  # all the vms
  for vm in vms:
    if 'Hostname' in vm and vm['Hostname'] == "!end":
      break
    if "IPv4" in vm:
      print vm
      if 'Parent' not in vm:
        print "WARNING: no parent for " + vm['Hostname'] + " ignoreing."
        continue
      parent = vm['Parent']
      add_host(vm['Hostname'].replace(".emf.camp", ""), vm['IPv4'], parent)

#TODO ssh etc

hostnames = {}

with open("out/icinga/network.cfg", "w") as f:
  for switch in switches:
    if "Hostname" in switch:
      if switch['Hostname'] not in hostnames:
        hostnames[switch['Hostname']] = 1
      else:
        print "PANIC: Duplicate switch hostname " + switch['Hostname']
        sys.exit(1)

      # Find our parent. Search the links for one where we're in second position
      parent = None
      for link in links:
        if link['Switch2'] == switch['Hostname']:
          parent = link['Switch1']
#      if switch["Hostname"] == 'SWCORE':
#        parent = 'vmhost1'

      add_host(switch["Hostname"], switch["Mgmt-IP"], parent)

# Links
  for link in links:
    if link['Switch2'] not in hostnames:
      # currently the uplink and the WLC
      print "Unknown destination switch " + link['Switch2']
      continue

    servicegroup = "link_" + link['Switch1'] + "_" + link['Switch2']
    f.write("define servicegroup {\n")
    f.write("  servicegroup_name " + servicegroup + "\n")
    f.write("  alias            Link from " + link['Switch1'] + " to " + link['Switch2'] + "\n")
    f.write("}\n\n")

    add_port(f, link['Switch1'], link['Switch1-Port1'], link['Switch2'], servicegroup)
    if ('Switch1-Port2' in link):
      add_port(f, link['Switch1'], link['Switch1-Port2'], link['Switch2'], servicegroup)
    add_port(f, link['Switch2'], link['Switch2-Port1'], link['Switch1'], servicegroup)
    if ('Switch2-Port2' in link):
      add_port(f, link['Switch2'], link['Switch2-Port2'], link['Switch1'], servicegroup)
# Now add the port channel
# Now create the servicegorup

