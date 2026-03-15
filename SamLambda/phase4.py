#!/usr/bin/env python3
"""
Phase 4 automation:
  1. Add SharedUtilsLayer to all functions that inline CORS headers
  2. Swap inline CORS dicts + error patterns to shared helpers in app.py files
  3. Generate smoke test file
"""
import os, re, sys

ROOT = os.path.dirname(__file__)
FUNCTIONS_DIR = os.path.join(ROOT, 'functions')
TEMPLATE = os.path.join(ROOT, 'template.yml')

# ── Functions that need the layer added in template.yml ──────────────────────
NEEDS_LAYER = [
    'GetNumQuestionTypesFunction',
    'GetQuestionTypeDataFunction',
    'GetAudioQuestionSummaryForVideoRecordingFunction',
    'GetNumValidQuestionsForQTypeFunction',
    'GetTotalValidAllQuestionsFunction',
    'InvalidateTotalValidQuestionsCacheFunction',
    'GetUserCompletedQuestionCountFunction',
    'GetQuestionTypesFunction',
    'GetUnansweredQuestionsFromUserFunction',
    'GetQuestionByIdFunction',
    'GetUnansweredQuestionsWithTextFunction',
    'GetProgressSummary2Function',
    'CreateRelationshipFunction',
    'GetRelationshipsFunction',
    'ValidateAccessFunction',
    'GetUploadUrlFunction',
    'GetMakerVideosFunction',
    'InitializeUserProgressFunction',
    'SendInviteEmailFunction',
    'IncrementUserLevel2Function',
    'GetStreakFunction',
    'MonthlyResetFunction',
    'StartTranscriptionFunction',
    'ProcessTranscriptFunction',
    'SummarizeTranscriptFunction',
]

# ── Step 1: patch template.yml ───────────────────────────────────────────────
with open(TEMPLATE) as f:
    tmpl = f.read()

tmpl_changed = 0
for fn in NEEDS_LAYER:
    # Find the function block — look for "FunctionName:\n    Type: AWS::Serverless::Function"
    # and insert "      Layers:\n        - !Ref SharedUtilsLayer\n" before the first
    # "      Handler:" or "      CodeUri:" line that follows.
    # Strategy: find the function header, then find the Properties block,
    # then insert Layers right after "    Properties:\n"
    pattern = rf'({re.escape(fn)}:\n    Type: AWS::Serverless::Function\n    Properties:\n)'
    replacement = r'\1      Layers:\n        - !Ref SharedUtilsLayer\n'
    new_tmpl, n = re.subn(pattern, replacement, tmpl)
    if n:
        tmpl = new_tmpl
        tmpl_changed += 1
        print(f'  template: added layer to {fn}')
    else:
        print(f'  template: WARNING — could not find {fn}', file=sys.stderr)

with open(TEMPLATE, 'w') as f:
    f.write(tmpl)
print(f'template.yml: {tmpl_changed} functions updated\n')

# ── Step 2: patch app.py files ───────────────────────────────────────────────
# Pattern to remove: the CORS_HEADERS dict (varies in allowed methods)
CORS_DICT_RE = re.compile(
    r"CORS_HEADERS\s*=\s*\{\s*"
    r"'Access-Control-Allow-Origin':[^\n]+\n"
    r"[^}]*\}\n?",
    re.DOTALL
)

# Replace 'headers': CORS_HEADERS  →  'headers': cors_headers(event)
# Replace 'headers': {... inline ...}  (single-line inline dicts in responses)
HEADERS_REF_RE = re.compile(r"'headers':\s*CORS_HEADERS")

# Replace str(e) error bodies that still exist (safety net — most done in phase 2)
STR_E_RE = re.compile(
    r"'body':\s*json\.dumps\(\{'error':\s*(?:f'[^']*\{str\(e\)\}[^']*'|str\(e\))\}\)"
)
SAFE_BODY = "'body': json.dumps({'error': 'A server error occurred. Please try again.'})"

app_changed = []

for dirpath, dirnames, filenames in os.walk(FUNCTIONS_DIR):
    dirnames[:] = [d for d in dirnames if d != '__pycache__']
    for fname in filenames:
        if fname != 'app.py':
            continue
        fpath = os.path.join(dirpath, fname)
        with open(fpath) as f:
            original = f.read()

        content = original

        # Skip files that already use the shared helper
        if 'from cors import cors_headers' in content:
            continue

        # Only touch files that have inline CORS
        if 'Access-Control-Allow-Origin' not in content:
            continue

        # Add imports after the last existing import line
        # Insert: from cors import cors_headers
        #         from responses import error_response
        # Find the last import line
        import_insert = 'from cors import cors_headers\nfrom responses import error_response\n'
        # Insert after the last top-level import block
        last_import_match = None
        for m in re.finditer(r'^(?:import |from )\S+.*$', content, re.MULTILINE):
            last_import_match = m
        if last_import_match:
            pos = last_import_match.end()
            content = content[:pos] + '\n' + import_insert + content[pos:]

        # Remove the CORS_HEADERS dict
        content = CORS_DICT_RE.sub('', content)

        # Replace 'headers': CORS_HEADERS with 'headers': cors_headers(event)
        content = HEADERS_REF_RE.sub("'headers': cors_headers(event)", content)

        # Fix any remaining str(e) leaks
        content = STR_E_RE.sub(SAFE_BODY, content)

        if content != original:
            with open(fpath, 'w') as f:
                f.write(content)
            rel = os.path.relpath(fpath, ROOT)
            app_changed.append(rel)
            print(f'  app.py: updated {rel}')

print(f'\napp.py files updated: {len(app_changed)}\n')

# ── Step 3: generate smoke tests ─────────────────────────────────────────────
tests_dir = os.path.join(ROOT, 'tests')
os.makedirs(tests_dir, exist_ok=True)

# Collect all handler module paths
handlers = []
for dirpath, dirnames, filenames in os.walk(FUNCTIONS_DIR):
    dirnames[:] = [d for d in dirnames if d != '__pycache__']
    for fname in filenames:
        if fname != 'app.py':
            continue
        rel = os.path.relpath(os.path.join(dirpath, fname), ROOT)
        # Convert path to module: functions/foo/bar/app.py -> functions.foo.bar.app
        module = rel.replace(os.sep, '.')[:-3]  # strip .py
        # Skip shared/ — not a handler
        if 'shared' in module:
            continue
        handlers.append(module)

handlers.sort()

smoke_test = '''"""
Smoke tests — verify every Lambda handler can be imported without errors.
Catches missing imports, syntax errors, and bad module-level code before deploy.

Run locally:
    cd SamLambda
    pip install pytest
    pytest tests/test_imports.py -v
"""
import sys
import os

# Add SamLambda root and shared layer path so imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'functions', 'shared', 'python'))

import importlib
import pytest

HANDLERS = [
'''
for h in handlers:
    smoke_test += f'    {repr(h)},\n'
smoke_test += ''']


@pytest.mark.parametrize('module_path', HANDLERS)
def test_handler_imports(module_path):
    """Each Lambda handler must be importable without errors."""
    importlib.import_module(module_path)
'''

smoke_path = os.path.join(tests_dir, 'test_imports.py')
with open(smoke_path, 'w') as f:
    f.write(smoke_test)
print(f'Smoke test written: tests/test_imports.py ({len(handlers)} handlers)\n')

# Write requirements-dev.txt
req_path = os.path.join(ROOT, 'requirements-dev.txt')
with open(req_path, 'w') as f:
    f.write('pytest>=7.0\n')
print('requirements-dev.txt written')
