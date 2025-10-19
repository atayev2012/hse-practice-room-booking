import os
from dotenv import load_dotenv, find_dotenv, set_key
from datetime import date, datetime

class Config:
    def __init__(self):
        self.dotenv_file = find_dotenv()
        load_dotenv(self.dotenv_file, override=True)

        # Telegram Bot data
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        self.TELEGRAM_REPORT_CHAT_ID = os.getenv("TELEGRAM_REPORT_CHAT_ID")

        # Database URL
        self.DB_URL = os.getenv("DB_URL")

        # Google Spreadsheet API data
        self.GOOGLE_TABLE_URL = os.getenv("GOOGLE_TABLE_URL")
        self.GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")

        # Schedule variables
        self.DAYS_TO_SHOW = int(os.getenv("DAYS_TO_SHOW")) # for how many days ahead to load schedule
        self.TIMEZONE = int(os.getenv("TIMEZONE")) # desired location timezone
        self.SCHEDULE_UPDATE_INTERVAL = int(os.getenv("SCHEDULE_UPDATE_INTERVAL")) # update schedule every ??? minutes
        self.UPPER_WEEK_START_DATE = datetime.strptime(str(os.getenv("UPPER_WEEK_START_DATE")),"%d.%m.%Y").date() # current module upper week start date

    # update specific field in Config() object and .env file
    def update_attr(self, attribute_name: str, new_value: str):
        if hasattr(self, attribute_name):
            set_key(self.dotenv_file, attribute_name, new_value)
            self.__init__()

# creating sample of config
config = Config()

if __name__ == "__main__":
    pass