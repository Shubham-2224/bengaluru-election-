import os

file_path = r'c:\banglore\voter_extraction_without_API\backend\python-service\extractor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "elif 'house' in key_lower:" in line:
        new_lines.append(line) # Keep the elif line
        new_lines.append("                        # HIGH-SPEED HOUSE NUMBER (GLOBAL MAP & LABELS)\n")
        new_lines.append("                        curr_val = clean_val if clean_val else raw_text\n")
        new_lines.append("                        def find_house_no_near_labels(blob):\n")
        new_lines.append("                            if not blob: return \"\"\n")
        new_lines.append("                            blob_norm = TranslitHelper.normalize_digits(blob).upper().translate(GLOBAL_DIGIT_TRANS)\n")
        new_lines.append("                            for label in HOUSE_LABELS:\n")
        new_lines.append("                                pattern = re.escape(label) + r'[\\s\\:\\-\\.\|]*([A-Z0-9/\\-]+)'\n")
        new_lines.append("                                matches = re.findall(pattern, blob_norm)\n")
        new_lines.append("                                if matches:\n")
        new_lines.append("                                    for m in matches:\n")
        new_lines.append("                                        if any(c.isdigit() for c in m): return m\n")
        new_lines.append("                            return \"\"\n\n")
        new_lines.append("                        house_val = find_house_no_near_labels(curr_val)\n")
        new_lines.append("                        if not house_val:\n")
        new_lines.append("                            if local_cell_words:\n")
        new_lines.append("                                house_val = find_house_no_near_labels(_extract_text_fast(cell_full_rect, local_cell_words))\n")
        new_lines.append("                            if not house_val: house_val = find_house_no_near_labels(full_text)\n")
        new_lines.append("                        if not house_val:\n")
        new_lines.append("                            house_val = re.sub(r'^(?:HOUSE|H\\.?\\s*NO|HS|NO|NUM|H)\\b[:\\- .]*', '', curr_val, flags=re.IGNORECASE).strip()\n")
        new_lines.append("                        if house_val:\n")
        new_lines.append("                            house_val = house_val.upper().translate(GLOBAL_DIGIT_TRANS)\n")
        new_lines.append("                            house_val = re.sub(r'[^A-Z0-9\\s\\/\\-]', ' ', house_val)\n")
        new_lines.append("                            house_val = ' '.join(house_val.split()).strip()\n")
        new_lines.append("                        additional_fields['houseNo'] = house_val\n")
        skip = True
        continue
    
    if skip:
        # Stop skipping once we hit the next block
        if "elif any(k in key_lower for k in ['serial'" in line:
            skip = False
            new_lines.append(line)
        continue
    
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("House No logic updated via script.")
