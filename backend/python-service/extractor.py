"""
Enhanced Extractor - Grid-based extraction with local OCR
Uses local Tesseract OCR for high-accuracy extraction
"""

import os

# PERFORMANCE OPTIMIZATION: Suppress verbose logging BEFORE imports
os.environ['OMP_THREAD_LIMIT'] = '1'  # Limit Tesseract threads for better multiprocessing
os.environ['GLOG_minloglevel'] = '3'  # Suppress PaddlePaddle C++ logs (0=INFO, 3=ERROR)
os.environ['FLAGS_print_model_net_proto'] = '0'  # Don't print model proto
os.environ['PADDLEOCR_SHOW_LOG'] = '0'  # Suppress PaddleOCR logs

# Memory optimization settings
os.environ['PYTHONUNBUFFERED'] = '0'  # Reduce I/O buffering
import gc  # Enable garbage collection control

import fitz  # PyMuPDF
import pytesseract
import base64
import io
from PIL import Image
import re
from typing import Dict, List, Optional
import multiprocessing as mp
from functools import partial
import time

# Import advanced modules
try:
    from photo_processor import PhotoProcessor
    PHOTO_PROCESSOR_AVAILABLE = True
except ImportError:
    PHOTO_PROCESSOR_AVAILABLE = False
    pass  # Photo Processor optional

try:
    from box_detector import BoxDetector
    BOX_DETECTOR_AVAILABLE = True
except ImportError:
    BOX_DETECTOR_AVAILABLE = False
    pass  # Box Detector optional

try:
    from smart_detector import SmartDetector
    SMART_DETECTOR_AVAILABLE = True
except ImportError:
    SMART_DETECTOR_AVAILABLE = False
    pass  # Smart Detector optional
    
from translit_helper import TranslitHelper

# Import 400 DPI OCR Processor
try:
    from ocr_processor_400dpi import OCRProcessor400DPI
    OCR_400DPI_AVAILABLE = True
except ImportError:
    OCR_400DPI_AVAILABLE = False
    pass  # 400 DPI OCR Processor optional

# Configure Tesseract OCR path
# Priority: 1. TESSERACT_CMD env var, 2. Auto-detect by OS
tesseract_cmd_from_env = os.getenv('TESSERACT_CMD')
if tesseract_cmd_from_env:
    # Use explicitly set path from environment (important for systemd services)
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_from_env
elif os.name == 'nt':  # Windows - auto-detect
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Tesseract-OCR\tesseract.exe',
    ]
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
else:
    # Linux/Unix - try common locations if not in PATH
    linux_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/bin/tesseract'
    ]
    for path in linux_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

# Initialize processors
photo_processor = PhotoProcessor() if PHOTO_PROCESSOR_AVAILABLE else None
box_detector = BoxDetector() if BOX_DETECTOR_AVAILABLE else None
smart_detector = SmartDetector() if SMART_DETECTOR_AVAILABLE else None
ocr_processor_400dpi = OCRProcessor400DPI() if OCR_400DPI_AVAILABLE else None

# Pre-compile regex patterns for better performance
EPIC_REGEX = re.compile(r'^[A-Z]{3}[0-9]{7}$')
LOOSE_EPIC_REGEX = re.compile(r'^[A-Z]{2,4}[0-9]{6,8}$')
DEVANAGARI_REGEX = re.compile(r'[\u0900-\u097F]')
NUMBER_CLEANUP_REGEX = re.compile(r'[0-9,]+')

# Constants for robust extraction (Global across Age/House/IDs)
GLOBAL_OCR_DIGIT_MAP = {
    'O': '0', 'D': '0', 'U': '0', 'Q': '0', 'V': '0',
    'I': '1', 'L': '1', 'J': '1', '|': '1',
    'Z': '2', 'A': '4', 'H': '4', 'Y': '4',
    'S': '5', 'G': '6', 'T': '7', 'B': '8', 'E': '8', 'P': '9'
}
GLOBAL_DIGIT_TRANS = str.maketrans(''.join(GLOBAL_OCR_DIGIT_MAP.keys()), ''.join(GLOBAL_OCR_DIGIT_MAP.values()))

# WATERMARK PROTECTION: Expanded list of watermark keywords to exclude from text layer
WATERMARK_WORDS = {
    'STATE', 'ELECTION', 'COMMISSION', 'INDIA', 'AVAILABLE', 'COUNCIL', 
    'ASSEMBLY', 'ELECTORAL', 'ROLL', 'OF', 'BENGALURU', 'KARNATAKA', 
    'BANGALORE', 'POLLING', 'STATION', 'PART', 'NO', 'SECTION', 'CENTRE',
    'DETAILS', 'NAME', 'MOTHER', 'FATHER', 'HUSBAND', 'OTHER'
}

AGE_LABELS = ['AGE', 'VAYASSU', 'ವಯಸ್ಸು', 'VAY', 'VAYU', 'வயது', 'AAYU', 'UMR', 'வயது', 'ಉಯರಂ', 'वय', 'आयु', 'उम्र', 'A:', 'A-', 'AG:']
HOUSE_LABELS = ['HOUSE', 'H.NO', 'H. NO', 'H NO', 'HS NO', 'H. NO.', 'ಮನೇ ಸಂಖ್ಯೇ', 'ಮನೆ ಸಂಖ್ಯೆ', 'ঘর নং', 'सदन संख्या']

# Get CPU count for multiprocessing
def get_cpu_count():
    """Get optimal CPU count for multiprocessing - USE ALL CORES!"""
    try:
        cpu_count = mp.cpu_count()
        # Use 100% of available CPUs for maximum speed
        optimal_workers = max(1, cpu_count)
        return optimal_workers
    except:
        return 4  # Fallback to 4 workers

CPU_WORKERS = get_cpu_count()

def _extract_text_fast(rect, page_words):
    if not page_words: return ""
    res = []
    
    # 🛡️ WATERMARK SUPPRESSION: Filter out watermark words while joining text layer words
    for w in page_words:
        w_cx = (w[0] + w[2]) / 2
        w_cy = (w[1] + w[3]) / 2
        
        if rect.x0 <= w_cx <= rect.x1 and rect.y0 <= w_cy <= rect.y1:
            w_text = w[4].strip().upper()
            
            # Skip common watermark tokens
            if w_text in WATERMARK_WORDS:
                continue
                
            # Skip long strings of "STATE ELECTION" variants
            if len(w_text) > 5 and any(wm in w_text for wm in ['ELECTION', 'COMMISSION', 'ELECTORAL', 'AVAILABLE']):
                continue
                
            res.append(w[4])
            
    return " ".join(res).strip()
