
import re
import os

file_path = r'd:\data mew code\aniket code\backend\python-service\extractor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Gender Logic
# Target block for Gender cleaning
gender_target_pattern = r"(if 'gender' in key_lower:.*?clean_val = re\.sub\(r'\[\^\\w\\s\\u0900-\\u097F\]', '', clean_val\)\.strip\(\).*?)(# === SPECIAL HANDLING FOR SERIAL NO)"
gender_replacement = r"""\1
                          
                          # Use TranslitHelper for Gender mapping (handles 'पर' -> 'Male', etc.)
                          gender_standard = TranslitHelper.map_gender(clean_val)
                          if gender_standard == "Male": clean_val = "पु"
                          elif gender_standard == "Female": clean_val = "स्री"
                          
                     \2"""

# Note: The above regex is risky due to formatting. Let's do a simpler line-based replacement.
lines = content.splitlines()
new_lines = []
skip_until = -1

for i, line in enumerate(lines):
    if i <= skip_until:
        continue
        
    # Check for Gender block (around line 975)
    if "if 'gender' in key_lower:" in line and "if 'gender' in key_lower and" not in line:
        # We found the gender block start
        new_lines.append(line)
        # Add next two lines (comment + regex)
        if i + 2 < len(lines):
            new_lines.append(lines[i+1])
            new_lines.append(lines[i+2])
            
            # Now insert our new logic
            indent = " " * 26
            new_lines.append("")
            new_lines.append(f"{indent}# Use TranslitHelper for Gender mapping (handles 'पर' -> 'पु', etc.)")
            new_lines.append(f"{indent}gender_standard = TranslitHelper.map_gender(clean_val)")
            new_lines.append(f"{indent}if gender_standard == \"Male\": clean_val = \"पु\"")
            new_lines.append(f"{indent}elif gender_standard == \"Female\": clean_val = \"स्री\"")
            
            # Skip the old Thai replacement lines (approx 6 lines)
            j = i + 3
            found_footer = False
            while j < len(lines) and j < i + 15:
                if "# === SPECIAL HANDLING FOR SERIAL NO" in lines[j]:
                    skip_until = j - 1
                    found_footer = True
                    break
                j += 1
            if not found_footer:
                # If we didn't find the footer, just proceed normally but we've added our code
                pass
    else:
        new_lines.append(line)

final_content = "\n".join(new_lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(final_content)

print("Extractor.py updated successfully via script.")
