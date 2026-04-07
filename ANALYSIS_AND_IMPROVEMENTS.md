# Code Analysis & Improvement Plan for Marathi OCR

## Current Flow Analysis

### 1. PDF Type Detection
**Status:** ❌ **NOT IMPLEMENTED**
- Currently treats all PDFs the same
- No distinction between text-based and image-based PDFs
- Always tries PDF text layer first (good strategy), but doesn't validate if PDF is actually text-based

### 2. OCR Handling
**Status:** ⚠️ **PARTIALLY IMPLEMENTED**
- Uses Tesseract OCR with `lang='eng+hin'` throughout
- **CRITICAL ISSUE:** Missing Marathi language support (`mar`/`mr`)
- Multi-strategy approach:
  1. PDF text layer extraction (fastest, most accurate)
  2. 400 DPI OCR processor with Tesseract
  3. Retry with 600 DPI + multiple PSM modes
  4. Ultra-aggressive fallback with 800 DPI
- Uses multiple preprocessing variants (contrast, sharpness, threshold, etc.)
- Location: `extractor.py` (lines 170-426), `ocr_processor_400dpi.py` (line 99)

### 3. Text Extraction Logic
**Status:** ⚠️ **VOTER ID FOCUSED, NOT MARATHI TEXT**
- Extracts voter IDs (alphanumeric patterns like ABC1234567)
- **No Marathi text extraction** - only focuses on voter ID numbers
- No line/paragraph reconstruction for Marathi text
- No text normalization for Devanagari script
- Pattern matching: `extractor.py` (lines 198-209), `ocr_processor_400dpi.py` (lines 212-260)

### 4. Excel Export Logic
**Status:** ✅ **BASIC IMPLEMENTATION**
- Simple structure: EPIC No + Base64 Image
- Uses `openpyxl` library
- No Marathi text columns
- No structured text export (names, addresses in Marathi)
- Location: `excel_generator.py`

## Identified Bottlenecks & Issues

### 1. Missing Marathi Language Support
- **Current:** `lang='eng+hin'` everywhere
- **Required:** `lang='eng+hin+mar'` or `lang='mar'`
- **Impact:** Poor OCR accuracy for Marathi (Devanagari) text

### 2. No PDF Type Detection
- **Issue:** Doesn't detect if PDF is text-based or image-based
- **Impact:** Unnecessary OCR processing for text-based PDFs
- **Solution:** Check if PDF has selectable text layer

### 3. No Marathi Text Normalization
- **Issue:** OCR output for Devanagari script may have errors
- **Impact:** Broken Marathi text (wrong characters, missing matras)
- **Solution:** Add normalization rules for Devanagari

### 4. No Line/Paragraph Reconstruction
- **Issue:** Raw OCR output is row-wise, may break words/lines
- **Impact:** Unreadable Marathi text in output
- **Solution:** Group OCR words by Y-coordinate, reconstruct lines

### 5. Limited Excel Structure
- **Issue:** Only exports Voter ID and image
- **Impact:** Marathi text (names, addresses) not exported
- **Solution:** Add columns for extracted Marathi text fields

## Improvement Plan

### Phase 1: Add Marathi Language Support
1. Update all Tesseract calls to include `mar` language
2. Verify Marathi language data is installed in Tesseract
3. Add fallback if Marathi not available

### Phase 2: PDF Type Detection
1. Create function to detect text-based vs image-based PDFs
2. Skip OCR for text-based PDFs (use text layer only)
3. Use OCR only for image-based PDFs

### Phase 3: Marathi Text Normalization
1. Add Devanagari character normalization
2. Fix common OCR errors (similar-looking characters)
3. Normalize Unicode variants

### Phase 4: Line & Paragraph Reconstruction
1. Extract OCR with bounding boxes (coordinates)
2. Group words by Y-coordinate (same line)
3. Join words to form lines
4. Join lines to form paragraphs

### Phase 5: Enhanced Excel Export
1. Add columns for Marathi text fields
2. Export structured data (name, address, etc.)
3. Preserve Unicode properly in Excel

### Phase 6: Optional - PaddleOCR Integration
1. Add PaddleOCR as alternative OCR engine
2. Compare accuracy: Tesseract vs PaddleOCR for Marathi
3. Use best performer or ensemble approach

## Implementation Strategy

**Do NOT rewrite everything** - integrate improvements into existing code:
- Keep function names and structure
- Add new functions, don't remove existing ones
- Replace Tesseract language parameter only where needed
- Add new modules for Marathi-specific processing
- Keep backward compatibility

