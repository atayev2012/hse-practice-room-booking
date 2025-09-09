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
    MODULE_I_START = datetime.strptime(str(os.getenv("MODULE_I_START")),"%d.%m.%Y").date()
    MODULE_I_END = datetime.strptime(str(os.getenv("MODULE_I_END")),"%d.%m.%Y").date()
    MODULE_II_START = datetime.strptime(str(os.getenv("MODULE_II_START")), "%d.%m.%Y").date()
    MODULE_II_END = datetime.strptime(str(os.getenv("MODULE_II_END")),"%d.%m.%Y").date()
    MODULE_III_START = datetime.strptime(str(os.getenv("MODULE_III_START")),"%d.%m.%Y").date()
    MODULE_III_END = datetime.strptime(str(os.getenv("MODULE_III_END")),"%d.%m.%Y").date()
    MODULE_IV_START = datetime.strptime(str(os.getenv("MODULE_IV_START")),"%d.%m.%Y").date()
    MODULE_IV_END = datetime.strptime(str(os.getenv("MODULE_IV_END")),"%d.%m.%Y").date()

config = Config()

if __name__ == "__main__":
    print(f"MODULE 1 = START: {config.MODULE_I_START} | END: {config.MODULE_I_END}")
    print(f"MODULE 2 = START: {config.MODULE_II_START} | END: {config.MODULE_II_END}")
    print(f"MODULE 3 = START: {config.MODULE_III_START} | END: {config.MODULE_III_END}")
    print(f"MODULE 4 = START: {config.MODULE_IV_START} | END: {config.MODULE_IV_END}")
    # print(config.MODULE_I_END)
    # print(type(config.MODULE_III_START))