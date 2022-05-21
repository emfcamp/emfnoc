#!/usr/bin/env python

# apt install python-configparser python-asterisk

import configparser, argparse, ConfigParser
import Asterisk, Asterisk.Manager, Asterisk.Config
import sys, os, getopt, inspect
from nocsheet import login, get_worksheets, get_worksheet_data

parser = argparse.ArgumentParser(description='Generate cisco IOS config files from gdocs.')

parser.add_argument('--icinga', action='store_true',
                    help='generate an icinga config')

parser.add_argument('--ping', action='store_true',
                    help='Ping the phones and report missing ones')

parser.add_argument('--sipconf', type=str, nargs=1, metavar=('<sip.conf>'),
                    help='path to sip.conf')

args = parser.parse_args()


sipconfig = configparser.ConfigParser(strict=False)

sipconf = '/etc/asterisk/sip.conf'

if args.sipconf:
  sipconf = args.sipconf[0]

sipconfig.read(sipconf)

config = ConfigParser.ConfigParser()
if not config.read("/etc/emf-gdata.conf"):
  print "Warning: config file /etc/emf-gdata.conf could not be found or read"

spreadsheet = config.get('gdata', 'noc_combined')
spr_client = login("emfcamp Cisco config generator", config, False)

switches = get_worksheet_data(spr_client, spreadsheet, "Switches")
returned_switches = {}

for sw in switches:
  if 'Teardown' in sw and sw['Teardown'] == "returned":
    returned_switches[sw['Hostname']] = 1

phones = get_worksheet_data(spr_client, spreadsheet, "Phones")

id_to_switch = {}

for line in phones:
  if 'Phone-Name' in line:
    id_to_switch[line['Phone-Name']] = {"switch": line['Switch']}

def munge_id(name):
  if name.startswith("\""):
    name = name[1:]
  if name.endswith('"'):
    name = name[:-1]
  return name

peer_to_id = {}

for k in sipconfig.keys():
  if k.isdigit():
    label = k
    if sipconfig[k]["username"] != k:
      label = k + "/" + sipconfig[k]["username"]
    id = sipconfig[k]['callerid']
    peer_to_id[k] = sipconfig[k]['callerid']
    id = munge_id(id)
    if id not in id_to_switch:
      print "# phone,", id, "missing in the sheet?"

# py-asterisk action SipShowPeer 1111
manager = Asterisk.Manager.Manager(*Asterisk.Config.Config().get_connection())
method = "SipShowPeer".lower()

#print inspect.getmembers(manager)

method_dict = dict(\
        [ (k.lower(), v) for (k, v) in inspect.getmembers(manager) \
          if inspect.ismethod(v) ])
#print method_dict

method = method_dict[method]

do_icinga = args.icinga

print "#", returned_switches

for k in peer_to_id.keys():
  pos_args = [k]
  kw_args = {}
  ret = method(*pos_args, **kw_args)
  if ret['Address-IP'] == "(null)":
    print "# %6s %18s %10s %s" %  (k, peer_to_id[k], ret['Address-IP'], ret['SIP-Useragent'])
  else:
    if do_icinga:
      bits = {}
      id = munge_id(peer_to_id[k])
      if id in id_to_switch:
        bits = id_to_switch[id]
      name = id
      if " " in name:
        name = name.replace(" ", "_")
#      print "#", bits, k, id, name
      if "switch" not in bits:
        print "# no switch for %s" % (name)
        continue
      if bits["switch"] in returned_switches:
        print "# phone %s is on a returned switch (%s)" % (name, bits["switch"])
        continue
      print "define host {"
      print "  use generic-host"
      print "  host_name %s" % (name + "-phone")
 #     print "  alias DOCKLANDS.emf.camp
      print "  address %s" % (ret['Address-IP'],)
      if "switch" in bits:
        print "  parents %s" % (bits["switch"],)
      print "}"
    elif args.ping:
      addr = ret['Address-IP']
      p = os.popen("ping -c 2 %s" % (addr,))
      out = p.read()
      pret = p.close()
      if pret != None:
#        print out, ret
        print "DOWN: %6s %18s %10s %s" %  (k, peer_to_id[k], ret['Address-IP'], ret['SIP-Useragent'])
    else:
      print "%6s %18s %10s %s" %  (k, peer_to_id[k], ret['Address-IP'], ret['SIP-Useragent'])
