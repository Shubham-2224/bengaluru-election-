import re
import io
import os
import base64
from deep_translator import GoogleTranslator

class TranslitHelper:
    """
    Helper class for English-only voter data extraction.
    Removed all Marathi-specific logic as requested.
    """
    
    _translit_cache = {}
    _kannada_translator = GoogleTranslator(source='en', target='kn')

    @staticmethod
    def correct_ocr_misreads(text):
        """
        Fix common English OCR misreads for voter documents.
        This should be used carefully to avoid mangling names.
        """
        if not text: return ""
        
        # 1. Fix common gender misreads (more robust)
        # Only if the text looks like it might be a gender field
        t_upper = text.strip().upper()
        if t_upper in ['NALE', 'PIALE', 'PU', 'PUR', 'MALE']:
             return "Male"
        if t_upper in ['RENALE', 'STRI', 'MAHILA', 'FEM', 'FE', 'FEMALE']:
             return "Female"

        # 2. Fix common "Name" label misreads (pre-cleaning)
        text = re.sub(r'\b(Nam|Nav|Nam|Nav|Nam)\b', 'Name', text, flags=re.IGNORECASE)
        
        return text

    @staticmethod
    def transliterate_marathi_to_english(text):
        """
        No longer transliterating from Marathi.
        Just cleaning and returning English text as requested.
        """
        if not text: return ""
        text = TranslitHelper.correct_ocr_misreads(text)
        # Standardize capitalization for voter data
        return ' '.join(word.capitalize() for word in text.split()).strip()

    @staticmethod
    def transliterate_marathi_to_kannada(text):
        """
        Since input is now English-only, we translate English to Kannada.
        """
        return TranslitHelper.translate_to_kannada(text)

    @staticmethod
    def translate_to_kannada(text):
        """
        Translate English text to Kannada using Google Translator.
        Includes retry logic for robustness.
        """
        if not text or len(str(text).strip()) < 2:
            return ""
        
        text = str(text).strip()
        try:
            # Check cache
            cache_key = f"en_kn_{text}"
            if cache_key in TranslitHelper._translit_cache:
                return TranslitHelper._translit_cache[cache_key]
            
            # Implementation with retry
            import time
            last_err = None
            for attempt in range(3):
                try:
                    result = TranslitHelper._kannada_translator.translate(text)
                    if result:
                        TranslitHelper._translit_cache[cache_key] = result
                        return result
                except Exception as e:
                    last_err = e
                    time.sleep(0.5 * (attempt + 1))
            
            # Fallback: if translation fails repeatedly, return the English text
            # This prevents data from being "skipped" entirely
            return text
        except:
            return text # Absolute fallback to English

    @staticmethod
    def map_gender(text):
        """
        Aggressive Gender mapping for messy OCR results.
        Includes common misreads: Ml, Mo, MM, iF, an, etc.
        """
        if not text:
            return ""
        
        t = str(text).strip().upper()
        # Remove common noise
        t = re.sub(r'[^A-Z]', ' ', t)
        t = ' '.join(t.split())
        
        # 1. Direct Keyword Matches (Highest Priority)
        if any(k in t for k in ['FEMALE', 'STRI', 'RENALE']): return "Female"
        if any(k in t for k in ['MALE', 'PURUSH', 'NALE']):
             if 'FEMALE' in t: return "Female"
             return "Male"

        # 2. Misread patterns - Female
        # iF, an (STRI misread?), ST, FE, EMA, LEN
        if any(k in t for k in [' FE', 'FE ', ' IF', 'IF ', 'STRI', 'ST ', ' AN ', 'ENALE']):
             return "Female"
        if t.startswith('F') or t.endswith('F') or t == 'F': return "Female"

        # 3. Misread patterns - Male
        # Ml, Mo, MM, MA, PIALE
        if any(k in t for k in ['ML', 'MO', 'MM', 'MA ', ' MA', 'PIALE', 'NALE']):
             if 'EMA' in t: return "Female" # avoid fEMALE
             return "Male"
        if t.startswith('M') or t.endswith('M') or t == 'M': 
             if t.startswith('FEM'): return "Female"
             return "Male"
        
        # 4. Final Fuzzy Substrings
        if 'FEM' in t or 'STR' in t: return "Female"
        if 'MAL' in t or 'PUR' in t: return "Male"
        
        return ""

    @staticmethod
    def map_relation_type(text):
        if not text:
            return ""
        t = str(text).strip().upper()
        
        if any(k in t for k in ['HUSBAND', 'H/O', 'H.O', 'H ']): return 'H'
        if any(k in t for k in ['FATHER', 'S/O', 'S.O', 'F ']): return 'F'
        if any(k in t for k in ['MOTHER', 'D/O', 'D.O', 'M ']): return 'M'
        if any(k in t for k in ['OTHER', 'W/O', 'W.O', 'O ']): return 'O'
        
        # Pass through abbreviations
        if t in ['H', 'F', 'M', 'O']: return t
        
        return ""

    @staticmethod
    def sanitize_name(text, is_relative=False):
        """
        Clean and format English names for voter records.
        """
        if not text:
            return ""
        
        # 1. Colon splitting fallback (User: "only data after colon")
        if ':' in text:
            text = text.rsplit(':', 1)[-1].strip()
        
        # 2. NEW ANCHOR STRIPPING: Remove everything UP TO "Name" label (User requested)
        # This handles cases like "Ausband S Name Surel Armed" -> "Surel Armed"
        name_anchor = re.search(r'\b(Name|Nam|Nav|Nan|Nom|Narn|Nim|Naro|Nare)\b', text, flags=re.IGNORECASE)
        if name_anchor:
            text = text[name_anchor.end():].strip()

        # 1.1 Basic OCR cleanup
        text = text.replace('||', '').replace('|', '')
        
        # 2. Remove common English labels and OCR artifacts (like Photo indicators)
        # Added common misreads: Falher, Fusband, Fusbanda, Pinoie, Pnote, Cnoto, Polo
        labels_pattern = r'^(?:Father|Husband|Mother|Relative|Other|Name|Nam|Nav|Nam|Phoate|Photo|Pnote|Pinoie|Fnote|Cnoto|Polo|Pnale|Not|Nat|Falher|Fusband|Fusbanda|Pinoie|Pnote|Cnoto|Polo|Pnale|Not|Nat)\'?\s*s?\s*(?:Name|Nav|Nam|Not|Available)?\s*(?:is)?\s*[:\-\.\|\\/ ]*'
        text = re.sub(labels_pattern, '', text, flags=re.IGNORECASE).strip()
        
        # 2.1 Specific junk removals for common bleeding text
        junk_patterns = [
            r'\b(?:Phoate|Phote|Pnote|Pinoie|Fnote|Cnoto|Polo|Pnale)\s*(?:Nat|Not)?\b',
            r'\bPhoto\s*(?:Available|Not)?\b'
        ]
        for jp in junk_patterns:
             text = re.sub(jp, '', text, flags=re.IGNORECASE).strip()
        
        # 2.2 Watermark removal
        watermark_patterns = [
            r'STATE\s+ELECTION\s+COMMISSION',
            r'ELECTION\s+COMMISSION\s+OF\s+INDIA',
            r'ELECTION\s+COMMISSION',
            r'STATE\s+ELECTION',
            r'COMMISSION',
            r'ELECTION',
            r'INDIA'
        ]
        for wp in watermark_patterns:
            text = re.sub(wp, '', text, flags=re.IGNORECASE).strip()
        
        # 3. Strictly keep only English letters and spaces
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        
        # 4. Normalize whitespace and capitalize
        text = ' '.join(word.capitalize() for word in text.split()).strip()
        
        # 5. Remove leading/trailing junk artifacts (like "Gh Ee I", "Rie Rad")
        # Removes leading fragments of 1-3 letters that look like OCR noise
        text = re.sub(r'^(?:[a-z]{1,2}|v|vi|vii|viii|ix|x)\s+', '', text, flags=re.IGNORECASE).strip()
        text = re.sub(r'^(?:Gh|Ee|Ii|Oo|Aa|Ai|Au)\s+', '', text, flags=re.IGNORECASE).strip()
        
        # 6. Final cleanup: eliminate lone single characters resulting from sanitization
        if len(text) <= 2 and not text.isalpha():
            return ""
        
        return text

    @staticmethod
    def normalize_digits(text):
        """
        Convert Indian script numerals (Kannada, Devanagari) to standard English numbers (0-9).
        """
        if not text: return ""
        
        # Devanagari (Hindi, Marathi)
        dev_digits = '०१२३೪೫೬೭೮೯' # Wait, my keyboard is mixing things. ०-९
        # Actually better to use unicode ranges
        
        # Mapping for Devanagari digits 0-9
        dev_map = str.maketrans('०१२३४५६७८९', '0123456789')
        # Mapping for Kannada digits 0-9
        kan_map = str.maketrans('೦೧೨೩೪೫೬೭೮೯', '0123456789')
        
        text = text.translate(dev_map)
        text = text.translate(kan_map)
        
        return text

    @staticmethod
    def clean_booth_info(text):
        """
        Clean and format booth center/address information (English only).
        """
        if not text:
            return ""
        
        # 1. Remove Watermark Noise
        watermark_patterns = [
            r'STATE\s+ELECTION\s+COMMISSION',
            r'ELECTION\s+COMMISSION\s+OF\s+INDIA',
            r'ELECTION\s+COMMISSION',
            r'STATE\s+ELECTION',
            r'COMMISSION',
            r'ELECTION',
            r'INDIA'
        ]
        active_text = text
        for p in watermark_patterns:
            active_text = re.sub(p, '', active_text, flags=re.IGNORECASE).strip()
        
        # 2. Remove common labels
        labels = [
            r'(?:Polling Station Name|Station Name|Polling Station Address|Address)\s*[:\-]*',
            r'^(?:Center|Address|Station|Name)\b\s*[:\-]*'
        ]
        for lp in labels:
            active_text = re.sub(lp, '', active_text, flags=re.IGNORECASE).strip()

        # 3. Standardize whitespace
        result = ' '.join(active_text.split()).strip()
        
        # 4. Final misread fixes for schools
        result = result.replace('2.2', 'Z.P.').replace('9.P', 'Z.P.').replace('800', 'Bhor')
        
        return result
