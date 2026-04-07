import os
import re

file_path = r'c:\banglore\voter_extraction_without_API\backend\python-service\extractor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find the Age block
# We'll use a regex that is more robust to small variations
pattern = re.compile(r'elif\s+\'age\'\s+in\s+key_lower:.*?(?=elif\s+\'gender\'\s+in\s+key_lower:)', re.DOTALL)

new_logic = """elif 'age' in key_lower:
                        # Phase 1: Contextual Search (High Precision for 'Full Selection')
                        age_val = ""
                        
                        def find_age_contextual(blob):
                            if not blob: return ""
                            # Apply multilingual digit normalization and global OCR correction
                            blob_norm = TranslitHelper.normalize_digits(blob).upper().translate(GLOBAL_DIGIT_TRANS)
                            # Strip non-alphanumeric noise to isolate labels and numbers
                            blob_search = re.sub(r'[^A-Z0-9\\s\\:\\-\\.\|]', ' ', blob_norm)
                            
                            for label in AGE_LABELS:
                                pattern = re.escape(label) + r'[\\s\\:\\-\\.\|]*(\\d+(?:\\s*\\d+)*)'
                                matches = re.findall(pattern, blob_search)
                                if matches:
                                    # PRIORITIZE LATER candidates (Age usually appears at the bottom/right)
                                    for m in reversed(matches):
                                        m_clean = m.replace(' ', '')
                                        if m_clean and 18 <= int(m_clean) <= 110: return m_clean
                            return ""

                        # Try Field crops, then Digital Layer, then Full Cell OCR
                        age_val = find_age_contextual(clean_val) or find_age_contextual(raw_text)
                        
                        if not age_val and local_cell_words:
                            age_val = find_age_contextual(_extract_text_fast(cell_full_rect, local_cell_words))
                        
                        if not age_val:
                            age_val = find_age_contextual(full_text)
                            
                        # Phase 2: Plausibility selection from OCR sequences
                        if not age_val:
                            v_clean = clean_val.upper().translate(GLOBAL_DIGIT_TRANS)
                            seqs = re.findall(r'\\d+', v_clean)
                            if not seqs:
                                v_raw = raw_text.upper().translate(GLOBAL_DIGIT_TRANS)
                                seqs = re.findall(r'\\d+', v_raw)
                            
                            if seqs:
                                # Join fragments like ['2', '8'] -> '28'
                                if len(seqs) >= 2 and all(len(p) == 1 for p in seqs[:2]):
                                     seqs = [seqs[0] + seqs[1]] + seqs[2:]
                                
                                normalized = [TranslitHelper.normalize_digits(n).translate(GLOBAL_DIGIT_TRANS) for n in seqs]
                                plausible = [n for n in normalized if n.isdigit() and 18 <= int(n) <= 110]
                                if plausible: age_val = plausible[-1] # Take last

                        # Phase 3: LAST RESORT - Global Numeric Scan
                        if not age_val:
                            blobs = [full_text, _extract_text_fast(cell_full_rect, local_cell_words) if local_cell_words else ""]
                            for blob in blobs:
                                nums = re.findall(r'\\d+', TranslitHelper.normalize_digits(blob).translate(GLOBAL_DIGIT_TRANS))
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

                        # Phase 4: Final Sanitization (Strict Integer)
                        final_age = ""
                        if age_val:
                            numeric = re.sub(r'[^0-9]', '', age_val)
                            try:
                                v = int(numeric)
                                if 18 <= v <= 110: final_age = str(v)
                                elif v > 110 and 18 <= int(numeric[-2:]) <= 110: final_age = str(int(numeric[-2:]))
                            except: pass
                        additional_fields['age'] = final_age

                    """

updated_content = pattern.sub(new_logic, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("Age logic updated successfully.")
