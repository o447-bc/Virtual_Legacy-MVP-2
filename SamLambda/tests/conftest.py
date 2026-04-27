"""
conftest.py — adds each Lambda function directory to sys.path so that
sibling-module imports (e.g. `from conversation_state import ...` inside
wsDefault) resolve correctly during smoke tests.
"""
import sys
import os

_SAMLAMBDA_ROOT = os.path.dirname(os.path.dirname(__file__))

# Directories that contain sibling-module imports
_FUNCTION_DIRS = [
    os.path.join(_SAMLAMBDA_ROOT, 'functions', 'conversationFunctions', 'wsDefault'),
    os.path.join(_SAMLAMBDA_ROOT, 'functions', 'adminFunctions', 'adminThemes'),
    os.path.join(_SAMLAMBDA_ROOT, 'functions', 'shared', 'python'),
]

for _d in _FUNCTION_DIRS:
    if _d not in sys.path:
        sys.path.insert(0, _d)
