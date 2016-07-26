#!/usr/bin/python

# EMF roundup user generator

import ipaddr, time, os, sys, ConfigParser

from nocsheet import login, get_worksheets, get_worksheet_data

config = ConfigParser.ConfigParser()
if not config.read("/etc/emf-gdata.conf"):
  print "Warning: config file /etc/emf-gdata.conf could not be found or read"

spreadsheet = config.get('gdata', 'noc_combined')

spr_client = login("emfcamp Roundup config generator", config)

print "downloading Users"
users = get_worksheet_data(spr_client, spreadsheet, "Users")

for user in users:
  if "uid" in user and user["uid"].isdigit():
    print "create user username=" + user["Username"] + " address=" + user["E-mail"] + " roles=Admin"
