import os
from dotenv import load_dotenv
from datetime import date, datetime

load_dotenv()

class Config:
    # Telegram Bot data
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_REPORT_CHAT_ID = os.getenv("TELEGRAM_REPORT_CHAT_ID")

    # Database URL
    DB_URL = os.getenv("DB_URL")

    # Google Spreadsheet API data
    GOOGLE_TABLE_URL = os.getenv("GOOGLE_TABLE_URL")
    GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")

    # Education modules start and end dates
    MODULES = {
        "1": {
            "start": datetime.strptime(str(os.getenv("MODULE_I_START")),"%d.%m.%Y").date(),
            "end": datetime.strptime(str(os.getenv("MODULE_I_END")),"%d.%m.%Y").date()
        },
        "2": {
            "start": datetime.strptime(str(os.getenv("MODULE_II_START")), "%d.%m.%Y").date(),
            "end": datetime.strptime(str(os.getenv("MODULE_II_END")),"%d.%m.%Y").date()
        },
        "3": {
            "start": datetime.strptime(str(os.getenv("MODULE_III_START")),"%d.%m.%Y").date(),
            "end": datetime.strptime(str(os.getenv("MODULE_III_END")),"%d.%m.%Y").date()
        },
        "4": {
            "start": datetime.strptime(str(os.getenv("MODULE_IV_START")),"%d.%m.%Y").date(),
            "end": datetime.strptime(str(os.getenv("MODULE_IV_END")),"%d.%m.%Y").date()
        }
    }

config = Config()

if __name__ == "__main__":
    print(f"MODULE 1 = START: {config.MODULES['1']['start']} | END: {config.MODULES['1']['end']}")

    # print(config.MODULE_I_END)
    # print(type(config.MODULE_III_START))