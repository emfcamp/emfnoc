#!/usr/bin/env python

from nocsheet import login, get_worksheets, get_worksheet_data
import ipaddr, jinja2, ConfigParser, argparse, shelve, gdata, code, shelve, os, sys, pprint
from jinja2 import Template, FileSystemLoader, Environment

def print_worksheets(spr_client, spreadsheet):
  worksheets = spr_client.GetWorksheetsFeed(key=spreadsheet)
  for e in worksheets.entry:
    print e.title.text + " : " + e.id.text.rsplit('/', 1)[1]

def download(spr_client, spreadsheet):
  if not os.path.exists('data'):
    os.mkdir('data')

  print "downloading switches"
  switches = get_worksheet_data(spr_client, spreadsheet, "Switches")

  sws = shelve.open("data/switches")
  sws['list'] = switches
  sws.close()

  print "downloading port types"
  port_types = get_worksheet_data(spr_client, spreadsheet, "Port Types")

  pt = shelve.open("data/port_types")
  pt['list'] = port_types
  pt.close()

  print "downloading users"
  users = get_worksheet_data(spr_client, spreadsheet, "Users")
  for user in list(users):
    if not "IOS password" in user:
      users.remove(user)

  u = shelve.open("data/users")
  u["list"] = users
  u.close()

  print "downloading Addressing"
  addressing = get_worksheet_data(spr_client, spreadsheet, "Addressing")
  
  v4 = shelve.open("data/addressing")
  v4["list"] = addressing
  v4.close()

  print "downloading Links"
  links = get_worksheet_data(spr_client, spreadsheet, "Links")
  
  l = shelve.open("data/links")
  l["list"] = links
  l.close()

  print "done"

def get_vlans(addressing):
  vlans = {}

  for line in addressing:
    if 'VLAN' in line:
      if 'Description' not in line:
        print "No description for VLAN " + line['VLAN']
        sys.exit(1)
      desc = ''

      if line['Description'] == "(Temp Staging pre event)":
        line['Description'] = "Temp Staging pre event"
      for c in line['Description']:
        if c.isalnum():
          desc += c
        elif c == '(':
          break
        else:
          if len(desc) > 0 and desc[len(desc)-1] != '-':
            desc += '-'

      print "Preparing VLAN " + line['VLAN']
      vlans[line['VLAN']] = { 'ipv4': line['IPv4-Subnet'],
                              'ipv4_subnet': ipaddr.IPv4Network(line['IPv4-Subnet']),
                              'name': desc,
                              'vlan': int(line['VLAN']),
                              'dhcp': ('dhcp' in line and line['dhcp'] == 'y'),
                              'sitewide': ('Sitewide' in line and line['Sitewide'] == 'y')
                              }

      if 'IPv6' in line:
        vlans[line['VLAN']]['ipv6'] = line['IPv6']
        vlans[line['VLAN']]['ipv6_subnet'] = ipaddr.IPv6Network(line['IPv6'])

#      print vlans[line['VLAN']]

  return vlans

def dump_worksheet(spr_client, spreadsheet, wks):
  print get_worksheet_data(spr_client, spreadsheet, wks)

def switch_hostname_exists(switches, name):
  for sw in switches:
    if sw['Hostname'] == name:
      return True
  return False

