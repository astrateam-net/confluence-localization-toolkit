#!/usr/bin/env python3
"""
Locale and language code utilities for multi-language support.
Converts between locale codes (e.g., ru_RU) and API language codes (e.g., ru).
"""

import os
from typing import Tuple

# Default locale - can be overridden via TARGET_LANGUAGE env var
DEFAULT_LOCALE = "ru_RU"

# Mapping of locale codes to language names and API codes
LOCALE_INFO = {
    "ru_RU": {"name": "Russian (Russia)", "language": "ru", "country": "RU", "deepl": "RU", "google": "ru"},
    "de_DE": {"name": "German (Germany)", "language": "de", "country": "DE", "deepl": "DE", "google": "de"},
    "fr_FR": {"name": "French (France)", "language": "fr", "country": "FR", "deepl": "FR", "google": "fr"},
    "es_ES": {"name": "Spanish (Spain)", "language": "es", "country": "ES", "deepl": "ES", "google": "es"},
    "it_IT": {"name": "Italian (Italy)", "language": "it", "country": "IT", "deepl": "IT", "google": "it"},
    "pt_BR": {"name": "Portuguese (Brazil)", "language": "pt", "country": "BR", "deepl": "PT", "google": "pt"},
    "ja_JP": {"name": "Japanese (Japan)", "language": "ja", "country": "JP", "deepl": "JA", "google": "ja"},
    "ko_KR": {"name": "Korean (Korea)", "language": "ko", "country": "KR", "deepl": "KO", "google": "ko"},
    "zh_CN": {"name": "Chinese (Simplified)", "language": "zh", "country": "CN", "deepl": "ZH", "google": "zh-CN"},
    "zh_TW": {"name": "Chinese (Traditional)", "language": "zh", "country": "TW", "deepl": "ZH", "google": "zh-TW"},
    "pl_PL": {"name": "Polish (Poland)", "language": "pl", "country": "PL", "deepl": "PL", "google": "pl"},
    "nl_NL": {"name": "Dutch (Netherlands)", "language": "nl", "country": "NL", "deepl": "NL", "google": "nl"},
    "sv_SE": {"name": "Swedish (Sweden)", "language": "sv", "country": "SE", "deepl": "SV", "google": "sv"},
    "fi_FI": {"name": "Finnish (Finland)", "language": "fi", "country": "FI", "deepl": "FI", "google": "fi"},
    "uk_UA": {"name": "Ukrainian (Ukraine)", "language": "uk", "country": "UA", "deepl": "UK", "google": "uk"},
}


def get_target_locale() -> str:
    """Get target locale from environment variable, default to ru_RU."""
    return os.getenv('TARGET_LANGUAGE', DEFAULT_LOCALE).strip()


def locale_to_jira_format(locale: str = None) -> str:
    """
    Convert locale format from ru_RU (underscore) to ru-RU (hyphen) for Jira properties files.
    
    Jira uses hyphens in properties filenames (e.g., message_en-US.properties, message_de-DE.properties).
    
    Args:
        locale: Locale code (e.g., 'ru_RU'). If None, reads from TARGET_LANGUAGE env var.
    
    Returns:
        Locale in Jira format (e.g., 'ru-RU')
    """
    if locale is None:
        locale = get_target_locale()
    
    # Convert underscore to hyphen
    return locale.replace('_', '-')


def get_locale_info(locale: str = None) -> dict:
    """
    Get locale information including language codes for different APIs.
    
    Args:
        locale: Locale code (e.g., 'ru_RU'). If None, reads from TARGET_LANGUAGE env var.
    
    Returns:
        Dictionary with locale information:
        {
            'name': 'Russian (Russia)',
            'language': 'ru',
            'country': 'RU',
            'deepl': 'RU',
            'google': 'ru'
        }
    """
    if locale is None:
        locale = get_target_locale()
    
    if locale not in LOCALE_INFO:
        # Fallback: try to extract language from locale code (e.g., 'fr_FR' -> 'fr')
        parts = locale.split('_')
        lang_code = parts[0].lower()
        country_code = parts[1].upper() if len(parts) > 1 else lang_code.upper()
        
        # Create fallback info
        return {
            "name": f"{lang_code.title()} ({country_code})",
            "language": lang_code,
            "country": country_code,
            "deepl": lang_code.upper(),
            "google": lang_code
        }
    
    return LOCALE_INFO[locale]


def get_deepl_code(locale: str = None) -> str:
    """Get DeepL language code for locale (e.g., 'RU' for 'ru_RU')."""
    return get_locale_info(locale)['deepl']


def get_google_code(locale: str = None) -> str:
    """Get Google Cloud Translation language code for locale (e.g., 'ru' for 'ru_RU')."""
    return get_locale_info(locale)['google']


def get_language_name(locale: str = None) -> str:
    """Get human-readable language name (e.g., 'Russian (Russia)')."""
    return get_locale_info(locale)['name']


def get_language_and_country(locale: str = None) -> Tuple[str, str]:
    """Get language and country codes as tuple (e.g., ('ru', 'RU'))."""
    info = get_locale_info(locale)
    return (info['language'], info['country'])