def _extract_cell_internal(page, page_num, cell_info, config, extraction_limits, processors, master_page_img=None, master_page_scale=None, page_words=None):
    """
    Internal function to process a cell given an open page and processors.
    Refactored for page-level optimization.
    """
    try:
        extraction_y_start, extraction_y_end = extraction_limits
        
        # Extract cell info
        cell_x = cell_info['x']
        cell_y = cell_info['y']
        cell_width_actual = cell_info['width']
        cell_height_actual = cell_info['height']
        row = cell_info['row']
        col = cell_info['col']
        scale_x = cell_info['scale_x']
        scale_y = cell_info['scale_y']
        first_cell_width = cell_info.get('first_cell_width', cell_width_actual)
        first_cell_height = cell_info.get('first_cell_height', cell_height_actual)
        
        # Skip if cell is COMPLETELY outside the extraction area (header/footer zone)
        cell_bottom = cell_y + cell_height_actual
        
        # Skip only if cell is completely in header zone OR completely in footer zone
        if cell_bottom <= extraction_y_start or cell_y >= extraction_y_end:
            return None
            
        # Define full cell rect (REQUIRED for extraction logic)
        cell_full_rect = fitz.Rect(
            cell_x, cell_y, 
            cell_x + cell_width_actual, 
            cell_y + cell_height_actual
        )
        
        # Get configuration
        cell_template = config.get('cellTemplate', {})
        voter_id_box = cell_template.get('voterIdBox', {})
        photo_box = cell_template.get('photoBox', {})

        # Cache performance settings
        extract_photos = config.get('extractPhotos', True)
        performance_mode = config.get('performanceMode', 'balanced')  # fast, balanced, accurate

        # Get processors (only get photo processor if needed)
        local_ocr_processor = processors.get('ocr')
        local_photo_processor = processors.get('photo') if extract_photos else None
        local_smart_detector = processors.get('smart')
        
        # Initialize variables to avoid NameErrors in skip logic
        voter_id_text = ""
        voter_id_confidence = 0.0
        voter_id_method = "none"
        photo_base64 = ""
        voter_id_base64 = ""
        cell_stats = {}

        # CRITICAL OPTIMIZATION: Sub-index words for THIS cell ONLY (Maximum Performance)
        local_cell_words = []
        if page_words:
            c_x0, c_y0, c_x1, c_y1 = cell_full_rect
            # Expand slightly to handle slight digital layer misalignments
            ex = 5
            local_cell_words = [w for w in page_words if 
                                (c_x0 - ex) <= (w[0]+w[2])/2 <= (c_x1 + ex) and 
                                (c_y0 - ex) <= (w[1]+w[3])/2 <= (c_y1 + ex)]
        
        # STRATEGY 0: Try PDF Text Layer First (FASTEST & MOST ACCURATE!)
        if voter_id_box:
            try:
                scaled_voter_id_x = voter_id_box.get('x', 0) * scale_x
                scaled_voter_id_y = voter_id_box.get('y', 0) * scale_y
                scaled_voter_id_width = voter_id_box.get('width', 200) * scale_x
                scaled_voter_id_height = voter_id_box.get('height', 30) * scale_y
                
                # Add PADDING to the voter ID box to ensure no part is cut off (especially on misaligned scans)
                padding_x = 5
                padding_y = 2
                
                voter_id_rect = fitz.Rect(
                    cell_x + scaled_voter_id_x - padding_x,
                    cell_y + scaled_voter_id_y - padding_y,
                    cell_x + scaled_voter_id_x + scaled_voter_id_width + padding_x,
                    cell_y + scaled_voter_id_y + scaled_voter_id_height + padding_y
                )
                
                # 📄 Strategy 0: High-Speed Digital Extraction (FASTEST!)
                if local_cell_words:
                    text_layer = _extract_text_fast(voter_id_rect, local_cell_words)
                else:
                    text_layer = page.get_text("text", clip=voter_id_rect).strip()
                
                if text_layer:
                    # Clean and extract voter ID from text layer
                    text_layer_clean = text_layer.upper().strip()
                    # Remove watermarks surgically from the text stream
                    watermarks = ['STATE ELECTION', 'COMMISSION', 'INDIA', 'AVAILABLE', 'COUNCIL', 'ASSEMBLY', 'ELECTORAL', 'ROLL']
                    for wm in watermarks:
                        text_layer_clean = re.sub(re.escape(wm), '', text_layer_clean, flags=re.IGNORECASE)
                    
                    text_layer_clean = re.sub(r'[^A-Z0-9]', '', text_layer_clean) 
                    
                    # Pattern Search (Strictly 3-7)
                    voter_id_patterns = [r'\b([A-Z]{3}[0-9]{7})\b', r'\b([A-Z]{3}\s*[0-9]{7})\b', r'\b([A-Z]{2,4}[0-9]{6,8})\b']
                    
                    text_layer_voter_id = ""
                    for pattern in voter_id_patterns:
                        matches = re.findall(pattern, text_layer_clean)
                        if matches:
                            text_layer_voter_id = max(matches, key=len).replace(' ', '')
                            break
                    
                    if text_layer_voter_id and len(text_layer_voter_id) >= 10:
                        voter_id_text = text_layer_voter_id
                        voter_id_confidence = 1.0
                        voter_id_method = 'digital_voter_id_direct'
                        cell_stats['pdf_text_layer'] = 1
                    elif len(text_layer_clean) >= 9:
                         voter_id_text = text_layer_clean[:13]
                         voter_id_confidence = 0.5
                         voter_id_method = 'digital_voter_id_partial'
                
            except Exception as e:
                if VERBOSE_OCR_LOGS: print(f"      ⚠️ Digital layer error: {str(e)}")

        # Strategy 1/2: USE MASTER IMAGE FOR CROP (NO REDUNDANT RENDERS)
        if (not voter_id_text or len(voter_id_text.strip()) < 3 or voter_id_confidence < 0.6) and voter_id_box:
            try:
                # Calculate Crop Rect from Master Image (Already at 400dpi)
                voter_id_crop = None
                if master_page_img and master_page_scale:
                    s = master_page_scale
                    header_offset = extraction_limits[0] 
                    left = int(voter_id_rect.x0 * s)
                    top = int((voter_id_rect.y0 - header_offset) * s)
                    right = int(voter_id_rect.x1 * s)
                    bottom = int((voter_id_rect.y1 - header_offset) * s)
                    
                    # Bounds check
                    left = max(0, min(master_page_img.width-1, left))
                    top = max(0, min(master_page_img.height-1, top))
                    right = max(left+1, min(master_page_img.width, right))
                    bottom = max(top+1, min(master_page_img.height, bottom))
                    
                    voter_id_crop = master_page_img.crop((left, top, right, bottom))
                    voter_id_method_tag = "master_crop"
                else:
                    # Fallback to local render only if master missing
                    v_pix = page.get_pixmap(clip=voter_id_rect, dpi=400, alpha=False)
                    voter_id_crop = Image.frombytes("RGB", [v_pix.width, v_pix.height], v_pix.samples)
                    voter_id_method_tag = "local_render"

                # Advance EPIC processing
                if voter_id_crop and local_ocr_processor:
                    result = local_ocr_processor.extract_epic_with_advanced_image_processing(
                        image=voter_id_crop,
                        pdf_page=None,
                        rect=None
                    )
                    
                    if result.get('confidence', 0) > voter_id_confidence:
                        voter_id_text = result.get('voter_id', '')
                        voter_id_confidence = result.get('confidence', 0.0)
                        voter_id_method = f"{voter_id_method_tag}_{result.get('method', 'advanced')}"
                        cell_stats['ocr_advanced_voter_id'] = 1
                
                # ULTRA-AGGRESSIVE FALLBACK: Only if still failed
                if (not voter_id_text or voter_id_confidence < 0.6) and performance_mode != 'fast' and voter_id_crop:
                     try:
                         # Try multiple binarization thresholds on the crop we already have
                         best_ultra_text = ""
                         best_ultra_conf = 0.0
                         
                         for threshold in [128, 160]:
                             bin_img = voter_id_crop.convert('L').point(lambda x: 0 if x < threshold else 255, '1')
                             for psm in [7, 8]:
                                 t_res = pytesseract.image_to_string(bin_img, lang='eng', config=f'--psm {psm} --oem 3').strip()
                                 if t_res:
                                     v_match = local_ocr_processor._validate_epic_format(t_res)
                                     if v_match and v_match['confidence'] > best_ultra_conf:
                                         best_ultra_conf = v_match['confidence']
                                         best_ultra_text = v_match['epic']
                             if best_ultra_conf > 0.9: break
                         
                         if best_ultra_text and best_ultra_conf > voter_id_confidence:
                             voter_id_text = best_ultra_text
                             voter_id_confidence = best_ultra_conf
                             voter_id_method = 'ultra_aggressive_fallback'
                     except: pass
            except Exception as e:
                if VERBOSE_OCR_LOGS: print(f"      ❌ OCR error: {str(e)}")

        # Strategy 3: Smart Detection (Use Master Image)
        if (not voter_id_text or voter_id_confidence < 0.6) and local_smart_detector:
            try:
                if master_page_img and master_page_scale:
                    s = master_page_scale
                    header_offset = extraction_limits[0]
                    left = int(cell_x * s)
                    top = int((cell_y - header_offset) * s)
                    right = int((cell_x + cell_width_actual) * s)
                    bottom = int((cell_y + cell_height_actual - header_offset) * s)
                    cell_img = master_page_img.crop((left, top, right, bottom))
                else:
                    cell_rect = fitz.Rect(cell_x, cell_y, cell_x + cell_width_actual, cell_y + cell_height_actual)
                    cell_pix = page.get_pixmap(clip=cell_rect, dpi=200, alpha=False)
                    cell_img = Image.frombytes("RGB", [cell_pix.width, cell_pix.height], cell_pix.samples)
                
                smart_result = local_smart_detector.find_voter_id_in_cell(cell_img)
                if smart_result['found'] and smart_result['confidence'] > voter_id_confidence:
                    voter_id_text = smart_result['voter_id']
                    voter_id_confidence = smart_result['confidence']
                    voter_id_method = 'smart_detector'
            except: pass
        
        # Strategy 4: Global Pattern Search Fallback (Digital Layer)
        if not voter_id_text or len(voter_id_text) < 5:
            try:
                full_cell_text = page.get_text("text", clip=cell_full_rect).upper()
                # Clean watermarks from full cell text too
                for wm in ['STATE ELECTION', 'COMMISSION', 'INDIA', 'AVAILABLE', 'BENGALURU', 'KARNATAKA']:
                    full_cell_text = full_cell_text.replace(wm, '')
                
                epic_patterns = [r'[A-Z]{3}[0-9]{7}', r'[A-Z]{2,4}[0-9]{6,8}']
                for pattern in epic_patterns:
                    matches = re.findall(pattern, full_cell_text)
                    if matches:
                        voter_id_text = matches[0].replace(' ', '')
                        voter_id_confidence = 0.6
                        voter_id_method = 'global_text_layer_fallback'
                        break
            except: pass
        
        # === PHOTO EXTRACTION REMOVED PER USER REQUEST ===
        photo_base64 = ""
        photo_quality = 0.0
        photo_method = "none"
        
        # === FINAL VERIFICATION: HIGH-POWER TEXT LAYER MATCHING (99% ACCURACY) ===
        # User requested maximum accuracy using CPU power to match PDF text layer with extracted data.
        # OPTIMIZATION: Skip deep verification if we already have a 100% match from text layer
        # This saves massive CPU time on digital PDFs
        try:
            # Define cell verify rect
            cell_rect_verify = fitz.Rect(
                cell_x, 
                cell_y, 
                cell_x + cell_width_actual, 
                cell_y + cell_height_actual
            )
            
            # ALWAYS perform deep verification for maximum integrity
            # COMPUTE-OPTIMIZED CELL WORDS: Use pre-extracted cell words if available
            if local_cell_words:
                 cell_words = local_cell_words
            else:
                 cell_words = page.get_text("words", clip=cell_rect_verify)
            
            # Compile candidates with their metadata
            candidates = []
            
            # Expected Voter ID location (relative to cell)
            expected_x = cell_x + (voter_id_box.get('x', 0) * scale_x)
            expected_y = cell_y + (voter_id_box.get('y', 0) * scale_y)
            
            # Standard Pattern for Voter ID - RELAXED for detection phase
            voter_id_pattern = LOOSE_EPIC_REGEX
            
            for w in cell_words:
                w_text = w[4].strip().upper()
                w_x0, w_y0 = w[0], w[1]
                
                # Check for Voter ID patterns (Standard)
                if voter_id_pattern.match(w_text):
                    dist = ((w_x0 - expected_x)**2 + (w_y0 - expected_y)**2)**0.5
                    candidates.append({'text': w_text, 'conf': 1.0, 'dist': dist, 'type': 'exact'})
            
            # Advanced Pattern Search: Concatenate adjacent words to handle split IDs
            # Example: "UZZ" + "1234567" or "UZZ123" + "4567"
            for i in range(len(cell_words)-1):
                w1 = cell_words[i]
                w2 = cell_words[i+1]
                
                # If words are physically close (same line approximation)
                if abs(w1[1] - w2[1]) < 5 and abs(w2[0] - w1[2]) < 10:
                    combined = (w1[4] + w2[4]).replace(' ', '').upper()
                    if voter_id_pattern.match(combined):
                        w_x0, w_y0 = w1[0], w1[1]
                        dist = ((w_x0 - expected_x)**2 + (w_y0 - expected_y)**2)**0.5
                        candidates.append({'text': combined, 'conf': 0.99, 'dist': dist, 'type': 'combined'})

            if candidates:
                # Sort by distance to expected location (Primary sorting)
                candidates.sort(key=lambda x: x['dist'])
                
                best_match = candidates[0]['text']
                match_type = candidates[0]['type']
                match_dist = candidates[0]['dist']
                
                if VERBOSE_OCR_LOGS:
                    print(f"      🛡️  Deep Verify Found: {best_match} (dist={match_dist:.1f}, type={match_type})")
                
                # LOGIC: Text Layer is the Ground Truth (99% Accuracy Source)
                current_nospaces = voter_id_text.replace(' ', '').strip().upper() if voter_id_text else ""
                
                # If we found a text layer match that looks like a Voter ID, use it.
                # STRICTER TOLERANCE: Reduced from 200 to 75 to ensure we don't accidentally pick a neighbor's ID
                # This ensures "5 is 5" and "6 is 6" by verifying we are looking at the EXACT right text element.
                if match_dist < 75:
                    if best_match != current_nospaces:
                        if current_nospaces:
                             print(f"      ⚠️  MISMATCH DETECTED. Starting Step-by-Step Digit Check:")
                             
                             # Compare Digit by Digit
                             max_len = max(len(best_match), len(current_nospaces))
                             txt_padded = best_match.ljust(max_len)
                             ocr_padded = current_nospaces.ljust(max_len)
                             
                             for i in range(max_len):
                                 c_txt = txt_padded[i]
                                 c_ocr = ocr_padded[i]
                                 
                                 if c_txt != c_ocr:
                                     print(f"         Step {i+1}: OCR '{c_ocr}' != Text '{c_txt}' -> ENFORCING Text Layer '{c_txt}'")
                                     if (c_ocr == '6' and c_txt == '5') or (c_ocr == '5' and c_txt == '6'):
                                         print(f"                  🛡️  CRITICAL FIX: 5/6 Ambiguity Resolved. Strictly using '{c_txt}'")
                             
                             print(f"      ✅ CORRECTION COMPLETE: Replaced '{current_nospaces}' with '{best_match}'")
                        else:
                             print(f"      ✅ RECOVERY: Found '{best_match}' from TextLayer")
                        
                        voter_id_text = best_match
                        voter_id_confidence = 1.0
                        voter_id_method = f'text_layer_deep_{match_type}'
                        cell_stats[f'text_layer_deep_{match_type}'] = 1
                    else:
                        print(f"      ✨ PERFECT INTEGRITY: '{best_match}' is identical in OCR and Text Layer.")
                        voter_id_confidence = 1.0
                else:
                    print(f"      ⚠️  Ignored Text Layer match (too far: {match_dist:.1f}px) - Risk of mismatch")
            
            else:
                 pass # No text layer candidate found
                 
        except Exception as e:
            print(f"      ⚠️  Deep Verification Error: {str(e)}")

        # Clean voter ID (STRICT ABC1234567 REQUIREMENT)
        if voter_id_text:
            # Normalize: Uppercase and remove ALL punctuations/spaces
            voter_id_text = re.sub(r'[^A-Z0-9]', '', voter_id_text.upper())
            
            # User Requirement: Strictly ABC1234567 (10 chars, 3 alpha + 7 digits)
            if len(voter_id_text) >= 9:
                # Truncate or pad if slightly off
                if len(voter_id_text) > 10:
                     voter_id_text = voter_id_text[:10]
                
                # If we have 10 chars, strictly enforce the 3-7 pattern
                if len(voter_id_text) == 10:
                    prefix = voter_id_text[:3]
                    suffix = voter_id_text[3:]
                    
                    # Force prefix to be alphabetic
                    prefix = prefix.replace('0', 'O').replace('1', 'I').replace('2', 'Z').replace('5', 'S').replace('8', 'B')
                    # Remove any remaining digits in prefix if possible
                    prefix = re.sub(r'[0-9]', 'O', prefix) 
                    
                    # Force suffix to be numeric
                    suffix = suffix.replace('O', '0').replace('I', '1').replace('L', '1').replace('S', '5').replace('G', '6').replace('B', '8').replace('Z', '2').replace('Q', '0')
                    # Remove any remaining letters in suffix if possible
                    suffix = re.sub(r'[A-Z]', '0', suffix)
                    
                    voter_id_text = prefix + suffix
            
            # Additional fallback for extremely long merged strings
            elif len(voter_id_text) > 15:
                # Find best EPIC match within the blob
                epic_matches = re.findall(r'[A-Z]{3}[0-9]{7}', voter_id_text)
                if epic_matches:
                    voter_id_text = epic_matches[0]
                else:
                    voter_id_text = voter_id_text[:10]
        
        # DEBUG: Log raw voter ID for troubleshooting
        print(f"      🔍 DEBUG Page {page_num+1}, Row {row+1}, Col {col+1}:")
        print(f"         Raw Voter ID: '{voter_id_text}'")
        print(f"         Voter ID Length: {len(voter_id_text) if voter_id_text else 0}")
        print(f"         Voter ID Confidence: {voter_id_confidence:.2f}")
        print(f"         Has Photo: {bool(photo_base64 and len(photo_base64) > 0)}")
        
        # Skip logic - Initialized to False (Check mandatory fields at the end)
        should_skip = False
        skip_reason = ""
        
        # Check for photo (Still useful for logging)
        has_photo = photo_base64 and len(photo_base64) > 0
        
        # Determine if we have a valid voter ID
        has_valid_voter_id = False
        if voter_id_text and len(voter_id_text.strip()) >= 5:
             has_valid_voter_id = True
             print(f"         ✓ Voter ID found: '{voter_id_text}'")
        else:
             print(f"         ✗ No valid voter ID found")
             if not voter_id_text:
                 voter_id_text = ""
        
        # Log the decision to proceed with full extraction for evaluation
        voter_id_display = voter_id_text[:20] if voter_id_text else "[No ID]"
        photo_status = "Yes" if has_photo else "No"
        print(f"      📝 Evaluating Page {page_num+1}, Row {row+1}, Col {col+1}: VoterID='{voter_id_display}', Photo={photo_status}")
        
        # === EXTRACT FULL MARATHI TEXT ===
        # Try to get text from PDF text layer first (for digital PDFs)
        full_text = ""
        text_method = "none"
        
        try:
            # cell_full_rect already defined at start of card
            
            # 1. Try PDF Text Layer (HIGH SPEED PRIORITY)
            if local_cell_words:
                text_layer_content = _extract_text_fast(cell_full_rect, local_cell_words)
            else:
                text_layer_content = page.get_text("text", clip=cell_full_rect).strip()
            
            # Lower thresholds for trusting the text layer (even 1 character might be a serial no)
            english_chars = len(re.findall(r'[A-Za-z0-9]', text_layer_content))
            
            # Check if text layer has meaningful content
            if english_chars > 2 or len(text_layer_content) > 5:
                # Digital PDF found! (More accurate than OCR)
                print(f"      📝 Text Layer found. Using Text Layer.")
                full_text = text_layer_content
                text_method = "pdf_text_layer"
            
            else:
                # Scanned PDF or broken text layer -> Use OCR
                print(f"      📄 No digital text found. Using Intelligent OCR...")
                
                if local_ocr_processor:
                    if master_page_img and master_page_scale:
                         s = master_page_scale
                         header_offset = extraction_limits[0]
                         left = int(cell_full_rect.x0 * s)
                         top = int((cell_full_rect.y0 - header_offset) * s)
                         right = int(cell_full_rect.x1 * s)
                         bottom = int((cell_full_rect.y1 - header_offset) * s)
                         cell_full_crop = master_page_img.crop((max(0,left), max(0,top), right, bottom))
                    else:
                         cell_full_pix = page.get_pixmap(clip=cell_full_rect, dpi=400, alpha=False)
                         cell_full_crop = Image.frombytes("RGB", [cell_full_pix.width, cell_full_pix.height], cell_full_pix.samples)

                    res = local_ocr_processor.extract_full_cell_text(image=cell_full_crop, force_marathi=False)
                    full_text = res.get('text', '')
                    text_method = res.get('method', 'ocr_master_cell')
        
        except Exception as e:
            print(f"      ⚠️  Text Extraction Error: {str(e)}")
            
        # === EXTRACT ADDITIONAL FIELDS ===
        additional_fields = {}
        fields_config = cell_template.get('fields', {})
        
        if local_ocr_processor and fields_config:
            # Redundant rendering removed - using master_page_img in field loop
            pass

            for field_key, field_box in fields_config.items():
                if field_key in ['voterID', 'photo']: continue
                
                try:
                    f_x = field_box.get('x', 0) * scale_x
                    f_y = field_box.get('y', 0) * scale_y
                    f_w = field_box.get('width', 0) * scale_x
                    f_h = field_box.get('height', 0) * scale_y
                    
                    key_lower = field_key.lower()
                    
                    # 1. SPECIAL PADDING FOR ALPHA FIELDS (Better for misalignment)
                    if any(k in key_lower for k in ['name', 'relative']):
                        field_rect = fitz.Rect(
                            cell_x + f_x - 10,  # More left padding for long names
                            cell_y + f_y - 3, 
                            cell_x + f_x + f_w + 10, # More right padding
                            cell_y + f_y + f_h + 3
                        )
                    elif any(k in key_lower for k in ['age', 'gender']):
                        field_rect = fitz.Rect(
                            cell_x + f_x - 5, 
                            cell_y + f_y - 2, 
                            cell_x + f_x + f_w + 5, 
                            cell_y + f_y + f_h + 2
                        )
                    else:
                        field_rect = fitz.Rect(cell_x + f_x, cell_y + f_y, cell_x + f_x + f_w, cell_y + f_y + f_h)
                    
                    # Strategy for High Speed & Accuracy: Robust Digital Text Extraction
                    use_layer_text = False
                    clean_val = ""
                    raw_text = ""
                    field_res = {}

                    try:
                        # HIGH-SPEED DIGITAL PATH: Logic for text layer extraction
                        layer_rect = fitz.Rect(field_rect.x0 - 5, field_rect.y0 - 2, field_rect.x1 + 5, field_rect.y1 + 2)
                        if local_cell_words:
                            layer_text = _extract_text_fast(layer_rect, local_cell_words)
                        else:
                            layer_text = page.get_text("text", clip=layer_rect).strip()
                        
                        if layer_text and len(layer_text) >= 2:
                            # 🛡️ CLEAN WATERMARKS (USER REQUEST: EXTREME CLEANLINESS)
                            # Removing common watermark artifacts directly from text layer
                            watermarks = ['STATE ELECTION', 'COMMISSION', 'INDIA', 'AVAILABLE', 'COUNCIL', 'ASSEMBLY', 'ELECTORAL', 'ROLL', 'BENGALURU', 'KARNATAKA']
                            clean_layer = layer_text
                            for wm in watermarks:
                                clean_layer = re.sub(re.escape(wm), '', clean_layer, flags=re.IGNORECASE).strip()
                            
                            if clean_layer and len(clean_layer) >= 1:
                                clean_val = clean_layer
                                raw_text = clean_layer
                                field_res = {'method': 'text_layer_optimized', 'text': clean_layer, 'raw_text': clean_layer}
                                use_layer_text = True
                    except: pass

                    if not use_layer_text:
                        # 🖼️ OCR Path - USE MASTER IMAGE CROP (ZERO RENDERING DELAY)
                        if master_page_img and master_page_scale:
                            s = master_page_scale
                            header_offset = extraction_limits[0] 
                            left = int(field_rect.x0 * s)
                            top = int((field_rect.y0 - header_offset) * s)
                            right = int(field_rect.x1 * s)
                            bottom = int((field_rect.y1 - header_offset) * s)
                            
                            left, top = max(0, left), max(0, top)
                            crop_img = master_page_img.crop((left, top, right, bottom))
                        else:
                            field_pix = page.get_pixmap(clip=field_rect, dpi=400, alpha=False)
                            crop_img = Image.frombytes("RGB", [field_pix.width, field_pix.height], field_pix.samples)
                        
                        field_res = local_ocr_processor.extract_full_cell_text(image=crop_img, force_marathi=False)
                        raw_text = field_res.get('raw_text', '').strip()
                        clean_val = field_res.get('text', '').strip()
                    
                    if not clean_val:
                        clean_val = raw_text or ""
                                  # === FIELD CLEANING ===
                    if 'name' in key_lower:
                        is_rel = 'relative' in key_lower
                        
                        if is_rel:
                            # 1. ENHANCED RELATIVE NAME EXTRACTION: Split by Colon (User Requested)
                            curr_val = clean_val if clean_val else raw_text
                            
                            if ':' in curr_val:
                                # Use the LAST colon to ensure we only get the actual Name (User Requested)
                                parts = curr_val.rsplit(':', 1)
                                rel_type_part = parts[0].strip()
                                name_part = parts[1].strip()
                                
                                # Sanitize only the name part
                                finalized_name = TranslitHelper.sanitize_name(name_part, is_relative=True)
                                
                                additional_fields['relativeName'] = finalized_name
                                additional_fields['relativeNameEnglish'] = finalized_name
                                additional_fields['relativeNameKannada'] = TranslitHelper.translate_to_kannada(finalized_name)
                                
                                # Strictly map to H, F, M, O based on the part before colon
                                additional_fields['relationType'] = TranslitHelper.map_relation_type(rel_type_part)
                            else:
                                # Standard Fallback
                                clean_val = TranslitHelper.sanitize_name(clean_val, is_relative=True)
                                additional_fields['relativeName'] = clean_val
                                additional_fields['relativeNameEnglish'] = clean_val
                                additional_fields['relativeNameKannada'] = TranslitHelper.translate_to_kannada(clean_val)
                                # Try to get relation type from full text
                                additional_fields['relationType'] = TranslitHelper.map_relation_type(raw_text)
                        
                        else:
                            # Primary Name
                            clean_val = TranslitHelper.sanitize_name(clean_val, is_relative=False)
                            additional_fields['name'] = clean_val
                            additional_fields['nameEnglish'] = clean_val
                            additional_fields['nameKannada'] = TranslitHelper.translate_to_kannada(clean_val)

                    elif 'age' in key_lower:
                        # AGGRESSIVE AGE EXTRACTION (USER REQUEST: PERFECT EXTRACTION)
                        # Phase 1: Robust cleaning of the specific field box
                        val = clean_val.strip().upper()
                        # Advanced digit mapping for common OCR misreads
                        digit_map = {
                            'O': '0', 'D': '0', 'U': '0', 'Q': '0',
                            'I': '1', 'L': '1', 'J': '1', 'T': '7',
                            'Z': '2', 'A': '4', 'E': '8', 'G': '6', 'B': '8',
                            'S': '5', 'V': '0', 'H': '4', 'Y': '4', 'M': '1'
                        }
                        for k, v in digit_map.items():
                            val = val.replace(k, v)
                        
                        # Find all digit sequences
                        potential_ages = re.findall(r'\d+', val)
                        
                        # Phase 2: Fallback to raw text if clean_val failed
                        if not potential_ages:
                            val_raw = raw_text.strip().upper()
                            for k, v in digit_map.items():
                                val_raw = val_raw.replace(k, v)
                            potential_ages = re.findall(r'\d+', val_raw)
                        
                        # Phase 3: Aggressive Fallback to Full Cell Text (Handles Misalignment)
                        # This is the "Safety Net" for 99% accuracy
                        age_val = ""
                        
                        # Labels for Age in multiple languages with fuzzy patterns
                        age_labels = ['AGE', 'VAYASSU', 'ವಯಸ್ಸು', 'VAY', 'VAYU', 'வயದು', 'AAYU', 'UMR', 'வயது', 'ಉಯರಂ', 'वय', 'आयु', 'उम्र', 'A:', 'A-', 'AG:']
                        
                        # Helper to search for age in a blob
                        def find_age_contextual(blob):
                            if not blob: return ""
                            blob_norm = TranslitHelper.normalize_digits(blob).upper().translate(GLOBAL_DIGIT_TRANS)
                            blob_search = re.sub(r'[^A-Z0-9\s\:\-\.\|]', ' ', blob_norm)
                            for label in AGE_LABELS:
                                pattern = re.escape(label) + r'[\s\:\-\.\|]*(\d+(?:\s*\d+)*)'
                                matches = re.findall(pattern, blob_search)
                                if matches:
                                    for m in reversed(matches):
                                        m_clean = m.replace(' ', '')
                                        try:
                                            if m_clean and 18 <= int(m_clean) <= 110: return m_clean
                                        except: continue
                            return ""

                        age_val = find_age_contextual(clean_val) or find_age_contextual(raw_text)
                        if not age_val and local_cell_words:
                            age_val = find_age_contextual(_extract_text_fast(cell_full_rect, local_cell_words))
                        if not age_val: age_val = find_age_contextual(full_text)
                            
                        # Fallback & Last Resort
                        if not age_val:
                            # 1. Join fragments
                            v_cl = clean_val.upper().translate(GLOBAL_DIGIT_TRANS)
                            seqs = re.findall(r'\d+', v_cl)
                            if not seqs: seqs = re.findall(r'\d+', raw_text.upper().translate(GLOBAL_DIGIT_TRANS))
                            if len(seqs) >= 2 and all(len(p) == 1 for p in seqs[:2]):
                                seqs = [seqs[0] + seqs[1]] + seqs[2:]
                            
                            normalized = [TranslitHelper.normalize_digits(n).translate(GLOBAL_DIGIT_TRANS) for n in seqs]
                            plausible = [n for n in normalized if n.isdigit() and 18 <= int(n) <= 110]
                            if plausible: age_val = plausible[-1]
                        
                        if not age_val:
                            blobs = [full_text, _extract_text_fast(cell_full_rect, local_cell_words) if local_cell_words else ""]
                            for blob in blobs:
                                nums = re.findall(r'\d+', TranslitHelper.normalize_digits(blob).translate(GLOBAL_DIGIT_TRANS))
                                candidates = [n for n in nums if 18 <= int(n) <= 110]
                                if candidates:
                                    h_no = str(additional_fields.get('houseNo', ''))
                                    for c in reversed(candidates):
                                        if c != h_no:
                                            age_val = c
                                            break
                                    if age_val: break
                                    age_val = candidates[-1]
                                    break

                        # Final Integer Output
                        final_age = ""
                        if age_val:
                            numeric = re.sub(r'[^0-9]', '', age_val)
                            try:
                                v = int(numeric)
                                if 18 <= v <= 110: final_age = str(v)
                                elif v > 110 and 18 <= int(numeric[-2:]) <= 110: final_age = str(int(numeric[-2:]))
                            except: pass
                        additional_fields['age'] = final_age

                    elif 'gender' in key_lower:
                        # Use enhanced map_gender which handles F/M shortcuts
                        g = TranslitHelper.map_gender(clean_val)
                        if not g: g = TranslitHelper.map_gender(raw_text)
                        
                        additional_fields['gender'] = g
                        additional_fields['genderEnglish'] = g
                        additional_fields['genderKannada'] = TranslitHelper.translate_to_kannada(g)

                    elif any(k in key_lower for k in ['booth', 'center', 'address', 'station']):
                        clean_val = TranslitHelper.clean_booth_info(clean_val)
                        if 'address' in key_lower:
                            additional_fields['boothAddress'] = clean_val
                            additional_fields['boothAddressEnglish'] = clean_val
                            additional_fields['boothAddressKannada'] = TranslitHelper.translate_to_kannada(clean_val)
                        else:
                            additional_fields['boothCenter'] = clean_val
                            additional_fields['boothCenterEnglish'] = clean_val
                            additional_fields['boothCenterKannada'] = TranslitHelper.translate_to_kannada(clean_val)

                    elif 'relation' in key_lower:
                        # 1. Specialized relation type extraction
                        curr_rel = clean_val if clean_val else raw_text
                        rt_to_map = curr_rel.split(':', 1)[0].strip() if ':' in curr_rel else curr_rel
                        additional_fields['relationType'] = TranslitHelper.map_relation_type(rt_to_map)

                    elif 'house' in key_lower:
                        # HIGH-SPEED HOUSE NUMBER (GLOBAL MAP & LABELS)
                        curr_val = clean_val if clean_val else raw_text
                        def find_house_no_near_labels(blob):
                            if not blob: return ""
                            # ALPHANUMERIC SUPPORT: Use only Indian digit normalization, skip aggressive OCR digit map
                            blob_norm = TranslitHelper.normalize_digits(blob).upper()
                            for label in HOUSE_LABELS:
                                pattern = re.escape(label) + r'[\s\:\-\.\|]*([A-Z0-9/\-]+)'
                                matches = re.findall(pattern, blob_norm)
                                if matches:
                                    for m in matches:
                                        # Keep the match if it contains at least one digit
                                        if any(c.isdigit() for c in m): return m
                            return ""

                        house_val = find_house_no_near_labels(curr_val)
                        if not house_val:
                            if local_cell_words:
                                house_val = find_house_no_near_labels(_extract_text_fast(cell_full_rect, local_cell_words))
                            if not house_val: house_val = find_house_no_near_labels(full_text)
                        if not house_val:
                            house_val = re.sub(r'^(?:HOUSE|H\.?\s*NO|HS|NO|NUM|H)\b[:\- .]*', '', curr_val, flags=re.IGNORECASE).strip()
                        if house_val:
                            house_val = house_val.upper() # Removed translate(GLOBAL_DIGIT_TRANS)
                            house_val = re.sub(r'[^A-Z0-9\s\/\-]', ' ', house_val)
                            house_val = ' '.join(house_val.split()).strip()
                        additional_fields['houseNo'] = house_val
                    elif any(k in key_lower for k in ['serial', 'assembly', 'ac', 'pc', 'part']):
                        num_val = re.sub(r'[^0-9/,\-]', '', clean_val)
                        if 'serial' in key_lower:
                            # User wants to add serial numbers manually, so keep it blank
                            additional_fields['serialNo'] = ""
                        elif any(k in key_lower for k in ['assembly', 'ac']):
                            additional_fields['assemblyNo'] = num_val
                        else:
                            additional_fields['partNo'] = num_val
                    
                    if field_key not in additional_fields:
                        additional_fields[field_key] = clean_val

                    # Update clean_val for logging so it shows the sanitized/mapped value
                    log_val = additional_fields.get(field_key, clean_val)
                    print(f"         > {field_key}: {log_val}")
                except Exception as ex:
                    print(f"         > {field_key}: Error ({str(ex)})")
        
        # === SMART FALLBACK (GRID PROTECTION) ===
        if full_text and (not additional_fields.get('nameEnglish') or len(additional_fields.get('nameEnglish', '')) < 2):
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            for line in lines:
                if any(k in line.lower() for k in ['name', 'nam']) and not any(k in line.lower() for k in ['husband', 'father', 'mother', 'other']):
                    detected = re.sub(r'^(?:Name|Nam)[:\- .]*', '', line, flags=re.IGNORECASE).strip()
                    if detected and len(detected) > 2:
                        name = TranslitHelper.sanitize_name(detected)
                        additional_fields['name'] = name
                        additional_fields['nameEnglish'] = name
                        additional_fields['nameKannada'] = TranslitHelper.translate_to_kannada(name)
                        break

        if full_text and (not additional_fields.get('relativeNameEnglish') or len(additional_fields.get('relativeNameEnglish', '')) < 2):
            rel_prefixes = ["Husband's", "Father's", "Mother's", "Other"]
            for prefix in rel_prefixes:
                pattern = f'{re.escape(prefix)}\\s*(?:Name)?[:\\- .]*(.*)'
                match = re.search(pattern, full_text, flags=re.IGNORECASE)
                if match:
                    detected = match.group(1).split('\n')[0].strip()
                    if detected and len(detected) > 2:
                        rel_name = TranslitHelper.sanitize_name(detected, is_relative=True)
                        additional_fields['relativeName'] = rel_name
                        additional_fields['relativeNameEnglish'] = rel_name
                        additional_fields['relativeNameKannada'] = TranslitHelper.translate_to_kannada(rel_name)
                        break

        # === SMART FALLBACK (GENDER RECOVERY) ===
        # If Gender is missing, scan the entire cell's full_text for recovery
        if full_text and not additional_fields.get('gender'):
             lines = [l.strip() for l in full_text.split('\n') if l.strip()]
             for line in lines:
                  g = TranslitHelper.map_gender(line)
                  if g:
                       additional_fields['gender'] = g
                       additional_fields['genderEnglish'] = g
                       additional_fields['genderKannada'] = TranslitHelper.translate_to_kannada(g)
                       break

        # === USER REQUEST: Mandatory Fields Filter (DISABLED TO PREVENT DATA LOSS) ===
        # We now include all records even if some fields are missing, but we still log the missing info.
        name_val = additional_fields.get('nameEnglish', '').strip()
        rel_name_val = additional_fields.get('relativeNameEnglish', '').strip()
        
        has_id = bool(voter_id_text and len(voter_id_text.strip()) >= 4)
        has_name = bool(name_val and len(name_val) >= 2)
        has_relative = bool(rel_name_val and len(rel_name_val) >= 2)
        
        # We only skip if the card is completely empty or junk (e.g., no ID AND no name)
        if not has_id and not has_name:
            # should_skip = True # Disabled to prevent skipping any data
            skip_reason = "Empty or junk record"
            print(f"      ⏭️  WOULD HAVE SKIPPED Page {page_num+1}, Row {row+1}, Col {col+1}: {skip_reason}")

        # Return result
        result = {
            'page': page_num + 1,
            'column': col + 1,
            'row': row + 1,
            'voterID': voter_id_text if voter_id_text else "",
            'full_text': full_text,
            'name': additional_fields.get('name', ''),
            'nameEnglish': additional_fields.get('nameEnglish', ''),
            'nameKannada': additional_fields.get('nameKannada', ''),
            'relativeName': additional_fields.get('relativeName', ''),
            'relativeNameEnglish': additional_fields.get('relativeNameEnglish', ''),
            'relativeNameKannada': additional_fields.get('relativeNameKannada', ''),
            'age': additional_fields.get('age', ''),
            'gender': additional_fields.get('gender', ''),
            'genderEnglish': additional_fields.get('genderEnglish', ''),
            'genderKannada': additional_fields.get('genderKannada', ''),
            'relationType': additional_fields.get('relationType', ''),
            'houseNo': additional_fields.get('houseNo', ''),
            'serialNo': additional_fields.get('serialNo', ''),
            'assemblyNo': additional_fields.get('assemblyNo', ''),
            'partNo': additional_fields.get('partNo', ''),
            'boothCenter': additional_fields.get('boothCenter', ''),
            'boothCenterEnglish': additional_fields.get('boothCenterEnglish', ''),
            'boothCenterKannada': additional_fields.get('boothCenterKannada', ''),
            'boothAddress': additional_fields.get('boothAddress', ''),
            'boothAddressEnglish': additional_fields.get('boothAddressEnglish', ''),
            'boothAddressKannada': additional_fields.get('boothAddressKannada', ''),
            'metadata': {
                'voter_id_confidence': voter_id_confidence,
                'photo_quality': photo_quality,
                'text_method': text_method,
                'skip_reason': skip_reason
            },
            'stats': cell_stats,
            'skipped': should_skip
        }
        return result
        
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return {'skipped': True, 'error': str(e)}

