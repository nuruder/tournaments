import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
TOPIC_ID = int(os.getenv("TOPIC_ID", "0"))

PARSER_URL = "https://padelteams.pt/infoclub/competitions?k=YmlkPTgy"
BASE_URL = "https://padelteams.pt"
CHECK_INTERVAL_MINUTES = 60
DB_PATH = "tournaments.db"
VENUES_FILE = "venues.txt"
