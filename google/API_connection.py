import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import config

# Loading credentials
creds = ServiceAccountCredentials.from_json_keyfile_name(
    filename=config.GOOGLE_CREDENTIALS_PATH,
    scopes=["https://spreadsheets.google.com/feeds"]
)

# Authorizing and creating client
client = gspread.authorize(creds)

# Opening the table
table = client.open_by_url(config.GOOGLE_TABLE_URL)
