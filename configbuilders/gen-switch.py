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

  print "downloading users"
  users = get_worksheet_data(spr_client, spreadsheet, "User Accounts")
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
#      print line['VLAN']
      desc = ''
      for c in line['Description']:
        if c.isalnum():
          desc += c
        else:
          if len(desc) > 0 and desc[len(desc)-1] != '-':
            desc += '-'

      vlans[line['VLAN']] = { 'ipv4': line['IPv4-Subnet'],
                              'ipv6': '2001:7f8:8c:'+line['VLAN']+'::/64',
                              'name': desc,
                              'vlan': int(line['VLAN'])
                              }
#      print vlans[line['VLAN']]

  return vlans

def dump_worksheet(spr_client, spreadsheet, wks):
  print get_worksheet_data(spr_client, spreadsheet, wks)

def generate():
  switches = shelve.open("data/switches")["list"]
  users = shelve.open("data/users")["list"]
  
  addressing = shelve.open("data/addressing")["list"]
  print "generating VLANs"
  vlans = get_vlans(addressing)

  links = shelve.open("data/links")["list"]

  sw_links = {}
  
  for link in links:
    o = {"Dir" : "down"}
    o2 = {"Dir" : "up"}
#    print link
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
      gfh.write(k + "->" + c + ";\n")

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

    if "Artnet-Hi" in sw:
      sw["artnet"] = range(int(sw["Artnet-Lo"]), int(sw["Artnet-Hi"]) + 1)
  
    if "Camper-Hi" in sw:
      sw["camper"] = range(int(sw["Camper-Lo"]), int(sw["Camper-Hi"]) + 1)
    
#    for l in sw["Links"]:
#      print l

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

    found = False
    for tname in (sw["Hostname"], sw["Model"], sw["Type"]):
      if os.path.exists("templates" + os.path.sep + tname + ".j2"):
        template = env.get_template(tname + ".j2")
        found = True
        break

    if found:
      out = template.render(users=users, switch=sw, vlans=vlans, mycampervlan=mycampervlan, config=config, uplink_vlans=sw_uplink_vlans).encode("utf-8", "replace")

      # remove excess empty lines
      while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")

      ofh = open("out" + os.path.sep + "switches" + os.path.sep + sw["Hostname"] + ".emf.camp", "w")
      ofh.write(out)
      ofh.close()
    else:
      print " - No template found for " + sw["Hostname"] + "!"


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Generate cisco IOS config files from gdocs.')

  parser.add_argument('--listws', action='store_true',
    help='list worksheets')

  parser.add_argument('--download', action='store_true',
    help='download the relevent bits from the sheet')

  parser.add_argument('--generate', action='store_true',
    help='generate the configs')

  parser.add_argument('--dumpws', type=str, nargs=1, metavar=('<sheet>'),
    help='dump the contents of a worksheet, don\'t forget to quote the name!')
          
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
    generate()
    done_something = True

  if not done_something:
    print "Nothing to do, try " + sys.argv[0] + " --help"