def generate(override_template):
  if os.path.isfile("data/switches") and os.path.isfile("data/users") and os.path.isfile("data/addressing"):

    switches = shelve.open("data/switches")["list"]
    port_types = shelve.open("data/port_types")["list"]
    users = shelve.open("data/users")["list"]

    addressing = shelve.open("data/addressing")["list"]
    print "generating VLANs"
    vlans = get_vlans(addressing)
  
    links = shelve.open("data/links")["list"]
  
    sw_links = {}

    sw_cvlan = {}
    cvlan_to_sw = {}
  
    # check camper vlans for issues
    for sw in switches:
      if "Camper-VLAN" in sw:
        if sw["Hostname"] in sw_cvlan:
          print "PANIC: Duplicate Hostname: >" + sw["Hostname"] + "<"
          sys.exit(1)
        sw_cvlan[sw["Hostname"]] = sw["Camper-VLAN"]
  
        if sw["Camper-VLAN"] in cvlan_to_sw:
          print "PANIC: Duplicate camper vlan id: >" + sw["Camper-VLAN"] + "<"
          print "for " + sw["Hostname"] + " and " + cvlan_to_sw[sw["Camper-VLAN"]]
          sys.exit(1)
        cvlan_to_sw[sw["Camper-VLAN"]] = sw["Hostname"]
  
    for a in addressing:
      if "VLAN" in a:
        if a["VLAN"] in cvlan_to_sw:
          if cvlan_to_sw[a["VLAN"]] != a["Description"]:
            print "WARNING - Camper VLAN missmatch?!?!"
            print a["VLAN"], a["Description"], cvlan_to_sw[a["VLAN"]]
            print "^---"
  
    for link in links:
      o = {"Dir" : "down"}
      o2 = {"Dir" : "up"}
  #    print link
  
      if not switch_hostname_exists(switches, link["Switch1"]):
        print "WARNING: switch in links but not on the Switches sheet >" + link["Switch1"] + "<"
  
      if not switch_hostname_exists(switches, link["Switch2"]):
        print "WARNING: switch in links but not on the Switches sheet >" + link["Switch2"] + "<"
  
      if link["Switch1"] not in sw_links:
        sw_links[link["Switch1"]] = []
  
      if link["Switch2"] not in sw_links:
        sw_links[link["Switch2"]] = []
  
      o["To"] = link["Switch2"]
      o2["To"] = link["Switch1"]
      o["Ports"] = []
      for port in (("Switch1-Port1", "Switch2-Port1"), ("Switch1-Port2", "Switch2-Port2")):
        if port[0] in link:
          o["Ports"].append((link[port[0]], link[port[1]]))
  
      o2["Ports"] = []
      for port in (("Switch2-Port1", "Switch1-Port1"), ("Switch2-Port2", "Switch1-Port2")):
        if port[0] in link:
          o2["Ports"].append((link[port[0]], link[port[1]]))
  
      sw_links[link["Switch1"]].append(o)
      sw_links[link["Switch2"]].append(o2)
    
    loader = FileSystemLoader('templates')
    env = Environment(loader=loader)
  
    if not os.path.exists('out'):
      os.mkdir('out')
    if not os.path.exists('out' + os.path.sep + "switches"):
      os.mkdir('out' + os.path.sep + "switches")
  
    # Hostname  -> vlan_id
    sw_to_vlan = {}
    for sw in switches:
      if "Camper-VLAN" in sw:
        sw_to_vlan[sw["Hostname"]] = sw["Camper-VLAN"]
    
    # Hostname -> [child Hostname, child Hostname]
    sw_children = {}
    for sw in switches:
      if sw["Hostname"] in sw_links:
        sw["Links"] = sw_links[sw["Hostname"]]
        for l in sw["Links"]:
          if l["Dir"] == "down":
  #          print l["To"], l["Dir"]
            if sw["Hostname"] not in sw_children:
              sw_children[sw["Hostname"]] = []
            sw_children[sw["Hostname"]].append(l["To"])
  
    # all sitewide vlans
    sitewide_vlans = ""
    for id, vlan in vlans.items():
      if vlan['sitewide']:
        if sitewide_vlans:
          sitewide_vlans += ","
        sitewide_vlans += str(vlan['vlan'])
  
  #  for k in sw_children:
  #    print k, sw_children[k]
  
    # graphiz is fun :)
    gfh = open("out/vlans.gv", "w")
  
    gfh.write("##Command to produce the output: \"neato -Tpng thisfile > thisfile.png\"\n\n")
    
    gfh.write("""digraph Vlans {\n""")
  #  node [shape=box];  gy2; yr2; rg2; gy1; yr1; rg1;
  #  node [shape=circle,fixedsize=true,width=0.9];  green2; yellow2; red2; safe2; safe1; green1; yellow1; red1;
  
    for k in sw_children:
      for c in sw_children[k]:
        gfh.write('"' + k + '"' + " -> " + '"' +  c + "\";\n")
  
    gfh.write("""
    overlap=false
    label="EMFCamp Switches and Vlans\\nlaid out by Graphviz"
    fontsize=12;
    }
    """)
  
    gfh.close()
  
  #  print sw_to_vlan
  #  print
  #  print sw_children
  #  print

  else:
    print "No datasources, did you --download first?"
    sys.exit(1)

  def get_swchildren(sw, cs = None):
    if not cs:
      cs = {}
    if sw not in sw_children:
      return {}
    for c in sw_children[sw]:
      if c in sw_to_vlan:
        if sw_to_vlan[c] not in cs:
          cs[sw_to_vlan[c]] = 1
#      else:
#        print "no vlan for " + c
      cs.update(get_swchildren(c, cs))
    return cs

  sw_uplink_vlans = {}
  for sw in switches:
    k = sw["Hostname"]
    if k not in sw_uplink_vlans:
      sw_uplink_vlans[k] = get_swchildren(k)
      if k in sw_to_vlan:
        sw_uplink_vlans[k][sw_to_vlan[k]] = 1

  o = {}
  for sw in sw_uplink_vlans:
    ks = sw_uplink_vlans[sw].keys()
    ks.sort()
    o[sw] = ks

  sw_uplink_vlans = o    

#  for k in sw_uplink_vlans:
#    print k, sw_uplink_vlans[k]

  for sw in switches:
    print "Generating " + sw["Hostname"] + " of type " + sw["Type"]