def detect_grid_offset(page, config, expected_first_cell_y):
    """
    Detects if the grid is shifted vertically on this page (e.g. larger header).
    Returns y_offset (positive = shifted down).
    """
    try:
        # Search area: Top 40% of page
        page_h = page.rect.height
        search_rect = fitz.Rect(0, 0, page.rect.width, page_h * 0.4)
        words = page.get_text("words", clip=search_rect)
        
        # Look for English anchors
        anchors_y = []
        for w in words:
            text = w[4].strip().lower()
        anchors_y.sort()
        
        # Find the first "cluster" of Y values. This corresponds to the first row of cells (Row 1).
        # The "Header Reference" for this config is usually where the first cell starts.
        
        # Let's say we find the "Name" label at Y=180.
        # We need to know where "Name" label SHOULD be in the static config.
        # This is hard to know exactly without the template reference.
        
        # ALTERNATE STRATEGY: Find the FIRST Horizontal Line that spans the page width
        # This marks the delimiter between Header and Grid.
        
        drawings = page.get_drawings()
        lines = []
        for p in drawings:
            r = p['rect']
            # Horizontal line, reasonable width > 300
            if r.height < 5 and r.width > 300 and r.y0 > 100 and r.y0 < page_h * 0.4:
                lines.append(r.y0)
        
        lines.sort()
        
        detected_start_y = 0
        
        if lines:
            # The last line in the top region likely separates header from data
            detected_start_y = lines[-1]
        elif anchors_y:
             # Fallback to text: Assume "Name" label is ~25px below the cell top
             detected_start_y = anchors_y[0] - 25
        else:
            return 0
            
        # Calculate Offset
        # We compare detected_start_y with `expected_first_cell_y` (from static config)
        # expected_first_cell_y is the TOP of the first cell (grid.y)
        
        offset = detected_start_y - expected_first_cell_y
        
        # Threshold: Ignore tiny shifts (<10px) to avoid jitter
        if abs(offset) < 10:
            return 0
            
        print(f"      📏 Dynamic Header Detect: Grid Start Y={detected_start_y:.1f} (Exp: {expected_first_cell_y:.1f}) -> Offset: {offset:.1f}")
        return offset
        
        dark_rows = np.where(row_means < threshold)[0]
        
        if len(dark_rows) > 0:
            # Group consecutive dark rows into "lines"
            lines_y = []
            if len(dark_rows) > 0:
                current_group = [dark_rows[0]]
                for i in range(1, len(dark_rows)):
                    if dark_rows[i] - dark_rows[i-1] <= 2: # Combine adjacent rows
                        current_group.append(dark_rows[i])
                    else:
                        # End of line group -> Take average Y
                        avg_y = sum(current_group) / len(current_group)
                        lines_y.append(avg_y)
                        current_group = [dark_rows[i]]
                
                # Add last group
                if current_group:
                    avg_y = sum(current_group) / len(current_group)
                    lines_y.append(avg_y)
            
            if lines_y:
                # Topmost line found in image coordinates
                top_line_px = lines_y[0]
                
                # Convert back to PDF coordinates
                # PDF Y = SearchMinY + (PixelY / ZoomFactor)
                top_line_pdf_y = search_min_y + (top_line_px / 2.0)
                
                # Assume this is the top grid line
                grid_y = config.get('grid', {}).get('y', 0)
                offset = top_line_pdf_y - grid_y
                
                if abs(offset) < 500:
                    print(f"      📸 Image-Align: Detected Grid Y={top_line_pdf_y:.1f} (Exp {grid_y}), Offset={offset:.1f}")
                    return offset

        return 0
        
    except Exception as e:
        print(f"      ⚠️  Auto-Align Error: {e}")
        return 0

