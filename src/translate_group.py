#!/usr/bin/env python3
"""
Translate group keys from database using DeepL API.
Works with group-based database tables.
Handles DeepL rate limiting and usage checking.
"""

import sys
import os
import time
import logging
from datetime import datetime
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False
    print("ERROR: deepl library not installed. Install with: pip install deepl", file=sys.stderr)
    sys.exit(1)

from db_group_manager import GroupDBManager
from translation_processor import TranslationProcessor

try:
    from locale_utils import get_target_locale
except ImportError:
    def get_target_locale():
        return os.getenv('TARGET_LANGUAGE', 'ru_RU').strip()


def setup_logging(group_key: str) -> logging.Logger:
    """Set up logging to both file and console."""
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"translate_{group_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create logger
    logger = logging.getLogger(f'translate_{group_key}')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler (less verbose)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger


class GroupTranslator:
    """Translates group keys from database using DeepL with rate limiting handling."""
    
    def __init__(self, db_path: str = "db/translations.db", logger: logging.Logger = None):
        self.db = GroupDBManager(db_path)
        self.processor = TranslationProcessor("", chunk_size=500)
        self.logger = logger or logging.getLogger('translate_group')
    
    def translate_group(self, group_key: str, api_key: str = None, service: str = None, 
                        google_api_version: str = None, target_locale: str = None):
        """
        Translate pending and error keys for a group.
        Automatically continues from keys with 'pending' or 'error' status.
        
        Args:
            group_key: Group key to translate (e.g., 'linchpin-suite')
            api_key: API key (DeepL) or credentials path (Google) - optional, reads from env
            service: Translation service to use ('deepl' or 'google'), auto-detects if None
            google_api_version: Google API version to use ('v2' or 'v3'), defaults to env var or 'v3'
            target_locale: Target locale code (e.g., 'ru_RU', 'de_DE'). Defaults to TARGET_LANGUAGE env var or 'ru_RU'
        """
        # Determine which service to use
        translation_service = service or os.getenv('TRANSLATION_SERVICE', 'auto')
        google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # If api_key is provided explicitly, prefer DeepL
        if translation_service == 'google' or (translation_service == 'auto' and google_creds and not api_key):
            # Using Google Cloud Translation
            self.logger.info("Using Google Cloud Translation API")
            if not google_creds:
                raise ValueError(
                    "Google Cloud Translation credentials required. Set GOOGLE_APPLICATION_CREDENTIALS "
                    "in .env file to path of your service account JSON file."
                )
            # Google translator will be initialized per-batch if needed
        else:
            # Using DeepL (default or explicitly requested)
            if not api_key:
                api_key = os.getenv('DEEPL_API_KEY')
                if not api_key:
                    raise ValueError(
                        "Translation API credentials required. Set either:\n"
                        "  - DEEPL_API_KEY for DeepL, or\n"
                        "  - GOOGLE_APPLICATION_CREDENTIALS for Google Cloud Translation\n"
                        "  in .env file or pass --api-key parameter."
                    )
            
            # Initialize DeepL translator with retry handling and increased timeout
            self.logger.info("Initializing DeepL translator...")
            import deepl.http_client
            import requests
            
            # Configure automatic retries for rate limiting (HTTP 429)
            # Note: Client handles basic retries, but we add exponential backoff for high load
            deepl.http_client.max_network_retries = 3
            
            # Increase timeout for requests (default is 10s, we set to 60s for slow connections)
            # DeepL library uses requests internally, so we configure it by monkey-patching
            # We'll intercept requests.Session.request to add a default timeout
            _original_session_request = requests.Session.request
            
            def _patched_request(self, method, url, **kwargs):
                # Set timeout to 60 seconds if not already specified
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = 60.0
                return _original_session_request(self, method, url, **kwargs)
            
            requests.Session.request = _patched_request
            
            # Check for proxy configuration (useful if IP is blocked)
            proxy_url = os.getenv('DEEPL_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')
            
            # DeepL library auto-detects free vs paid endpoint based on API key format
            # Paid keys automatically use https://api.deepl.com
            # Free keys automatically use https://api-free.deepl.com
            try:
                if proxy_url:
                    # DeepL library supports proxy via constructor argument
                    self._deepl_translator = deepl.Translator(api_key, proxy=proxy_url)
                    self.logger.info(f"DeepL translator initialized with proxy: {proxy_url}")
                else:
                    self._deepl_translator = deepl.Translator(api_key)
                    self.logger.info("DeepL translator initialized (auto-detected endpoint, timeout: 60s)")
            except TypeError:
                # Older library version might not support proxy parameter
                self._deepl_translator = deepl.Translator(api_key)
                if proxy_url:
                    self.logger.warning(f"Proxy {proxy_url} specified but library version doesn't support it")
                self.logger.info("DeepL translator initialized (auto-detected endpoint, timeout: 60s)")
            
            # Check account status and usage (helps diagnose IP blocking)
            try:
                usage = self._deepl_translator.get_usage()
                if usage.character.limit_reached:
                    raise ValueError(
                        f"DeepL API character limit reached. "
                        f"Used {usage.character.count}/{usage.character.limit} characters. "
                        f"Please check your quota or wait for the billing period to reset."
                    )
                self.logger.info(f"DeepL API Status:")
                self.logger.info(f"  Characters used: {usage.character.count:,}/{usage.character.limit:,}")
                self.logger.info(f"  Available: {usage.character.limit - usage.character.count:,} characters")
                if usage.character.limit - usage.character.count < 10000:
                    self.logger.warning(f"  ⚠ Warning: Low quota remaining!")
            except Exception as e:
                # Usage check might fail for free API or geo-restrictions, but translation may still work
                error_msg = str(e)
                error_lower = error_msg.lower()
                
                # Check for connection/timeout errors that might indicate IP blocking
                if any(keyword in error_lower for keyword in ['timeout', 'connection', 'ssl', 'tls', 'unreachable']):
                    self.logger.error(f"⚠ Connection error during API usage check: {error_msg[:100]}")
                    self.logger.error("  This may indicate:")
                    self.logger.error("    1. DeepL API is currently unreachable")
                    self.logger.error("    2. Your IP address may be blocked by DeepL")
                    self.logger.error("    3. Network connectivity issues")
                    self.logger.error("  If this persists, contact DeepL support or use a proxy (set DEEPL_PROXY in .env)")
                    self.logger.info("  Attempting translation anyway...")
                elif "451" in error_msg or "Unavailable" in error_lower or "region" in error_lower:
                    self.logger.warning(f"⚠ Warning: API usage check failed (may be geo-restricted): {error_msg[:100]}")
                    self.logger.info("  Translation may still work. Proceeding...")
                else:
                    self.logger.warning(f"⚠ Warning: Could not check API usage: {error_msg[:100]}")
                    self.logger.info("  Continuing anyway...")
        
        # Get statistics
        stats = self.db.get_statistics(group_key)
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Translation Summary for Group: {group_key}")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total keys: {stats['total']}")
        self.logger.info(f"Already translated: {stats['translated']}")
        self.logger.info(f"Pending: {stats['pending'] - stats.get('error', 0)}")
        self.logger.info(f"Errors (to retry): {stats.get('error', 0)}")
        self.logger.info(f"Total to translate: {stats['pending']}")
        self.logger.info(f"Progress: {stats['percentage']:.1f}%")
        self.logger.info(f"{'='*60}\n")
        
        if stats['pending'] == 0:
            self.logger.info("✓ All keys already translated!")
            return
        
        # Get pending and error translations (status-based, not position-based)
        pending = self.db.get_pending_translations(group_key)
        
        if not pending:
            self.logger.info("✓ No keys to translate!")
            return
        
        self.logger.info(f"Translating {len(pending)} keys (pending + errors)...")
        self.logger.info("(DeepL client will automatically handle rate limiting and retries)")
        self.logger.info("(Using exponential backoff for high load errors)\n")
        
        translated_count = 0
        error_count = 0
        high_load_errors = 0
        
        # Process in batches of 100 keys
        batch_size = 100
        total_batches = (len(pending) + batch_size - 1) // batch_size
        
        self.logger.info(f"Processing {len(pending)} keys in {total_batches} batches of {batch_size}")
        self.logger.info("Strategy: Translate 100 keys, if high load detected -> sleep, then continue")
        
        batch_start_idx = 0
        
        while batch_start_idx < len(pending):
            # Get next batch
            batch_end_idx = min(batch_start_idx + batch_size, len(pending))
            current_batch = pending[batch_start_idx:batch_end_idx]
            batch_num = (batch_start_idx // batch_size) + 1
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing batch {batch_num}/{total_batches} (keys {batch_start_idx + 1}-{batch_end_idx})")
            self.logger.info(f"{'='*60}")
            
            batch_translated = 0
            batch_errors = 0
            batch_high_load = False
            
            self.logger.info(f"Starting batch {batch_num}/{total_batches} ({len(current_batch)} keys)")
            
            for idx, row in enumerate(current_batch, 1):
                global_idx = batch_start_idx + idx
                key = row['key']
                original_text = row['original_text']
                
                # Log every key to file, but show progress on console
                self.logger.info(f"[{global_idx}/{len(pending)}] Translating: {key[:80]}...")
                
                # Show progress on console every 10 keys
                if idx % 10 == 0 or idx == len(current_batch):
                    current_stats = self.db.get_statistics(group_key)
                    progress_msg = (f"[Batch {batch_num}, Key {global_idx}/{len(pending)}] "
                                  f"Progress: {current_stats['translated']}/{current_stats['total']} "
                                  f"({current_stats['percentage']:.1f}%) - "
                                  f"Translated: {translated_count + batch_translated}, Errors: {error_count + batch_errors}")
                    self.logger.info(progress_msg)
                    print(f"\r{progress_msg}", end='', flush=True)
                else:
                    print(f"\r[Batch {batch_num}, Key {global_idx}/{len(pending)}] Translating...", end='', flush=True)
                
                try:
                    # Detect which translation service to use
                    translation_service = os.getenv('TRANSLATION_SERVICE', 'auto')
                    google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                    
                    if translation_service == 'google' or (translation_service == 'auto' and google_creds and not api_key):
                        # Use Google Cloud Translation
                        # Determine API version
                        api_version = google_api_version or os.getenv('GOOGLE_TRANSLATE_API_VERSION', 'v3')
                        api_version = api_version.lower().replace('v', '').strip()
                        
                        # Initialize translator if not already done (version-specific)
                        translator_key = f'_google_translator_v{api_version}'
                        if not hasattr(self, translator_key) or getattr(self, translator_key) is None:
                            if api_version == '3':
                                from google.cloud.translate_v3 import TranslationServiceClient
                                from google.oauth2 import service_account
                                
                                if google_creds and os.path.exists(google_creds):
                                    credentials = service_account.Credentials.from_service_account_file(google_creds)
                                    setattr(self, translator_key, TranslationServiceClient(credentials=credentials))
                                else:
                                    setattr(self, translator_key, TranslationServiceClient())
                                self.logger.info(f"Using Google Cloud Translation API v3 (Advanced)")
                            else:
                                from google.cloud import translate_v2
                                setattr(self, translator_key, translate_v2.Client.from_service_account_json(google_creds))
                                self.logger.info(f"Using Google Cloud Translation API v2 (Basic)")
                        
                        translator = getattr(self, translator_key) if hasattr(self, translator_key) else None
                        translated = self.processor.translate_text(
                            original_text, 
                            translator=translator,
                            service='google',
                            credentials_path=google_creds,
                            api_version=f'v{api_version}',
                            target_locale=target_locale
                        )
                    else:
                        # Use DeepL (default)
                        # Use the pre-initialized translator if available
                        deepl_translator = getattr(self, '_deepl_translator', None)
                        if not deepl_translator:
                            # Initialize on the fly if not already initialized
                            import deepl
                            deepl_translator = deepl.Translator(api_key or os.getenv('DEEPL_API_KEY'))
                        translated = self.processor.translate_with_deepl(
                            original_text, deepl_translator, api_key, target_locale
                        )
                    
                    # Update database with successful translation
                    # Determine translation method based on service used
                    current_translation_method = 'google' if (translation_service == 'google' or (translation_service == 'auto' and google_creds)) else 'deepl'
                    self.db.update_translation(
                        group_key, key, translated, 
                        translation_method=current_translation_method, 
                        status='translated'
                    )
                    translated_count += 1
                    batch_translated += 1
                    
                    # Log successful translation (to file)
                    translated_preview = translated[:60] + "..." if translated and len(translated) > 60 else (translated or "")
                    self.logger.info(f"  ✓ Success: {key[:60]}... -> {translated_preview}")
                    
                    # Small delay to avoid hitting rate limits too quickly
                    # DeepL client handles retries, but we add a small delay to be polite
                    time.sleep(0.05)
                    
                except Exception as e:
                    error_count += 1
                    batch_errors += 1
                    error_msg = str(e)
                    error_type = type(e).__name__
                    
                    # Check if it's a Google Cloud API error
                    is_google_error = (
                        'google' in error_type.lower() or
                        'google.api_core' in str(type(e)) or
                        '403' in error_msg or
                        'resource exhausted' in error_msg.lower() or
                        'quota exceeded' in error_msg.lower() or
                        'daily limit exceeded' in error_msg.lower() or
                        'user rate limit exceeded' in error_msg.lower()
                    )
                    
                    # Check if it's a DeepL error
                    is_deepl_error = (
                        'deepl' in error_type.lower() or
                        hasattr(e, '__class__') and 'DeepLException' in str(type(e))
                    )
                    
                    # Check if it's a high load / rate limit error
                    is_high_load = (
                        # DeepL errors
                        (is_deepl_error and (
                            'too many requests' in error_msg.lower() or
                            'high load' in error_msg.lower() or
                            '429' in error_msg or
                            '529' in error_msg or
                            'rate limit' in error_msg.lower()
                        )) or
                        # Google Cloud errors
                        (is_google_error and (
                            '403' in error_msg or
                            'resource exhausted' in error_msg.lower() or
                            'quota exceeded' in error_msg.lower() or
                            'daily limit exceeded' in error_msg.lower() or
                            'user rate limit exceeded' in error_msg.lower() or
                            'rate limit' in error_msg.lower()
                        ))
                    )
                    
                    # Check if it's a timeout or connection error (handle separately)
                    is_timeout = (
                        'timeout' in error_msg.lower() or
                        'timed out' in error_msg.lower() or
                        'read timeout' in error_msg.lower() or
                        'connection timeout' in error_msg.lower() or
                        'ssl connection timeout' in error_msg.lower()
                    )
                    
                    # Check if it's a connection error (service might be down)
                    is_connection_error = (
                        'connection' in error_msg.lower() and 'error' in error_msg.lower() or
                        'connection refused' in error_msg.lower() or
                        'connection reset' in error_msg.lower() or
                        'name or service not known' in error_msg.lower() or
                        'failed to establish' in error_msg.lower()
                    )
                    
                    if is_high_load:
                        high_load_errors += 1
                        batch_high_load = True
                        service_name = "Google Cloud Translation" if is_google_error else "DeepL"
                        self.logger.warning(f"⚠ Rate limit error ({service_name}) for {key[:60]}...: {error_msg[:100]}")
                        # Mark as error but don't wait here - we'll pause after batch
                        print(f"\n  ⚠ Rate limit detected in batch {batch_num} ({service_name})...", flush=True)
                    elif is_timeout or is_connection_error:
                        # Connection errors or timeouts suggest service might be down/unreachable
                        service_name = "Google Cloud Translation" if is_google_error else "DeepL"
                        if is_connection_error:
                            self.logger.warning(f"⚠ Connection error ({service_name} may be unreachable): {error_msg[:100]}")
                            self.logger.warning("  This may indicate service is down or network connectivity issues")
                            print(f"\n  ⚠ Connection error - {service_name} may be unreachable (will retry later)...", flush=True)
                        else:
                            self.logger.warning(f"⚠ Timeout error for {key[:60]}...: {error_msg[:100]}")
                            print(f"\n  ⚠ Timeout (will retry later)...", flush=True)
                        # Don't trigger high load pause - these are connectivity issues, not rate limits
                        self.logger.info("  Connection/timeout errors won't trigger high load pause - will retry later")
                    else:
                        service_name = "Google Cloud Translation" if is_google_error else "DeepL"
                        self.logger.warning(f"⚠ Error translating ({service_name}) {key[:60]}...: {error_msg[:100]}")
                    
                    # Mark as error - clear translated_text so it can be retried later
                    try:
                        # Set translated_text to NULL so it can be retranslated
                        table_name = self.db.get_table_name(group_key)
                        with self.db.connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(f"""
                                UPDATE {table_name} 
                                SET translated_text = NULL, translation_method = ?, status = 'error', updated_at = ?
                                WHERE key = ?
                            """, (f'error: {error_msg[:100]}', datetime.now().isoformat(), key))
                    except Exception as db_err:
                        self.logger.error(f"Database error: {db_err}")
                        
                except Exception as e:
                    error_count += 1
                    batch_errors += 1
                    error_msg = str(e)
                    
                    # Check if it's a connection-related exception
                    error_type = type(e).__name__
                    is_connection_exception = any(keyword in error_type.lower() for keyword in 
                                                  ['connection', 'timeout', 'network', 'socket'])
                    
                    if is_connection_exception:
                        self.logger.error(f"⚠ Connection exception ({error_type}) for {key[:60]}...: {error_msg[:100]}")
                        self.logger.error("  This may indicate DeepL service is down or network connectivity issues")
                        print(f"\n  ⚠ Connection exception - DeepL may be unreachable (will retry later)...", flush=True)
                    else:
                        self.logger.error(f"⚠ Unexpected error ({error_type}) translating {key[:60]}...: {error_msg[:100]}")
                        print(f"\n  ⚠ Unexpected error: {error_msg[:100]}", file=sys.stderr)
                    
                    # Mark as error - clear translated_text so it can be retried later
                    try:
                        table_name = self.db.get_table_name(group_key)
                        with self.db.connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(f"""
                                UPDATE {table_name} 
                                SET translated_text = NULL, translation_method = ?, status = 'error', updated_at = ?
                                WHERE key = ?
                            """, (f'error: {error_msg[:100]}', datetime.now().isoformat(), key))
                    except Exception as db_err:
                        self.logger.error(f"Database error: {db_err}")
            
            # Batch completed - log results
            batch_summary = f"Batch {batch_num}/{total_batches} completed: Translated: {batch_translated}/{len(current_batch)}, Errors: {batch_errors}"
            self.logger.info(f"\n{'='*60}")
            self.logger.info(batch_summary)
            self.logger.info(f"{'='*60}")
            print()  # New line after batch
            print(batch_summary)  # Also show on console
            
            # If high load detected in this batch, sleep before continuing
            if batch_high_load:
                # Sleep time increases with each high load batch: 30s, 40s, 50s... up to 120s max
                sleep_time = min(30 + (high_load_errors * 10), 120)  # 30s to 120s max
                self.logger.warning(f"⚠ High load detected in batch {batch_num}. Sleeping for {sleep_time}s before next batch...")
                print(f"\n⏸ High load detected. Sleeping for {sleep_time}s before continuing...", flush=True)
                time.sleep(sleep_time)
                # Re-fetch pending keys after pause (in case some were retried successfully)
                pending = self.db.get_pending_translations(group_key)
                # Recalculate batches based on remaining keys
                total_batches = (len(pending) + batch_size - 1) // batch_size
                batch_start_idx = 0  # Start from beginning of remaining keys
                self.logger.info(f"After pause: {len(pending)} keys remaining, {total_batches} batches left")
            else:
                # Continue with next batch
                batch_start_idx = batch_end_idx
                # Small pause between successful batches to be polite
                if batch_num < total_batches:
                    time.sleep(2)
                    self.logger.debug(f"Brief pause between batches (2s)")
            
            # Update current stats
            current_stats = self.db.get_statistics(group_key)
            self.logger.info(f"Overall progress: {current_stats['translated']}/{current_stats['total']} ({current_stats['percentage']:.1f}%)")
        
        print()  # New line after progress
        self.logger.info("")  # Empty line in log
        
        # Final statistics
        final_stats = self.db.get_statistics(group_key)
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"✓ Translation completed!")
        self.logger.info(f"  Group: {group_key}")
        self.logger.info(f"  Total keys: {final_stats['total']}")
        self.logger.info(f"  Translated: {final_stats['translated']} (+{translated_count} new)")
        self.logger.info(f"  Pending: {final_stats['pending']}")
        self.logger.info(f"  Errors: {error_count} (High load errors: {high_load_errors})")
        self.logger.info(f"  Progress: {final_stats['percentage']:.1f}%")
        self.logger.info(f"{'='*60}")
        
        print(f"\n{'='*60}")
        print(f"✓ Translation completed!")
        print(f"  Group: {group_key}")
        print(f"  Total keys: {final_stats['total']}")
        print(f"  Translated: {final_stats['translated']} (+{translated_count} new)")
        print(f"  Pending: {final_stats['pending']}")
        print(f"  Errors: {error_count} (High load errors: {high_load_errors})")
        print(f"  Progress: {final_stats['percentage']:.1f}%")
        print(f"{'='*60}")
        
        # Check final usage
        try:
            final_usage = translator.get_usage()
            self.logger.info(f"\nDeepL API Final Status:")
            self.logger.info(f"  Characters used: {final_usage.character.count:,}/{final_usage.character.limit:,}")
            print(f"\nDeepL API Final Status:")
            print(f"  Characters used: {final_usage.character.count:,}/{final_usage.character.limit:,}")
        except Exception as e:
            self.logger.debug(f"Could not get final usage: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Translate group keys from database using DeepL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate a specific group
  python3 src/translate_group.py --group linchpin-suite
  
  # Resume translation (automatically continues from pending/error keys)
  python3 src/translate_group.py --group linchpin-suite
        """
    )
    
    parser.add_argument('--group', required=True,
                       help='Group key to translate (e.g., linchpin-suite)')
    parser.add_argument('--api-key',
                       help='DeepL API key (default: from .env file or DEEPL_API_KEY env var)')
    parser.add_argument('--google-api-version', choices=['v2', 'v3'], default=None,
                       help='Google Cloud Translation API version: v2 (Basic) or v3 (Advanced). Default: from GOOGLE_TRANSLATE_API_VERSION env var or v3')
    parser.add_argument('--target-language', default=None,
                       help='Target locale code (e.g., ru_RU, de_DE). Defaults to TARGET_LANGUAGE env var or ru_RU')
    parser.add_argument('--db', default='db/translations.db',
                       help='Database path (default: db/translations.db)')
    
    args = parser.parse_args()
    
    try:
        # Set up logging
        logger = setup_logging(args.group)
        logger.info(f"Starting translation for group: {args.group}")
        logger.info(f"Database: {args.db}")
        
        translator = GroupTranslator(args.db, logger=logger)
        translator.translate_group(
            args.group, 
            args.api_key,
            google_api_version=args.google_api_version,
            target_locale=args.target_language
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted! Progress has been saved in database.")
        print("You can resume later - it will automatically continue from pending/error keys.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