##
## Do something smart with port assignments here..
## Artnet, Voip, Dect, Voc, Bar
##
    if not "Ports" in sw or len(sw["Ports"]) == 0:
      sw["Ports"] = 48

    sw['port_configs'] = []
    for i in range(int(sw['Camper-Ports'])):
        sw['port_configs'].append({ 'description': 'Camper', 'vlan': sw['Camper-VLAN']})

    for port_type in reversed(port_types):
        if ('#'+port_type["Port-Type"]) in sw:
            for i in range(int(sw['#'+port_type['Port-Type']])):
                sw['port_configs'].append({ 'description': port_type['Port-Type'], 'vlan': port_type['VLAN']})
    print sw


    if "Links" not in sw:
      print "*** No links found for switch ", sw["Hostname"]

    mycampervlan = None
    if "Camper-VLAN" in sw:
      mycampervlan = vlans[sw["Camper-VLAN"]]
      mycampervlan["ipv4-subnet"] = ipaddr.IPv4Network(mycampervlan["ipv4"])
      mycampervlan["ipv6-subnet"] = ipaddr.IPv6Network(mycampervlan["ipv6"])
#      print mycampervlan["ipv4-subnet"].network

    if sw["Hostname"] in sw_uplink_vlans:
      sw["Uplink Vlans"] = sw_uplink_vlans[sw["Hostname"]]

    if override_template:
      template = env.get_template(override_template + ".j2")
      found = True
    else:
      found = False
      for tname in (sw["Hostname"], sw["Model"], sw["Type"]):
        if os.path.exists("templates" + os.path.sep + tname + ".j2"):
          template = env.get_template(tname + ".j2")
          found = True
          break


    if found:
      out = template.render(users=users, switch=sw, vlans=vlans, mycampervlan=mycampervlan, config=config, uplink_vlans=sw_uplink_vlans, sitewide_vlans=sitewide_vlans).encode("utf-8", "replace")

      # remove excess empty lines
      while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")

      ofh = open("out" + os.path.sep + "switches" + os.path.sep + sw["Hostname"] + ".emf.camp", "w")
      ofh.write(out)
      ofh.close()
    else:
      print " - No template found for " + sw["Hostname"] + "!"

  # make it eaiser to match switch config to a switch
  for sw in switches:
    if os.path.islink("out" + os.path.sep + "switches" + os.path.sep + sw["Serial"]):
      os.unlink("out" + os.path.sep + "switches" + os.path.sep + sw["Serial"])
    os.symlink(sw["Hostname"] + ".emf.camp", "out" + os.path.sep + "switches" + os.path.sep + sw["Serial"])

  # rancid
  rfh = open("out" + os.path.sep + "router.db", "w")
  for sw in switches:
    o = sw["Hostname"].lower() + ".emf.camp"
    if sw["Type"] == "ios":
      o += ";cisco;up"
    elif sw["Type"] == "ios-core":
      o += ";cisco;up"
    elif sw["Type"] == "xos":
      o += ";Extreme;up"
    elif sw["Type"] == "eos":
      o += ";arista;up"
    elif sw["Type"] == "eos-core":
      o += ";arista;up"
    elif sw["Type"] == "junos":
      o += ";juniper;up"
    elif sw["Type"] == "junos-els":
      o += ";juniper;up"
    elif sw["Type"] == "procurve":
      o += ";hp;up"
    else:
      print "**** unknown type:", sw["Type"]
      exit()
    rfh.write(o + "\n")
  rfh.close()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Generate cisco IOS config files from gdocs.')

  parser.add_argument('--listws', action='store_true',
    help='list worksheets')

  parser.add_argument('--dumpws', type=str, nargs=1, metavar=('<sheet>'),
    help='dump the contents of a worksheet, don\'t forget to quote the name!')
          
  parser.add_argument('--download', action='store_true',
    help='download the relevent bits from the sheet')

  parser.add_argument('--generate', action='store_true',
    help='generate the configs')

  parser.add_argument('--template', action='store',
    help='override the template')

  args = parser.parse_args()

  config = ConfigParser.ConfigParser()
  if not config.read("/etc/emf-gdata.conf"):
    print "Warning: config file /etc/emf-gdata.conf could not be found or read"

  spreadsheet = config.get('gdata', 'noc_combined')

  if args.listws or args.download or args.dumpws:
    spr_client = login("emfcamp Cisco config generator", config)

  done_something = False

  if args.listws:
    print_worksheets(spr_client, spreadsheet)
    done_something = True
  
  if args.download:
    download(spr_client, spreadsheet)
    done_something = True

  if args.dumpws:
    dump_worksheet(spr_client, spreadsheet, args.dumpws[0])
    done_something = True
  
  if args.generate:
    generate(args.template)
    done_something = True

  if not done_something:
    print "Nothing to do, try " + sys.argv[0] + " --help"
