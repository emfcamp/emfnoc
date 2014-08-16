#!/usr/bin/env python

import gdata.spreadsheet.service
import gdata.spreadsheet.text_db
import getpass, os, sys

def login(source, config):
  print "Connecting to spreadsheet"
#  spr_client.email = email
#  spr_client.password = password

  try:
    email = config.get('gdata', 'email')
  except:
    email = ""

  try:
    password = config.get('gdata', 'password')
  except:
    password = ""

  if email == "":
    email = raw_input("Please enter email for Google account: ")

  if password == "":
    password = getpass.getpass("Please enter the password for " + email + ": ")

  spr_client = gdata.spreadsheet.service.SpreadsheetsService(email = email,
    password = password, source = source)

  spr_client.ssl = True

  spr_client.ProgrammaticLogin()
        
  return spr_client

def get_worksheets(spr_client, spreadsheet):
  worksheets = spr_client.GetWorksheetsFeed(key=spreadsheet)
  out = {}
  for e in worksheets.entry:
    out[e.title.text] = e.id.text.rsplit('/', 1)[1]
  return out

def get_worksheet_data(spr_client, spreadsheet, wks):
  sheets = get_worksheets(spr_client, spreadsheet)

  if wks not in sheets:
    print "worksheet " + wks + " not found"
    exit()

  wks_key = sheets[wks]
  feed = spr_client.GetCellsFeed(spreadsheet, wks_key)

  col_keys = {}
  out = []
  r = {}
  cur_row = 1
  for i, entry in enumerate(feed.entry):
    row = int(entry.cell.row)
    col = int(entry.cell.col)

    if row == 1:
      # assemble keys
      col_keys[col] = entry.content.text
      
    if row != cur_row:
      if cur_row > 1:
#        print row
#        print r
        out.append(r)
      if entry.content.text == "!end":
        break
      r = {}
      cur_row = row

    if entry.content.text != None and entry.content.text != "":
      r[col_keys[col]] = entry.content.text

#  print len(out)
  return out
