import sys
import os

_this_dir = os.path.dirname(os.path.abspath(__file__))


def pytest_collect_file(parent, file_path):
    """Clear sys.modules['app'] before this directory's test files are imported."""
    if str(file_path.parent) == _this_dir and file_path.name.startswith('test_'):
        for key in list(sys.modules.keys()):
            if key == 'app' or key.startswith('app.'):
                del sys.modules[key]
        if _this_dir in sys.path:
            sys.path.remove(_this_dir)
        sys.path.insert(0, _this_dir)
    return None
