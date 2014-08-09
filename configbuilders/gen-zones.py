#!/usr/bin/python

# 
# generate zone files from google spreadsheet
# nat@nuqe.net
#

import gdata.spreadsheet.service
import gdata.spreadsheet.text_db
import ipaddr
import time
import string
import os
import shutil
import getpass
from subprocess import Popen, PIPE

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

def checkzone(domain,file):
  checkcmd = "/usr/sbin/named-checkzone %s %s" % (domain,file)
  checkresult = os.popen(checkcmd).read()
  if checkresult.endswith("OK\n") == True:
    return True
  else:
    return False

def makezonelive(domain,file):
  if getpass.getuser() != "root":
    print "  - Cannot put zone live, must be ran as root"
    return False
  livepath = "/etc/bind/master/%s" % (domain)
  shutil.copyfile(file,livepath)
  os.remove(file)
  reloadzone(domain)
  return True

def reloadzone(domain):
  print "  - Reloading"
  reloadcmd = "rndc reload %s" % (domain)
  reloadresult = os.popen(reloadcmd).read()
  return

spreadsheet_key = "0AriFdfLzFu4-dHlsX21Fd2tNSldIVGhabTc1WnZpeEE"
worksheet_subnets = "ocx"
worksheet_dhcp = "od0"
domain = "emfcamp.org"

fwdentries = {}
reventries = {}

print "Connecting to spreadsheet"
spr_client = gdata.spreadsheet.service.SpreadsheetsService()
spr_client.email = ""
spr_client.password = ""
spr_client.source = "emfcamp dns generator"
spr_client.ProgrammaticLogin()

print "Querying hosts"
qsubnets = gdata.spreadsheet.service.ListQuery()
qsubnets.orderby = 'column:v4subnet column:v4'
feedsubnets = spr_client.GetListFeed(spreadsheet_key, worksheet_subnets, query=qsubnets)

# loop through each row
for row_entry in feedsubnets.entry:
  record = gdata.spreadsheet.text_db.Record(row_entry=row_entry)
  hostname = record.content['hostname']
  zone = record.content['zone']

  # is it a host?
  if hostname != None and zone != None:
    subnet4 = record.content['v4subnet']
    host4 = record.content['v4']
    subnet6 = record.content['v6subnet']
    host6 = record.content['v6']

    # create zone dict entry if need be
    if zone not in fwdentries.keys():
      fwdentries[zone] = []

    # v4
    if subnet4 != None and host4 != None:
      # fwd
      row = "%s\tIN\tA\t%s" % (hostname,hostin4net(subnet4,host4))
      fwdentries[zone].append(row)

      # rev
      row = "%s\tPTR\t%s.%s.%s." % (host4,hostname,zone,domain)
      revzone4 = subnet4tozone(subnet4)
      if revzone4 not in reventries.keys():
        reventries[revzone4] = []
      reventries[revzone4].append(row)

    # v6 fwd
    if subnet6 != None and host6 != None:
      row = "%s\tIN\tAAAA\t%s" % (hostname,hostin6net(subnet6,host6))
      fwdentries[zone].append(row)	

# dhcp fwd and rev entries
print "Querying DHCP scopes"
qscopes = gdata.spreadsheet.service.ListQuery()
qscopes.orderby = 'column:subnet'
feedscopes = spr_client.GetListFeed(spreadsheet_key, worksheet_dhcp, query=qscopes)
for row_entry in feedscopes.entry:
  record = gdata.spreadsheet.text_db.Record(row_entry=row_entry)
  version = record.content['version']
  if version == "4":
    net4 = ipaddr.ip_network(record.content['subnet'])
    scopestart = record.content['start']
    scopefinish = record.content['finish']
    scopename = record.content['name']
    scopefwdzone = record.content['fwdzone']
    paststart = False
    pastfinish = False
    for x in net4.iterhosts():
      ip = str(x)
      if ip == scopestart:
        paststart = True
      if paststart == True and pastfinish == False:
        iparr = ip.split('.')
        hostname = "%s-%s-%s" % (scopename,iparr[2],iparr[3])
        fwdrow = "%s\tIN\tA\t%s" % (hostname,ip)
        fwdentries[scopefwdzone].append(fwdrow)
        revzone = subnet4tozone(ip)
        revrow = "%s\tPTR\t%s.%s.%s." % (iparr[3],hostname,scopefwdzone,domain)
        if revzone not in reventries.keys():
          reventries[revzone] = []
        reventries[revzone].append(revrow)
      if ip == scopefinish:
        pastfinish = True


# write out  zone files
zoneserial = time.strftime("%Y%m%d%H")
zoneserial = int(time.time())

# forward zones
print "Generating forward zones"
for zonekey in fwdentries.keys():
  domainname = "%s.%s" % (zonekey,domain)
  tempfile = "/tmp/tmp.%s" % (domainname)
  print "* %s" % (domainname)
  writezone(domainname,zoneserial,fwdentries[zonekey],tempfile)
  if checkzone(domainname,tempfile) == True:
    makezonelive(domainname,tempfile)
  else:
    print "  - Zone problems: %s" % (tempfile)

print ""

# revzones
print "Generating reverse zones"
for zonekey in reventries.keys():
  domainname = zonekey
  tempfile = "/tmp/tmp.%s" % (domainname)
  print "* %s" % (domainname)
  writezone(domainname,zoneserial,reventries[zonekey],tempfile)
  if checkzone(domainname,tempfile) == True:
    makezonelive(domainname,tempfile)
  else:
    print "  - Zone problems: %s" % (tempfile)
