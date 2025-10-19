import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import config

class GoogleAPIConnection:
    def __init__(self):
        self.__credentials = None
        self.__client = None
        self.spreadsheet = None

        self.__load_credentials()
        self.__establish_connection()
        self.__connect_to_spreadsheet()

    # Read credentials for Google API
    def __load_credentials(self):
        self.__credentials = ServiceAccountCredentials.from_json_keyfile_name(
            filename=config.GOOGLE_CREDENTIALS_PATH,
            scopes=["https://spreadsheets.google.com/feeds"]
        )

    # Authorize to Google API
    def __establish_connection(self):
        self.__client = gspread.authorize(self.__credentials)

    # Connect to spreadsheet
    def __connect_to_spreadsheet(self):
        self.spreadsheet = self.__client.open_by_url(config.GOOGLE_TABLE_URL)

    # Reinitialize connection
    def update_connection(self):
        self.__init__()

    def __repr__(self):
        return f"Spreadsheet name: \"{self.spreadsheet.title}\" | URL: \"{self.spreadsheet.url}\""


# initiate connection sample
conn = GoogleAPIConnection()
