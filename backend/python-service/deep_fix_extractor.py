
import os

file_path = r'd:\data mew code\aniket code\backend\python-service\extractor.py'

print(f"Checking file: {file_path}")
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Line 1746: {lines[1745].strip()}")
print(f"Line 1771: {lines[1770].strip()}")
print(f"Line 1884: {lines[1883].strip()}")

# FIX 1: Ensure OCRProcessor400DPI is used everywhere
for i in range(len(lines)):
    if 'from ocr_processor_400dpi import OCRProcessor' in lines[i] and 'OCRProcessor400DPI' not in lines[i]:
        print(f"Fixing import at line {i+1}")
        lines[i] = lines[i].replace('OCRProcessor', 'OCRProcessor400DPI')
    if 'WORKER_OCR = OCRProcessor(dpi=300)' in lines[i]:
        print(f"Fixing initialization at line {i+1}")
        lines[i] = lines[i].replace('OCRProcessor(dpi=300)', 'OCRProcessor400DPI()')

# FIX 2: Initialize detected_cells
# Find the start of process_page
found_process_page = False
for i in range(len(lines)):
    if 'def process_page(' in lines[i]:
        # Start of function. Find first line after docstring or imports
        # Or just initialize it right before usage.
        found_process_page = True
        continue
    if found_process_page and 'y_offset = detect_page_alignment' in lines[i]:
        # Initialize here
        indent = " " * (len(lines[i]) - len(lines[i].lstrip()))
        lines.insert(i+1, f"{indent}detected_cells = []\n")
        print(f"Initialized detected_cells at line {i+2}")
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fix completed.")