# === GLOBAL CACHE FOR ALIGNMENT ===
ALIGNMENT_CACHE = {}

def is_cell_empty(pix_or_img, threshold=500):
    """
    Check if a cell is effectively empty (low ink density).
    Returns True if empty.
    """
    try:
        # FAST PATH: PIL extremas
        if isinstance(pix_or_img, fitz.Pixmap):
            # Convert Pixmap to PIL for fast extrema check
            img_pil = Image.frombytes("RGB", [pix_or_img.width, pix_or_img.height], pix_or_img.samples)
            extrema = img_pil.convert('L').getextrema()
            if extrema[1] - extrema[0] < 10: return True
            img = np.array(img_pil.convert('L'))
        elif isinstance(pix_or_img, Image.Image):
            extrema = pix_or_img.convert('L').getextrema()
            if extrema[1] - extrema[0] < 10: return True
            img = np.array(pix_or_img.convert('L'))
        else:
            return False
            
        # Threshold (Black text on white background)
        _, thresh = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)
        non_zero = cv2.countNonZero(thresh)
        return non_zero < threshold
    except:
        return False

def detect_page_alignment(page, config, file_id=None):
    """
    Detects the 'Anchor' Y position dynamically using multiple strategies:
    1. CV2 Horizontal Lines (Header-Grid separator)
    2. Text Anchors ("Name", "Age", "नाव", "वय")
    3. Voter ID Patterns (EPIC)
    """
    try:
        # 1. CHECK CACHE
        grid_y = config.get('grid', {}).get('y', 0)
        page_h = page.rect.height
        
        if file_id and file_id in ALIGNMENT_CACHE:
            cached_offset = ALIGNMENT_CACHE[file_id]
            # Verify if cached offset is sane
            if abs(cached_offset) < page_h * 0.5:
                return cached_offset

        # Search area: Top 50% of page
        search_region_h = page_h * 0.5
        search_rect = fitz.Rect(0, 0, page.rect.width, search_region_h)

        # STRATEGY 1: CV2 Horizontal Lines (Highly Reliable for clean scans)
        try:
            zoom = 150 / 72.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=search_rect)
            
            import cv2
            import numpy as np
            
            img_bytes = pix.tobytes("png")
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            
            # Canny + HoughLinesP
            edges = cv2.Canny(img, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=200, maxLineGap=10)
            
            if lines is not None:
                h_lines = sorted([line[0][1] / zoom for line in lines if abs(line[0][1] - line[0][3]) < 5])
                if h_lines:
                    # Find first major line starting after 100pt (likely top of grid)
                    for find_y in h_lines:
                        if find_y > 100:
                            offset = find_y - grid_y
                            if abs(offset) < page_h * 0.4:
                                print(f"      ⚓ Smart Align (Lines): Found at {find_y:.1f}, Offset={offset:.1f}")
                                if file_id: ALIGNMENT_CACHE[file_id] = offset
                                return offset
        except: pass

        # STRATEGY 2: Text Anchors (नाव, Name, वय, Age)
        words = page.get_text("words", clip=search_rect)
        anchors_y = []
        for w in words:
            text = w[4].strip()
            # Look for common labels found in every voter record
            if any(k in text for k in ['नाव', 'Name', 'Age', 'वय', 'लिंग', 'Gender', 'Husband', 'Father']):
                if w[1] > 100: # Below header
                    anchors_y.append(w[1])
        
        if anchors_y:
            anchors_y.sort()
            # Topmost label. In template, 'Name' might be at grid_y + 20
            # Let's assume the first label defines the top of the grid
            first_label_y = anchors_y[0]
            
            # Search for relative Y of 'Name' or 'Serial No' in template
            cell_template = config.get('cellTemplate', {})
            fields = cell_template.get('fields', {})
            rel_y = 20 # Default guess
            for fk, fv in fields.items():
                if 'name' in fk.lower() or 'serial' in fk.lower():
                    rel_y = fv.get('y', 20)
                    break
            
            actual_grid_y = first_label_y - rel_y
            offset = actual_grid_y - grid_y
            if abs(offset) < page_h * 0.4:
                print(f"      ⚓ Smart Align (Labels): Found at {actual_grid_y:.1f}, Offset={offset:.1f}")
                if file_id: ALIGNMENT_CACHE[file_id] = offset
                return offset

        # STRATEGY 3: Voter ID Regex (Original Fallback)
        voter_id_candidates = []
        for w in words:
            text = w[4].strip().upper().replace(" ", "")
            if EPIC_REGEX.match(text) or LOOSE_EPIC_REGEX.match(text):
                voter_id_candidates.append(w[1])

        if voter_id_candidates:
            voter_id_candidates.sort()
            first_id_y = voter_id_candidates[0]
            
            cell_template = config.get('cellTemplate', {})
            vid_box = cell_template.get('voterIdBox', {})
            vid_rel_y = vid_box.get('y', 10) 
            
            actual_grid_y = first_id_y - vid_rel_y
            offset = actual_grid_y - grid_y
            
            if abs(offset) < page_h * 0.4:
                print(f"      ⚓ Smart Align (EPIC): Found at {actual_grid_y:.1f}, Offset={offset:.1f}")
                if file_id: ALIGNMENT_CACHE[file_id] = offset
                return offset

        return 0.0
    except Exception as e:
        print(f"      ⚠️  Alignment Error: {e}")
        return 0.0

