#!/usr/bin/env python3
import configparser
import os.path
import pathlib
import shelve
import sys
from pprint import pprint

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from emfnoc import EmfNoc

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class NocSheetHelper:

    def add_arguments(self, parser):
        parser.add_argument("--listws", action="store_true", help="list worksheets")

        parser.add_argument(
            "--dumpws",
            type=str,
            nargs=1,
            metavar=("<sheet>"),
            help="dump the contents of a worksheet, don't forget to quote the name!",
        )

        parser.add_argument(
            "--download",
            action="store_true",
            help="download the relevent bits from the sheet",
        )

    def process_arguments(self, args):
        if not (args.listws or args.download or args.dumpws):
            return False

        config = EmfNoc.load_config()

        spr_client = self.login(config)

        spreadsheet = config.get("gdata", "noc_combined")

        if args.listws:
            for ws in self.get_worksheets(spr_client, spreadsheet):
                print(ws)
            done_something = True

        if args.download:
            self.download(spr_client, spreadsheet)
            done_something = True

        if args.dumpws:
            self.dump_worksheet(spr_client, spreadsheet, args.dumpws[0])
            done_something = True

        return done_something

    def download(self, spr_client, spreadsheet):
        if not os.path.exists("data"):
            os.mkdir("data")

        print("downloading switches")
        switches = self.get_worksheet_data(spr_client, spreadsheet, "Switches")

        sws = shelve.open("data/switches")
        sws["list"] = switches
        sws.close()

        print("downloading port types")
        port_types = self.get_worksheet_data(spr_client, spreadsheet, "Port Types")

        pt = shelve.open("data/port_types")
        pt["list"] = port_types
        pt.close()

        print("downloading users")
        users = self.get_worksheet_data(spr_client, spreadsheet, "Users")
        for user in list(users):
            if not "IOS password" in user:
                users.remove(user)

        u = shelve.open("data/users")
        u["list"] = users
        u.close()

        print("downloading Addressing")
        addressing = self.get_worksheet_data(spr_client, spreadsheet, "Addressing")

        v4 = shelve.open("data/addressing")
        v4["list"] = addressing
        v4.close()

        print("downloading Links")
        links = self.get_worksheet_data(spr_client, spreadsheet, "Links")

        l = shelve.open("data/links")
        l["list"] = links
        l.close()

        print("done")

    def dump_worksheet(self, spr_client, spreadsheet, wks):
        print(self.get_worksheet_data(spr_client, spreadsheet, wks))

    def login(self, config):
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        token_storage_file = os.path.expanduser("~/.emfnoc-gdata-token.json")
        if os.path.exists(token_storage_file):
            creds = Credentials.from_authorized_user_file(
                token_storage_file, SCOPES
            )

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                print("Refresh!")
            else:
                client_config = {
                    'installed': {
                        'client_id': config.get('gdata', 'oauth_client_id'),
                        'client_secret': config.get('gdata', 'oauth_client_secret'),
                        'redirect_uris': ['http://localhost', 'urn:ietf:wg:oauth:2.0:oob'],
                        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                        'token_uri': 'https://accounts.google.com/o/oauth2/token'
                    }
                }
                # flow = InstalledAppFlow.from_client_secrets_file(
                #     os.path.expanduser("~/.config/emf/credentials.json"), SCOPES
                # )
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_storage_file, "w") as token:
                token.write(creds.to_json())

        try:
            service = build("sheets", "v4", credentials=creds)
            return service
        except HttpError as err:
            print(err)

    def get_worksheets(self, spr_client, spreadsheet):
        request = spr_client.spreadsheets().get(spreadsheetId=spreadsheet)
        response = request.execute()
        worksheets = []
        for k in response["sheets"]:
            worksheets.append((k["properties"]["title"]))
        return worksheets

    def get_worksheet_data(self, spr_client, spreadsheet, wks):
        sheets = self.get_worksheets(spr_client, spreadsheet)
        if wks not in sheets:
            print("worksheet " + wks + " not found")
            exit()

        request = (
            spr_client.spreadsheets().values().get(spreadsheetId=spreadsheet, range=wks)
        )
        response = request.execute()
        col_keys = {}
        out = []

        for row, entry in enumerate(response["values"]):
            r = {}
            if row == 0:
                for col, col_val in enumerate(entry):
                    col_keys[col] = col_val
            else:
                for col, col_val in enumerate(entry):
                    if col_val == "!end":
                        return out
                    if col_val != None and col_val != "":
                        r[col_keys[col]] = col_val
                if r:
                    out.append(r)
        return out

    def get_shelf(self, name):
        return shelve.open("data/switches")["list"]
