#!/usr/bin/env python

import gdata.spreadsheets.client
#import gdata.spreadsheet.text_db
import getpass, os, sys
import pprint

def login(source, config):
  print "Connecting to spreadsheet"

  if config.has_option('gdata', 'oauth_token'):
    token = gdata.gauth.token_from_blob(config.get('gdata', 'oauth_token'))
  else:
    SCOPES = ['https://spreadsheets.google.com/feeds/']

    token = gdata.gauth.OAuth2Token(
      client_id=config.get('gdata', 'oauth_client_id'),
      client_secret=config.get('gdata', 'oauth_client_secret'),
      scope=' '.join(SCOPES),
      user_agent=source)

    print "Visit this URL and get the token:"
    print
    print token.generate_authorize_url()
    print
    auth_code = raw_input("Enter the code: ")

    try:
      token.get_access_token(auth_code)
    except gdata.gauth.OAuth2AccessTokenError as err:
      print "Token failure: " + err.error_message
      raise

    print
    print "Add this to /etc/emf-gdata.conf:"
    print
    print "oauth_token=" + gdata.gauth.token_to_blob(token)
    print

    exit(1)

  spr_client = gdata.spreadsheets.client.SpreadsheetsClient(source = source)

  spr_client.ssl = True

  spr_client = token.authorize(spr_client)

  return spr_client

def get_worksheets(spr_client, spreadsheet):
  worksheets = spr_client.get_worksheets(spreadsheet, None)
  out = {}
  for e in worksheets.entry:
    out[e.title.text] = e.id.text.rsplit('/', 1)[1]
#  pprint.pprint(out)
  return out

def get_worksheet_data(spr_client, spreadsheet, wks):
  sheets = get_worksheets(spr_client, spreadsheet)

  if wks not in sheets:
    print "worksheet " + wks + " not found"
    exit()

  wks_key = sheets[wks]
  feed = spr_client.get_cells(spreadsheet, wks_key)

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
        out.append(r)
        if entry.content.text.strip() == "!end":
          break
      r = {}
      cur_row = row

    if entry.content.text != None and entry.content.text != "":
      r[col_keys[col]] = entry.content.text

#  print len(out)
  return out
