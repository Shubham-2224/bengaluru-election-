
import os

file_path = r'd:\data mew code\aniket code\backend\python-service\extractor.py'

print(f"Searching in: {file_path}")
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'relation' in line.lower():
        print(f"Line {i+1}: {line.strip()}")
