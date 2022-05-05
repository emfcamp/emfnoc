#!/usr/bin/env python3

import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# keep backwards compatibility with older scripts passing the login info
def login(*args, **kwargs):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    Taken from https://developers.google.com/sheets/api/quickstart/python
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(os.path.expanduser("~/.config/emf/token.json")):
        creds = Credentials.from_authorized_user_file(
            os.path.expanduser("~/.config/emf/token.json"), SCOPES
        )
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.expanduser("~/.config/emf/credentials.json"), SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(os.path.expanduser("~/.config/emf/token.json"), "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)
        return service
    except HttpError as err:
        print(err)


def get_worksheets(spr_client, spreadsheet):
    request = spr_client.spreadsheets().get(spreadsheetId=spreadsheet)
    response = request.execute()
    worksheets = []
    for k in response["sheets"]:
        worksheets.append((k["properties"]["title"]))
    return worksheets


def get_worksheet_data(spr_client, spreadsheet, wks):
    sheets = get_worksheets(spr_client, spreadsheet)
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
