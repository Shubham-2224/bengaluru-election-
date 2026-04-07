
import os

file_path = r'd:\data mew code\aniket code\backend\python-service\extractor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

new_lines = []
skip = 0

# Base indent for the if/elif blocks is around 20-21.
# Let's find it dynamically or just fix specific lines.

for i in range(len(lines)):
    if skip > 0:
        skip -= 1
        continue
        
    line = lines[i]
    
    # Fix the block at line 975 (approx)
    if "if 'gender' in key_lower:" in line and "if 'gender' in key_lower and" not in line and "elif" not in line:
        # Base indent for this 'if'
        indent_level = len(line) - len(line.lstrip())
        child_indent = " " * (indent_level + 5)
        
        new_lines.append(line)
        # Next few lines are cleaning and TranslitHelper
        new_lines.append(f"{child_indent}# Keep only Marathi/Devanagari characters and remove punctuation")
        new_lines.append(f"{child_indent}clean_val = re.sub(r'[^\\w\\s\\u0900-\\u097F]', '', clean_val).strip()")
        new_lines.append("")
        new_lines.append(f"{child_indent}# Use TranslitHelper for Gender mapping (handles 'पर' -> 'पु', etc.)")
        new_lines.append(f"{child_indent}gender_standard = TranslitHelper.map_gender(clean_val)")
        new_lines.append(f"{child_indent}if gender_standard == \"Male\": clean_val = \"पु\"")
        new_lines.append(f"{child_indent}elif gender_standard == \"Female\": clean_val = \"स्री\"")
        
        # Skip until the next block
        j = i + 1
        while j < len(lines) and "# === SPECIAL HANDLING FOR SERIAL NO" not in lines[j]:
            j += 1
        skip = j - i - 1
        continue

    # Fix the standardization block duplication (around line 1074)
    if "elif 'gender' in key_lower:" in line and i > 1000:
        # This is the standardization section
        indent_level = len(line) - len(line.lstrip())
        child_indent = " " * (indent_level + 5)
        
        new_lines.append(line)
        new_lines.append(f"{child_indent}# Use TranslitHelper for mapping to English (Male/Female)")
        new_lines.append(f"{child_indent}# We already mapped clean_val to 'पु'/'स्री' above, but map_gender handles that too.")
        new_lines.append(f"{child_indent}additional_fields['gender'] = clean_val # Standard key")
        new_lines.append(f"{child_indent}additional_fields['genderEnglish'] = TranslitHelper.map_gender(clean_val)")
        
        # Skip until the next elif
        j = i + 1
        while j < len(lines) and "elif 'age' in key_lower:" not in lines[j]:
            j += 1
        skip = j - i - 1
        continue
        
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(new_lines))

print("Extractor.py indentation and duplication fixed.")