def process_single_page_worker(task_info):
    """
    Worker to process a WHOLE page.
    Optimized for high-speed digital extraction and 'Zero-Skip' integrity.
    """
    try:
        pdf_path = task_info['pdf_path']
        page_num = task_info['page_num']
        config = task_info['config']
        file_id = task_info.get('file_id', 'default')
        
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # === HIGH-SPEED DIGITAL DETECTION ===
        # Extract ALL words once to avoid hundreds of repetitive PDF parsing calls
        page_words = page.get_text("words")
        digital_mode = len(page_words) > 50 # Heuristic for digital PDF
        
        # === SMART ANCHOR ALIGNMENT ===
        y_offset = detect_page_alignment(page, config, file_id)
        
        # === GRID DEFINITION ===
        grid = config.get('grid', {})
        grid_rows, grid_cols = grid.get('rows', 4), grid.get('columns', 3)
        grid_x, grid_y = grid.get('x', 0), grid.get('y', 0)
        grid_width, grid_height = grid.get('width', 1500), grid.get('height', 2000)
        col_positions, row_positions = grid.get('colPositions'), grid.get('rowPositions')
        skip_header, skip_footer = config.get('skipHeaderHeight', 0), config.get('skipFooterHeight', 0)
        
        cell_width, cell_height = grid_width / grid_cols, grid_height / grid_rows
        extraction_limits = (skip_header, page.rect.height - skip_footer)
        
        # Reference scale
        first_cell_width = (col_positions[1] - col_positions[0]) if col_positions and len(col_positions) > 1 else cell_width
        first_cell_height = (row_positions[1] - row_positions[0]) if row_positions and len(row_positions) > 1 else cell_height

        # === GENERATE CELLS (ZERO-SKIP) ===
        manual_grid_cells = []
        for row in range(grid_rows):
            for col in range(grid_cols):
                cx = col_positions[col] if col_positions and col < len(col_positions) else grid_x + (col * cell_width)
                cy = row_positions[row] if row_positions and row < len(row_positions) else grid_y + (row * cell_height)
                cw = (col_positions[col+1] - col_positions[col]) if col_positions and col+1 < len(col_positions) else cell_width
                ch = (row_positions[row+1] - row_positions[row]) if row_positions and row+1 < len(row_positions) else cell_height
                
                cy += y_offset # Apply detected alignment
                manual_grid_cells.append({
                    'x': cx, 'y': cy, 'width': cw, 'height': ch,
                    'row': row, 'col': col,
                    'scale_x': cw / first_cell_width if first_cell_width else 1.0,
                    'scale_y': ch / first_cell_height if first_cell_height else 1.0,
                    'first_cell_width': first_cell_width,
                    'first_cell_height': first_cell_height
                })

        # === INITIALIZE PROCESSORS ===
        processors = {'ocr': None, 'photo': None, 'smart': None}
        if OCR_400DPI_AVAILABLE:
            proc_ocr = OCRProcessor400DPI()
            proc_ocr.set_ocr_language(config.get('language', 'mr'))
            processors['ocr'] = proc_ocr
        if PHOTO_PROCESSOR_AVAILABLE: processors['photo'] = PhotoProcessor()
        if SMART_DETECTOR_AVAILABLE: processors['smart'] = SmartDetector()

        # === MASTER RENDER (FOR HYBRID MODES) ===
        performance_mode = config.get('performanceMode', 'balanced')
        render_dpi = 200 if performance_mode == 'fast' else 300
        master_img = None
        try:
            pix = page.get_pixmap(dpi=render_dpi, alpha=False)
            master_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        except: pass

        # === EXTRACT PAGE FIELDS (DIGITAL PRIORITY) ===
        page_data = {'prabhag': config.get('prabhag', ''), 'boothNo': config.get('boothNo', '')}
        page_template = config.get('pageTemplate', {})
        
        if page_template:
            for field_key, box in page_template.items():
                try:
                    f_rect = fitz.Rect(box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
                    val = ""
                    
                    # High speed digital path for booth info
                    if digital_mode:
                        val = _extract_text_fast(f_rect, page_words)
                    
                    # OCR Fallback
                    if not val and processors['ocr']:
                        p = page.get_pixmap(clip=f_rect, dpi=300, alpha=False)
                        img = Image.frombytes("RGB", [p.width, p.height], p.samples)
                        res = processors['ocr'].extract_full_cell_text(image=img)
                        val = res.get('text', '')
                    
                    if any(k in field_key.lower() for k in ['booth', 'center', 'address']):
                        val = TranslitHelper.clean_booth_info(val)
                    
                    page_data[field_key] = val
                    if val:
                         page_data[f"{field_key}English"] = val
                         page_data[f"{field_key}Kannada"] = TranslitHelper.translate_to_kannada(val)
                except: pass

        # === PROCESS CELLS ===
        results = []
        for cell_info in manual_grid_cells:
            # Pass pre-extracted words for maximum speed
            res = _extract_cell_internal(
                page, page_num, cell_info, config, 
                extraction_limits, processors, 
                master_page_img=master_img, 
                master_page_scale=render_dpi/72.0,
                page_words=page_words
            )
            
            if res and not res.get('skipped'):
                for pk, pv in page_data.items(): res[pk] = pv
                # Ensure translation
                if res.get('name'):
                    res['nameEnglish'] = res['name']
                    res['nameKannada'] = TranslitHelper.translate_to_kannada(res['name'])
                if res.get('relativeName'):
                    res['relativeNameEnglish'] = res['relativeName']
                    res['relativeNameKannada'] = TranslitHelper.translate_to_kannada(res['relativeName'])
            
            results.append(res)
            
        doc.close()
        return results
    except Exception as e:
        print(f"CRITICAL PAGE ERROR: {e}")
        return []
        
    except Exception as e:
        print(f"CRITICAL ERROR in page worker {task_info.get('page_num')}: {e}")
        import traceback
        traceback.print_exc()
        return []

# GLOBAL WORKER CACHE
WORKER_OCR = None
WORKER_BOX = None

def init_worker():
    """
    Initializer for Multiprocessing Workers.
    Creates the OCR Processor AND Box Detector ONCE per process.
    """
    global WORKER_OCR, WORKER_BOX
    import os
    pid = os.getpid()
    try:
        # print(f"   🔧 Worker {pid}: Initializing Processors...")
        from ocr_processor_400dpi import OCRProcessor400DPI
        WORKER_OCR = OCRProcessor400DPI() 
        
        # Initialize BoxDetector if module available
        if BOX_DETECTOR_AVAILABLE:
            from box_detector import BoxDetector
            WORKER_BOX = BoxDetector()
            
        # print(f"   ✅ Worker {pid}: Ready.")
    except Exception as e:
        print(f"   ❌ Worker {pid} Init Failed: {e}")

def process_page(pdf_path, page_num, config, template, box_detector_config=None):
    """
    Process a single page (Worker Function).
    """
    try:
        import os
        pid = os.getpid()
        
        # Use Cached Processor
        global WORKER_OCR, WORKER_BOX
        
        if WORKER_OCR is None:
             # Fallback
             from ocr_processor_400dpi import OCRProcessor400DPI
             WORKER_OCR = OCRProcessor400DPI()
             
        local_ocr_processor = WORKER_OCR
        # Update quality mode based on config
        performance_mode = config.get('performanceMode', 'balanced')
        local_ocr_processor.set_quality_mode(performance_mode)
        
        # Use Cached Box Detector
        local_box_detector = None
        # FORCE ENABLE: If BoxDetector is available, we USE it for Dynamic Grid (User Request)
        # Verify if we should use it? User asked to "enable" it.
        # We'll treat it as enabled by default if the module is loaded.
        use_auto_grid = BOX_DETECTOR_AVAILABLE
        
        if use_auto_grid:
            if WORKER_BOX is None:
                from box_detector import BoxDetector
                WORKER_BOX = BoxDetector()
            local_box_detector = WORKER_BOX
        
        # Open PDF (Must be done in worker)
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # === SMART ANCHOR ALIGNMENT (WITH CACHING & CV2) ===
        # This part needs to be re-evaluated for worker context.
        # For now, assume alignment is done once per page.
        # If detect_page_alignment uses CV2, it might need its own processor.
        # For simplicity, let's assume it's lightweight or already cached.
        y_offset = detect_page_alignment(page, config, f"{pdf_path}_{page_num}") # Pass unique file_id
        detected_cells = []
        
        # === GENERATE CELLS DYNAMICALLY ===
        grid = config.get('grid', {})
        grid_rows = grid.get('rows', 4)
        grid_cols = grid.get('columns', 3)
        grid_x = grid.get('x', 0)
        grid_y = grid.get('y', 0)
        grid_width = grid.get('width', 1500)
        grid_height = grid.get('height', 2000)
        col_positions = grid.get('colPositions')
        row_positions = grid.get('rowPositions')
        skip_header = config.get('skipHeaderHeight', 0)
        skip_footer = config.get('skipFooterHeight', 0)
        
        cell_width = grid_width / grid_cols
        cell_height = grid_height / grid_rows
        
        extraction_limits = (skip_header, page.rect.height - skip_footer)
        
        first_cell_width = cell_width
        first_cell_height = cell_height
        if col_positions and len(col_positions) > 1:
            first_cell_width = col_positions[1] - col_positions[0]
        if row_positions and len(row_positions) > 1:
            first_cell_height = row_positions[1] - row_positions[0]

        # Box detection logic
        if use_auto_grid and local_box_detector:
            try:
                # Use cached local_box_detector (Already initialized in worker header)
                # ...
                
                detected_start_y = grid_y + y_offset
                safe_start_y = max(0, detected_start_y - 50)
                
                det_zoom = 150 / 72.0
                det_mat = fitz.Matrix(det_zoom, det_zoom)
                det_rect = fitz.Rect(0, safe_start_y, page.rect.width, page.rect.height - skip_footer)
                det_pix = page.get_pixmap(matrix=det_mat, clip=det_rect, alpha=False)
                
                import numpy as np
                import cv2
                if det_pix.n == 3:
                    det_img = np.frombuffer(det_pix.samples, dtype=np.uint8).reshape(det_pix.h, det_pix.w, 3)
                    det_img = cv2.cvtColor(det_img, cv2.COLOR_RGB2BGR)
                elif det_pix.n == 4:
                    det_img = np.frombuffer(det_pix.samples, dtype=np.uint8).reshape(det_pix.h, det_pix.w, 4)
                    det_img = cv2.cvtColor(det_img, cv2.COLOR_RGBA2BGR)
                else:
                    det_img = np.frombuffer(det_pix.samples, dtype=np.uint8).reshape(det_pix.h, det_pix.w, det_pix.n)
                    if det_pix.n == 1:
                        det_img = cv2.cvtColor(det_img, cv2.COLOR_GRAY2BGR)

                raw_boxes = local_box_detector.detect_boxes_from_cv_image(det_img)
                
                pdf_boxes = []
                for b in raw_boxes:
                    s = 1.0 / det_zoom
                    bx = b['x'] * s
                    by = (b['y'] * s) + safe_start_y
                    bw = b['width'] * s
                    bh = b['height'] * s
                    if (by + bh) <= (page.rect.height - skip_footer):
                         pdf_boxes.append({'x': bx, 'y': by, 'width': bw, 'height': bh})
                
                if pdf_boxes:
                    grid_info = local_box_detector.organize_into_grid(pdf_boxes)
                    d_rows = grid_info.get('rows', 0)
                    d_cols = grid_info.get('columns', 0)
                    if d_rows >= 2 and d_cols >= 2:
                        detected_grid = grid_info.get('grid', [])
                        for r_idx, row_list in enumerate(detected_grid):
                            for c_idx, box in enumerate(row_list):
                                final_w = box['width']
                                final_h = box['height']
                                detected_cells.append({
                                     'x': box['x'], 'y': box['y'], 'width': final_w, 'height': final_h,
                                     'row': r_idx, 'col': c_idx,
                                     'scale_x': final_w / first_cell_width, 'scale_y': final_h / first_cell_height,
                                     'first_cell_width': first_cell_width, 'first_cell_height': first_cell_height
                                })
            except Exception as e:
                print(f"      ⚠️  Auto-Grid Detection Error in worker for page {page_num+1}: {e}")

        cells_to_process = []
        if detected_cells and len(detected_cells) > 5:
             cells_to_process = detected_cells
        else:
             for col in range(grid_cols):
                 for row in range(grid_rows):
                     if col_positions and row_positions:
                         cx = col_positions[col] if col < len(col_positions) else grid_x + (col * cell_width)
                         cy = row_positions[row] if row < len(row_positions) else grid_y + (row * cell_height)
                         cw = (col_positions[col+1] - col_positions[col]) if col+1 < len(col_positions) else (grid_x+grid_width-cx)
                         ch = (row_positions[row+1] - row_positions[row]) if row+1 < len(row_positions) else (grid_y+grid_height-cy)
                     else:
                         cx = grid_x + (col * cell_width)
                         cy = grid_y + (row * cell_height)
                         cw, ch = cell_width, cell_height
                     
                     cy += y_offset
                         
                     cells_to_process.append({
                         'x': cx, 'y': cy, 'width': cw, 'height': ch,
                         'row': row, 'col': col,
                         'scale_x': cw / first_cell_width,
                         'scale_y': ch / first_cell_height,
                         'first_cell_width': first_cell_width,
                         'first_cell_height': first_cell_height
                     })

        # Initialize other processors locally if needed, or pass them.
        # For now, only OCR is globally cached.
        processors = {
            'ocr': local_ocr_processor,
            'photo': None,
            'smart': None,
            'box': None
        }
        
        try:
            if PHOTO_PROCESSOR_AVAILABLE:
                from photo_processor import PhotoProcessor
                processors['photo'] = PhotoProcessor()
        except: pass
        
        try:
            if SMART_DETECTOR_AVAILABLE:
                from smart_detector import SmartDetector
                processors['smart'] = SmartDetector()
        except: pass

        # BoxDetector is already used above for grid detection, if needed.
        # If it's needed for _extract_cell_internal, it should be initialized here.
        # For now, let's assume it's not needed or handled by the main process.
        # if BOX_DETECTOR_AVAILABLE:
        #     processors['box'] = BoxDetector()
        
        page_results = []
        
        # === PERFORMANCE OPTIMIZATION: RENDER PAGE ONCE ===
        # Choose DPI based on performance mode
        performance_mode = config.get('performanceMode', 'balanced')
        if performance_mode == 'fast':
            render_dpi = 250
        elif performance_mode == 'balanced':
            render_dpi = 300
        else:
            render_dpi = 400
            
        master_page_img = None
        master_page_scale = render_dpi / 72.0
        try:
            page_pix = page.get_pixmap(dpi=render_dpi, alpha=False)
            master_page_img = Image.frombytes("RGB", [page_pix.width, page_pix.height], page_pix.samples)
        except Exception as e:
            print(f"      ⚠️  Master page render failed in worker: {e}")

        # === EXTRACT PAGE LEVEL FIELDS (Booth Info) ===
        page_data = {}
        # New constant fields from config
        page_data['prabhag'] = config.get('prabhag', '')
        page_data['boothNo'] = config.get('boothNo', '')
        page_data['boothName'] = config.get('boothName', '')
        page_data['boothNameKannada'] = config.get('boothNameKannada', '')
        
        page_template = config.get('pageTemplate', {})
        
        if page_template and processors.get('ocr'):
             for field_key, field_box in page_template.items():
                    try:
                        r_x = field_box.get('x', 0)
                        r_y = field_box.get('y', 0)
                        r_w = field_box.get('width', 0)
                        r_h = field_box.get('height', 0)
                        
                        full_rect = fitz.Rect(r_x, r_y, r_x + r_w, r_y + r_h)

                        # Crop from master image
                        cropped_field_img = None
                        if master_page_img:
                            left = r_x * master_page_scale
                            top = r_y * master_page_scale
                            right = (r_x + r_w) * master_page_scale
                            bottom = (r_y + r_h) * master_page_scale
                            cropped_field_img = master_page_img.crop((left, top, right, bottom))
                        
                        # Determine if this is a booth-related field
                        is_booth_field = any(k in field_key.lower() for k in ['booth', 'center', 'address'])
                        # Rule: Force English OCR as requested by User
                        force_marathi_val = False 
                        
                        field_res = processors['ocr'].extract_full_cell_text(
                            image=cropped_field_img,
                            pdf_page=None if cropped_field_img else page,
                            rect=None if cropped_field_img else full_rect,
                            force_marathi=force_marathi_val 
                        )
                        
                        # RULE: For booth fields, use raw text + special cleaning for Z.P.
                        if is_booth_field:
                            val = field_res.get('raw_text', '').strip()
                            val = TranslitHelper.clean_booth_info(val)
                        else:
                            val = field_res.get('text', '').strip()
                            # CLEANUP: Remove common OCR garbage for standard fields
                            val = re.sub(r'[|:;!॥\--]', '', val).strip()
                            
                        val = ' '.join(val.split())
                        
                        page_data[field_key] = val
                        
                        if val:
                            try:
                                # RULE: Transliterate to English/Kannada if Devanagari is present
                                if any('\u0900' <= char <= '\u097F' for char in val):
                                     eng_v = TranslitHelper.transliterate_marathi_to_english(val)
                                     page_data[field_key] = eng_v # Force English in base field
                                     page_data[f"{field_key}English"] = eng_v
                                     page_data[f"{field_key}Kannada"] = TranslitHelper.transliterate_marathi_to_kannada(val)
                                else:
                                     page_data[field_key] = val
                                     page_data[f"{field_key}English"] = val
                                     page_data[f"{field_key}Kannada"] = TranslitHelper.translate_to_kannada(val)
                            except:
                                page_data[f"{field_key}English"] = ""
                                page_data[f"{field_key}Kannada"] = ""
                    except Exception as e:
                        pass

             # === SMART FALLBACK: Search for missing booth info if not found via template ===
             if (not page_data.get('boothCenter') or len(page_data.get('boothCenter', '')) < 5) and master_page_img:
                 try:
                     # Scan Top 15% of the page
                     header_h = int(page.rect.height * 0.15)
                     header_img = master_page_img.crop((0, 0, int(page.rect.width * master_page_scale), int(header_h * master_page_scale)))
                     
                     # Force English OCR (False) to avoid Marathi input as requested
                     header_res = processors['ocr'].extract_full_cell_text(image=header_img, force_marathi=False)
                     header_text = header_res.get('raw_text', '')
                     if header_text:
                         # Booth Center patterns
                         for p in [r'(?:मतदान केंद्राचे नाव|नाम|नाव)\s*[:\-]*\s*(.*)', r'(?:Polling Station Name|Station Name)\s*[:\-]*\s*(.*)']:
                             m = re.search(p, header_text, re.IGNORECASE)
                             if m:
                                 det = m.group(1).split('\n')[0].strip()
                                 if len(det) > 5:
                                     # FIX: Common Z.P. OCR error
                                     det = re.sub(r'\b2[,. ]+2\b', 'Z.P.', det)
                                     det = re.sub(r'\b2[,. ]+P\b', 'Z.P.', det)
                                     det = TranslitHelper.clean_booth_info(det); page_data['boothCenter'] = det
                                     try: 
                                         # RULE: Transliterate to English if Devanagari is present
                                         if any('\u0900' <= char <= '\u097F' for char in det):
                                             page_data['boothCenterEnglish'] = TranslitHelper.transliterate_marathi_to_english(det)
                                             page_data['boothCenterKannada'] = TranslitHelper.transliterate_marathi_to_kannada(det)
                                         else:
                                             page_data['boothCenterEnglish'] = det
                                             page_data['boothCenterKannada'] = TranslitHelper.translate_to_kannada(det)
                                     except: pass
                                     break
                         # Booth Address patterns
                         for p in [r'(?:मतदान केंद्राचे पत्ता|पत्ता)\s*[:\-]*\s*(.*)', r'(?:Polling Station Address|Address)\s*[:\-]*\s*(.*)']:
                             m = re.search(p, header_text, re.IGNORECASE)
                             if m:
                                 det = m.group(1).split('\n')[0].strip()
                                 if len(det) > 5:
                                     # FIX: Common Z.P. OCR error
                                     det = re.sub(r'\b2[,. ]+2\b', 'Z.P.', det)
                                     det = re.sub(r'\b2[,. ]+P\b', 'Z.P.', det)
                                     det = TranslitHelper.clean_booth_info(det); page_data['boothAddress'] = det
                                     try: 
                                         # RULE: Transliterate to English if Devanagari is present
                                         if any('\u0900' <= char <= '\u097F' for char in det):
                                             page_data['boothAddressEnglish'] = TranslitHelper.transliterate_marathi_to_english(det)
                                             page_data['boothAddressKannada'] = TranslitHelper.transliterate_marathi_to_kannada(det)
                                         else:
                                             page_data['boothAddressEnglish'] = det
                                             page_data['boothAddressKannada'] = TranslitHelper.translate_to_kannada(det)
                                     except: pass
                                     break
                 except: pass

        # Process Cells
        for cell_info in cells_to_process:
            result = _extract_cell_internal(
                page=page,
                page_num=page_num,
                cell_info=cell_info,
                config=config,
                extraction_limits=extraction_limits, 
                processors=processors,
                master_page_img=master_page_img,
                master_page_scale=master_page_scale
            )
            
            if result and not result.get('skipped'):
                for pk, pv in page_data.items():
                    result[pk] = pv
                
                try:
                    name_marathi = result.get('name', '')
                    if name_marathi:
                        eng_name = TranslitHelper.transliterate_marathi_to_english(name_marathi)
                        result['nameEnglish'] = eng_name
                        
                        # PRIORITY: High-accuracy offline transliteration from Marathi
                        if any('\u0900' <= char <= '\u097F' for char in name_marathi):
                            result['nameKannada'] = TranslitHelper.transliterate_marathi_to_kannada(name_marathi)
                        else:
                            # Fallback: Translate from English (Google / ITRANS)
                            result['nameKannada'] = TranslitHelper.translate_to_kannada(eng_name)
                    
                    rel_name_marathi = result.get('relativeName', '')
                    if rel_name_marathi:
                        eng_rel_name = TranslitHelper.transliterate_marathi_to_english(rel_name_marathi)
                        result['relativeNameEnglish'] = eng_rel_name
                        
                        # PRIORITY: High-accuracy offline transliteration from Marathi
                        if any('\u0900' <= char <= '\u097F' for char in rel_name_marathi):
                            result['relativeNameKannada'] = TranslitHelper.transliterate_marathi_to_kannada(rel_name_marathi)
                        else:
                            # Fallback: Translate from English (Google / ITRANS)
                            result['relativeNameKannada'] = TranslitHelper.translate_to_kannada(eng_rel_name)
                            
                except Exception as e:
                    print(f"      Translation error in worker: {e}")
                    pass
            
            page_results.append(result)
            
        doc.close()
        return page_results
        
    except Exception as e:
        print(f"CRITICAL ERROR in page worker {page_num}: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_grid_vertical_enhanced(pdf_bytes, config, pdf_path=None):
    """
    Enhanced extraction with local OCR - OPTIMIZED FOR LARGE FILES
    Refactored to process by PAGE instead of by CELL to reduce overhead.
    """
    import time
    import tempfile
    import multiprocessing as mp
    
    # Start timing
    start_time = time.time()
    
    print("=" * 60)
    print("ENHANCED EXTRACTION (Optimized) - Page Level Parallelism")
    print("=" * 60)
    
    # Ensure we have a file path (required for efficient multiprocessing)
    temp_file = None
    if not pdf_path:
        print("WARNING: No PDF path provided, creating temp file for workers...")
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        with os.fdopen(temp_fd, 'wb') as f:
            f.write(pdf_bytes)
        pdf_path = temp_path
        temp_file = temp_path
    
    try:
        # Open PDF to plan tasks
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"PDF opened: {total_pages} pages")
        
        # Calculate valid page range
        skip_start = config.get('skipPagesStart', 0)
        skip_end = config.get('skipPagesEnd', 0)
        start_page = skip_start
        end_page = total_pages - skip_end
        
        print(f"Processing pages {start_page + 1} to {end_page}")
        
        # Prepare Config
        worker_config = {
            'grid': config.get('grid', {}),
            'cellTemplate': config.get('cellTemplate', {}),
            'pageTemplate': config.get('pageTemplate', {}),
            'skipHeaderHeight': config.get('skipHeaderHeight', 0),
            'skipFooterHeight': config.get('skipFooterHeight', 0),
            'prabhag': config.get('prabhag', '') or config.get('Prabhag', ''), # Handle case variants
            'boothNo': config.get('boothNo', '') or config.get('BoothNo', ''), # Handle case variants
            'boothName': config.get('boothName', '') or config.get('BoothName', ''),
            'boothNameKannada': config.get('boothNameKannada', '') or config.get('BoothNameKannada', ''),
            'performanceMode': config.get('performanceMode', 'balanced')
        }
        
        print(f"      DEBUG: Passing Prabhag='{worker_config['prabhag']}', BoothNo='{worker_config['boothNo']}' to workers")
        
        # PREPARE TASKS BY PAGE
        work_items = []
        
        for page_num in range(start_page, end_page):
            # Create Task for process_page function
            work_items.append((
                pdf_path,
                page_num,
                worker_config,
                config.get('cellTemplate', {}), # template argument for process_page
                config.get('boxDetectorConfig') # Pass box detector config if available
            ))
            
        print(f"\nCreated {len(work_items)} page tasks (OPTIMIZED)")
        print(f"Starting parallel processing with {CPU_WORKERS} workers...\n")
        
        # EXECUTE PARALLEL
        parallel_start = time.time()
        results_flat = []
        
        max_workers = CPU_WORKERS
        if max_workers > 1:
            try:
                # Pass initializer to create OCR Processor once per worker
                with mp.Pool(processes=max_workers, initializer=init_worker) as pool:
                    # We use starmap to unpack arguments
                    # process_page needs to be top-level pickleable. It is.
                    map_results = pool.starmap(process_page, work_items)
                    
                    # Flatten results (each process_page returns a list of voters)
                    for res_list in map_results:
                        if res_list:
                            results_flat.extend(res_list)
            except Exception as e:
                print(f"Parallel execution failed: {e}")
        else:
             results_flat = [item for t in work_items for item in process_single_page_worker(t)]

        print(f"Parallel time: {time.time() - parallel_start:.2f}s")
        
        # AGGREGATE STATS
        extracted_data = []
        stats = {'total_cells': 0, 'cells_skipped': 0}

        # Memory optimization: Process results in batches to reduce memory usage
        batch_size = 1000
        for i, res in enumerate(results_flat):
            if not res: continue
            stats['total_cells'] += 1

            if res.get('skipped', False):
                stats['cells_skipped'] += 1
                # Aggregate sub-stats
                for k,v in res.get('stats', {}).items():
                     stats[k] = stats.get(k, 0) + v
            else:
                extracted_data.append(res)
                for k,v in res.get('stats', {}).items():
                     stats[k] = stats.get(k, 0) + v

            # Memory optimization: Force garbage collection periodically
            if i % batch_size == 0 and i > 0:
                gc.collect()
        
        # Sort results by Serial No primarily, fallback to physical order
        def get_sort_key(x):
            s = x.get('serialNo')
            if s and isinstance(s, str):
                # Faster numeric extraction
                digits = "".join(filter(str.isdigit, s))
                if digits: return (0, int(digits))
            return (1, x.get('page', 0), x.get('row', 0), x.get('col', 0))

        extracted_data.sort(key=get_sort_key)
        
        total_time = time.time() - start_time
        print(f"Total Time: {total_time:.2f}s")
        print(f"Extracted: {len(extracted_data)}/{stats['total_cells']}")
        
        return {
            'extracted_data': extracted_data,
            'stats': {
                'records_extracted': len(extracted_data),
                'cells_processed': stats['total_cells'],
                'cells_skipped': stats['cells_skipped'],
                'extraction_time_seconds': round(total_time, 2)
            }
        }
        
    finally:
        # Cleanup temp file if we created one
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except: pass


def extract_grid_vertical(pdf_bytes, config, pdf_path=None):
    """
    Main extraction function - uses enhanced version with local OCR
    
    Returns:
        If enhanced version returns dict with stats, extract just the data list
        Otherwise returns the list directly for backward compatibility
    """
    result = extract_grid_vertical_enhanced(pdf_bytes, config, pdf_path=pdf_path)
    
    # If result is a dict with stats, return it as-is (new format)
    if isinstance(result, dict) and 'extracted_data' in result:
        return result
    
    # Otherwise return result directly (backward compatibility)
    return result


def clean_voter_id(text):
    """
    Clean and normalize voter ID text (fallback method)
    
    Args:
        text: Raw OCR text
    
    Returns:
        Cleaned voter ID text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common OCR errors
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Try to extract voter ID pattern (e.g., NOW1234567)
    # Common patterns: 3 letters followed by 7 digits
    pattern = r'[A-Z]{3}\d{7}'
    match = re.search(pattern, text.upper())
    if match:
        cleaned = match.group(0)
    else:
        # If no pattern match, return cleaned text
        cleaned = text.strip()
    
    # Remove trailing underscores (common OCR error)
    cleaned = cleaned.rstrip('_').strip()
    
    return cleaned


def test_tesseract():
    """
    Test if Tesseract is properly installed
    """
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {version}")
        
        # Check available languages
        langs = pytesseract.get_languages()
        print(f"Available languages: {langs}")
        
        if 'eng' not in langs:
            print("WARNING: English language data not found")
        if 'hin' not in langs:
            print("WARNING: Hindi language data not found")
        
        return True
    except Exception as e:
        print(f"Tesseract test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test enhanced extraction modules
    print("Testing Enhanced Extraction Modules...")
    print("=" * 60)
    
    # Test Tesseract installation
    print("\n1. Testing Tesseract OCR (fallback)...")
    test_tesseract()
    
    # Test advanced modules
    print("\n2. Testing Advanced Modules...")
    
    if ocr_processor_400dpi:
        print("  OK: 400 DPI OCR Processor: Available ✓")
    else:
        print("  FAIL: 400 DPI OCR Processor: Not available")
    
    if photo_processor:
        print("  OK: Photo Processor: Available")
    else:
        print("  FAIL: Photo Processor: Not available")
    
    if box_detector:
        print("  OK: Box Detector: Available")
    else:
        print("  FAIL: Box Detector: Not available")
    
    if smart_detector:
        print("  OK: Smart Detector: Available")
    else:
        print("  FAIL: Smart Detector: Not available")
    
    print("\n" + "=" * 60)
    print("Ready for enhanced extraction!")
    if ocr_processor_400dpi:
        print("Strategy: 400 DPI Local OCR ✓")
    else:
        print("Strategy: Standard Tesseract OCR")
    print("=" * 60)