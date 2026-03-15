#!/usr/bin/env python3

import os
import shutil
import sys
from pathlib import Path
from signal import signal, alarm, SIGALRM

SOURCE_DIR = "/Users/Oliver/Library/Mobile Documents/com~apple~CloudDocs/Documents - Mac/AI"
DEST_DIR = "/Users/Oliver/Downloads/backUpAI"
LOG_FILE = os.path.join(DEST_DIR, "inaccessible_files.log")

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError()

def copy_with_timeout(src, dst, timeout_sec=10):
    signal(SIGALRM, timeout_handler)
    alarm(timeout_sec)
    try:
        shutil.copy2(src, dst)
        alarm(0)
        return True
    except TimeoutError:
        alarm(0)
        return False
    except Exception:
        alarm(0)
        return False

# Create destination
os.makedirs(DEST_DIR, exist_ok=True)

# Initialize log
with open(LOG_FILE, 'w') as f:
    pass

# Count files
print("Counting files...")
files = [str(p) for p in Path(SOURCE_DIR).rglob('*') if p.is_file() and 'node_modules' not in p.parts]
total = len(files)
print(f"Total files: {total}")

# Process files
count = 0
read_errors = 0
copy_errors = 0
last_dir = ""
dir_errors = 0
skipped_dirs = set()

for file in files:
    count += 1
    pct = count * 100 // total
    file_rel = os.path.relpath(file, SOURCE_DIR)
    dest_file = os.path.join(DEST_DIR, file_rel)
    current_dir = os.path.dirname(file)
    
    # Skip if directory has issues
    if current_dir in skipped_dirs:
        read_errors += 1
        continue
    
    # Reset counter for new directory
    if current_dir != last_dir:
        last_dir = current_dir
        dir_errors = 0
    
    print(f"\r[{count}/{total} {pct}%] Read errors: {read_errors} | Copy errors: {copy_errors} | {file_rel[:50]:<50}", end='', flush=True)
    
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
    
    if os.access(file, os.R_OK):
        if not copy_with_timeout(file, dest_file):
            copy_errors += 1
            with open(LOG_FILE, 'a') as log:
                log.write(f"Copy failed: {file}\n")
    else:
        read_errors += 1
        dir_errors += 1
        with open(LOG_FILE, 'a') as log:
            log.write(f"Inaccessible: {file}\n")
        
        if dir_errors >= 10:
            skipped_dirs.add(current_dir)
            with open(LOG_FILE, 'a') as log:
                log.write(f"FOLDER ISSUE: Skipping {current_dir} (10+ read errors)\n")

print(f"\n\nDone! Copied: {count - read_errors - copy_errors} | Read errors: {read_errors} | Copy errors: {copy_errors} | Log: {LOG_FILE}")
