import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default language
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

# Available languages
LANGUAGES = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "ru": "Русский",
    "ar": "العربية",
    "hi": "हिन्दी",
    "zh": "中文",
    "bn": "বাংলা"
}

# Language data cache
_language_data = {}

def load_language_file(lang_code):
    """Load language data from file"""
    try:
        # Get the directory of the current file
        current_dir = Path(__file__).parent
        
        # Construct path to language file
        lang_file = current_dir / f"{lang_code}.json"
        
        # If language file doesn't exist, use English
        if not lang_file.exists():
            if lang_code != "en":
                logger.warning(f"Language file for {lang_code} not found, using English")
                return load_language_file("en")
            else:
                logger.error("English language file not found")
                return {}
        
        # Load language data from file
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    except Exception as e:
        logger.error(f"Error loading language file: {e}")
        return {}

def get_language_data(lang_code=None):
    """Get language data for the specified language code"""
    global _language_data
    
    # Use default language if none specified
    if not lang_code:
        lang_code = DEFAULT_LANGUAGE
    
    # Normalize language code
    lang_code = lang_code.lower()
    
    # Load language data if not cached
    if lang_code not in _language_data:
        _language_data[lang_code] = load_language_file(lang_code)
    
    return _language_data[lang_code]

def get_text(key, lang_code=None, **kwargs):
    """Get text for the specified key in the specified language"""
    # Get language data
    lang_data = get_language_data(lang_code)
    
    # Get text for key
    text = lang_data.get(key, key)
    
    # Format text with kwargs
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.error(f"Error formatting text: {e}")
    
    return text