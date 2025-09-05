import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv("TOKEN")
    REPORT_CHAT_ID = os.getenv("REPORT_CHAT_ID")
    DB_URL = os.getenv("DB_URL")

config = Config()