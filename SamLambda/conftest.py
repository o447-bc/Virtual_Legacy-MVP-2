"""
Root conftest.py for SamLambda tests.

Each Lambda function has its own app.py. When pytest collects multiple test
files that all do `from app import ...`, Python's sys.modules cache causes
the wrong app.py to be used after the first import.

This conftest uses pytest_collect_file to clear sys.modules['app'] and
set sys.path correctly before each test file is imported during collection.
"""
import sys
import os


def pytest_collect_file(parent, file_path):
    """
    Fires before pytest imports each test file.
    Clear 'app' from sys.modules and put this file's directory first on
    sys.path so the correct app.py is loaded for each Lambda test.
    """
    if file_path.suffix == '.py' and file_path.name.startswith('test_'):
        test_dir = str(file_path.parent)
        # Clear cached app module so this test file gets its own app.py
        for key in list(sys.modules.keys()):
            if key == 'app' or key.startswith('app.'):
                del sys.modules[key]
        # Put this test's directory first on sys.path
        if test_dir in sys.path:
            sys.path.remove(test_dir)
        sys.path.insert(0, test_dir)
    return None
