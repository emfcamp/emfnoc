#!/usr/bin/env python3
import os.path
import shelve
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from emfnoc import EmfNoc

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class NocSheetHelper:
    SHELF_VLANS = 'vlans'
    SHELF_LINKS = 'links'
    SHELF_USERS = 'users'
    SHELF_PORT_TYPES = 'port_types'
    SHELF_DEVICES = 'devices'

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

        self.download_sheet_to_shelf('Devices', self.SHELF_DEVICES, spr_client, spreadsheet)
        self.download_sheet_to_shelf('Port Types', self.SHELF_PORT_TYPES, spr_client, spreadsheet)
        self.download_sheet_to_shelf('Users', self.SHELF_USERS, spr_client, spreadsheet)
        self.download_sheet_to_shelf('Links', self.SHELF_LINKS, spr_client, spreadsheet)
        self.download_sheet_to_shelf('VLANs', self.SHELF_VLANS, spr_client, spreadsheet)

        print("done")

    def download_sheet_to_shelf(self, sheet_name, shelf_name, spr_client, spreadsheet):
        print("downloading %s" % sheet_name)
        data = self.get_worksheet_data(spr_client, spreadsheet, sheet_name)
        shelf = shelve.open('data/%s' % shelf_name)
        shelf["list"] = data
        shelf.close()

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

    def get_worksheet_data(self, spr_client, spreadsheet, sheet_name):
        sheets = self.get_worksheets(spr_client, spreadsheet)
        if sheet_name not in sheets:
            print("Worksheet " + sheet_name + " not found", file=sys.stderr)
            sys.exit(1)

        request = (
            spr_client.spreadsheets().values().get(spreadsheetId=spreadsheet, range=sheet_name)
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
        return shelve.open('data/%s' % name)["list"]
