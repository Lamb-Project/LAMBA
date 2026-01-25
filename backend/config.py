import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default activity language (en, es, ca, eu)
# Used when teacher creates an activity without specifying a language
DEFAULT_ACTIVITY_LANGUAGE = os.getenv('DEFAULT_ACTIVITY_LANGUAGE', 'en')

# Validate the default language
if DEFAULT_ACTIVITY_LANGUAGE not in ['en', 'es', 'ca', 'eu']:
    DEFAULT_ACTIVITY_LANGUAGE = 'en'
