import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_REPORT_CHAT_ID = os.getenv("TELEGRAM_REPORT_CHAT_ID")
    DB_URL = os.getenv("DB_URL")
    GOOGLE_TABLE_URL=os.getenv("GOOGLE_TABLE_URL")
    GOOGLE_CREDENTIALS_PATH=os.getenv("GOOGLE_CREDENTIALS_PATH")

config = Config()
