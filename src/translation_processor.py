#!/usr/bin/env python3
"""
Translation processor for Confluence plugin translations.
Supports multiple target languages via TARGET_LANGUAGE env var (default: ru_RU).
Processes in chunks, preserves HTML tags and placeholders using DeepL/Google Cloud Translation APIs.
"""

import json
import re
import sys
import os
from typing import Dict, Tuple
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from project root (parent of src/)
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv is optional, can use env vars directly

# Translation APIs - DeepL or Google Cloud Translation
try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False

# Google Cloud Translation API support - both v2 and v3
try:
    from google.cloud import translate_v2
    GOOGLE_TRANSLATE_V2_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_V2_AVAILABLE = False

try:
    from google.cloud import translate_v3
    GOOGLE_TRANSLATE_V3_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_V3_AVAILABLE = False

GOOGLE_TRANSLATE_AVAILABLE = GOOGLE_TRANSLATE_V2_AVAILABLE or GOOGLE_TRANSLATE_V3_AVAILABLE

if not DEEPL_AVAILABLE and not GOOGLE_TRANSLATE_AVAILABLE:
    print("ERROR: No translation library installed. Install with:", file=sys.stderr)
    print("  pip install deepl  (for DeepL)", file=sys.stderr)
    print("  OR", file=sys.stderr)
    print("  pip install google-cloud-translate  (for Google Cloud Translation)", file=sys.stderr)
    sys.exit(1)

# Import locale utilities
try:
    from locale_utils import get_target_locale, get_deepl_code, get_google_code
except ImportError:
    # Fallback if locale_utils not available
    def get_target_locale():
        return os.getenv('TARGET_LANGUAGE', 'ru_RU').strip()
    def get_deepl_code(locale=None):
        if locale is None:
            locale = get_target_locale()
        return locale.split('_')[0].upper() if '_' in locale else locale.upper()
    def get_google_code(locale=None):
        if locale is None:
            locale = get_target_locale()
        return locale.split('_')[0].lower() if '_' in locale else locale.lower()


class TranslationProcessor:
    """
    Core translation processor class.
    Handles translation via DeepL or Google Cloud Translation API.
    Used by translate_group.py for database-based workflow.
    """
    def __init__(self, source_file: str = None, chunk_size: int = 500):
        """
        Initialize translation processor.
        
        Args:
            source_file: Optional source file (not used in database workflow)
            chunk_size: Optional chunk size (not used in database workflow)
        """
        pass
    
    def convert_to_xml_for_deepl(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Convert text to XML format for DeepL translation.
        Converts ANY placeholders {0}, {1}, {page}, {task}, etc. to XML tags.
        Returns XML text and mapping to restore placeholders.
        """
        placeholders = {}
        
        # Convert ANY placeholder {anything} to XML placeholder tags
        def replace_placeholder(match):
            placeholder_content = match.group(1)
            # Use placeholder content as ID (sanitize for XML if needed)
            # Replace any special chars that might break XML
            safe_id = placeholder_content.replace(' ', '_').replace('.', '_')
            xml_tag = f'<ph id="{safe_id}"/>'
            placeholders[xml_tag] = match.group(0)  # Store mapping: XML tag -> original {content}
            return xml_tag
        
        # Replace ANY {content} with XML tags (not just numbers)
        xml_text = re.sub(r'\{([^}]+)\}', replace_placeholder, text)
        
        return xml_text, placeholders
    
    def restore_from_xml(self, xml_text: str, placeholders: Dict[str, str]) -> str:
        """Restore placeholders from XML format after DeepL translation."""
        # Replace XML placeholder tags back to original {0}, {1} format
        for xml_tag, original_placeholder in placeholders.items():
            xml_text = xml_text.replace(xml_tag, original_placeholder)
        return xml_text
    
    def translate_with_google(self, text: str, translator=None,
                             credentials_path: str = None, api_version: str = None,
                             target_locale: str = None) -> str:
        """
        Translate using Google Cloud Translation API (v2 or v3).
        Preserves HTML tags and placeholders {0}, {1}, etc.
        
        Args:
            text: Text to translate
            translator: Translator client instance (optional)
            credentials_path: Path to service account JSON file
            api_version: API version to use ('v2' or 'v3'), defaults to env var or 'v3'
        """
        # Determine which API version to use
        if not api_version:
            api_version = os.getenv('GOOGLE_TRANSLATE_API_VERSION', 'v3')
        
        # Normalize API version (handle 'v2', 'v3', '2', '3')
        if api_version:
            api_version = api_version.lower().replace('v', '').strip()
        if not api_version or api_version not in ['2', '3']:
            # Default to v3 if invalid, fallback to v2 if v3 not available
            if GOOGLE_TRANSLATE_V3_AVAILABLE:
                api_version = '3'
            elif GOOGLE_TRANSLATE_V2_AVAILABLE:
                api_version = '2'
            else:
                raise ValueError("Neither Google Cloud Translation v2 nor v3 is available")
        
        # Initialize translator if not provided
        if translator is None:
            if not credentials_path:
                credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            
            if api_version == '3':
                if not GOOGLE_TRANSLATE_V3_AVAILABLE:
                    raise ValueError("Google Cloud Translation v3 not available. Install: pip install google-cloud-translate")
                
                # v3 uses TranslationServiceClient
                from google.cloud.translate_v3 import TranslationServiceClient
                from google.oauth2 import service_account
                
                if credentials_path and os.path.exists(credentials_path):
                    # Load credentials and create client
                    credentials = service_account.Credentials.from_service_account_file(credentials_path)
                    translator = TranslationServiceClient(credentials=credentials)
                else:
                    # Use default credentials
                    translator = TranslationServiceClient()
            else:  # v2
                if not GOOGLE_TRANSLATE_V2_AVAILABLE:
                    raise ValueError("Google Cloud Translation v2 not available. Install: pip install google-cloud-translate")
                
                # v2 uses simple Client
                if credentials_path:
                    translator = translate_v2.Client.from_service_account_json(credentials_path)
                else:
                    translator = translate_v2.Client()
        
        # Check if text has HTML tags or placeholders
        has_html = bool(re.search(r'<[^>]+>', text))
        has_placeholders = bool(re.search(r'\{[^}]+\}', text))
        
        # Google Cloud Translation preserves HTML tags automatically
        # For placeholders, we need to protect them by converting to HTML entities temporarily
        # or use HTML format which preserves {0} placeholders
        if has_placeholders:
            # Convert {0}, {1} to temporary HTML-like tags that Google won't translate
            xml_text, placeholder_map = self.convert_to_xml_for_deepl(text)
            text_to_translate = xml_text
        else:
            text_to_translate = text
            placeholder_map = {}
        
        try:
            # Google Cloud Translation API - different methods for v2 vs v3
            if api_version == '3':
                # v3 API uses TranslationServiceClient
                from google.cloud.translate_v3 import TranslateTextRequest
                
                # Get project ID from env var or credentials file
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
                if not project_id:
                    # Try to get project ID from credentials file
                    import json
                    creds_file = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                    if creds_file and os.path.exists(creds_file):
                        with open(creds_file) as f:
                            creds = json.load(f)
                            project_id = creds.get('project_id')
                
                if not project_id:
                    raise ValueError(
                        "Google Cloud project ID required for v3. Set GOOGLE_CLOUD_PROJECT env var "
                        "or include project_id in credentials JSON file."
                    )
                
                parent = f"projects/{project_id}/locations/global"
                target_lang = get_google_code(target_locale)
                request = TranslateTextRequest(
                    parent=parent,
                    contents=[text_to_translate],
                    source_language_code='en',
                    target_language_code=target_lang,
                    mime_type='text/html' if (has_html or has_placeholders) else 'text/plain'
                )
                response = translator.translate_text(request=request)
                translated = response.translations[0].translated_text
            else:
                # v2 API - simpler Client interface
                if not hasattr(translator, 'translate'):
                    raise ValueError("v2 API not properly initialized. Check credentials.")
                
                target_lang = get_google_code(target_locale)
                result = translator.translate(
                    text_to_translate,
                    source_language='en',
                    target_language=target_lang,
                    format_='html' if (has_html or has_placeholders) else 'text'
                )
                translated = result['translatedText']
            
            # Restore placeholders from XML format
            if placeholder_map:
                translated = self.restore_from_xml(translated, placeholder_map)
            
            return translated
            
        except Exception as e:
            error_msg = str(e)
            print(f"Google Cloud Translation API (v{api_version}) error: {error_msg}", file=sys.stderr)
            raise
    
    def translate_with_deepl(self, text: str, translator: deepl.Translator = None,
                             api_key: str = None, target_locale: str = None) -> str:
        """
        Translate using DeepL API with native HTML/XML tag handling.
        Uses DeepL's built-in tag handling to preserve HTML tags and placeholders.
        """
        if translator is None:
            if not api_key:
                api_key = os.getenv('DEEPL_API_KEY')
                if not api_key:
                    raise ValueError(
                        "DeepL API key required. Set DEEPL_API_KEY in .env file or "
                        "environment variable, or pass --api-key parameter."
                    )
            # DeepL library auto-detects free vs paid endpoint based on API key format
            translator = deepl.Translator(api_key)
        
        # Check if text has HTML tags or placeholders
        has_html = bool(re.search(r'<[^>]+>', text))
        has_placeholders = bool(re.search(r'\{[^}]+\}', text))
        
        # Convert placeholders to XML tags for DeepL
        if has_placeholders:
            xml_text, placeholder_map = self.convert_to_xml_for_deepl(text)
            text_to_translate = xml_text
        else:
            text_to_translate = text
            placeholder_map = {}
        
        try:
            # Use DeepL's native HTML/XML tag handling
            if has_html or has_placeholders:
                # Use XML tag handling to preserve both HTML tags and placeholder XML tags
                # ignore_tags=['ph'] tells DeepL to not translate the placeholder tags
                target_lang = get_deepl_code(target_locale)
                result = translator.translate_text(
                    text_to_translate,
                    source_lang="EN",
                    target_lang=target_lang,
                    tag_handling="xml",
                    ignore_tags=["ph"],  # Ignore placeholder tags
                    preserve_formatting=True,
                    formality="default"
                )
            else:
                # Plain text, no special handling needed
                target_lang = get_deepl_code(target_locale)
                result = translator.translate_text(
                    text_to_translate,
                    source_lang="EN",
                    target_lang=target_lang,
                    preserve_formatting=True,
                    formality="default"
                )
            
            translated = result.text
            
            # Restore placeholders from XML format
            if placeholder_map:
                translated = self.restore_from_xml(translated, placeholder_map)
            
            return translated
            
        except deepl.exceptions.DeepLException as e:
            print(f"DeepL API error: {e}", file=sys.stderr)
            raise
    
    def translate_text(self, text: str, translator=None, api_key: str = None,
                      service: str = None, credentials_path: str = None,
                      api_version: str = None, target_locale: str = None) -> str:
        """
        Translate text with automatic HTML/placeholder preservation.
        
        Args:
            text: Text to translate
            translator: Translator instance (optional, will create if needed)
            api_key: API key for DeepL (if using DeepL)
            service: Translation service to use ('deepl' or 'google'), auto-detects if None
            credentials_path: Path to Google service account JSON (if using Google)
            api_version: Google API version ('v2' or 'v3'), defaults to env var or 'v3'
        
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        # Auto-detect service if not specified
        if not service:
            # Check environment variables to determine which service to use
            if os.getenv('DEEPL_API_KEY'):
                service = 'deepl'
            elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or GOOGLE_TRANSLATE_AVAILABLE:
                service = 'google'
            else:
                # Default to DeepL if available, otherwise Google
                service = 'deepl' if DEEPL_AVAILABLE else 'google'
        
        try:
            # Use target locale from parameter or environment variable
            if target_locale is None:
                target_locale = get_target_locale()
            
            if service == 'deepl' or (service is None and DEEPL_AVAILABLE):
                if not DEEPL_AVAILABLE:
                    raise ValueError("DeepL library not installed. Install with: pip install deepl")
                translated = self.translate_with_deepl(text, translator, api_key, target_locale)
            elif service == 'google':
                if not GOOGLE_TRANSLATE_AVAILABLE:
                    raise ValueError("Google Cloud Translation library not installed. Install with: pip install google-cloud-translate")
                translated = self.translate_with_google(text, translator, credentials_path, api_version, target_locale)
            else:
                raise ValueError(f"Unknown translation service: {service}")
            
            return translated
            
        except Exception as e:
            print(f"Translation error for '{text[:50]}...': {e}", file=sys.stderr)
            return text  # Return original on error
    

