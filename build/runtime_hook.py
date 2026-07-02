"""Runtime hook for PyInstaller-frozen drive-uploader.

Adds the bundled src/ directory to sys.path so the PEP 420 namespace
package imports (`from src.bootstrap...`) resolve at runtime against
the on-disk extraction in _MEIPASS.
"""
import os
import sys

sys.path.insert(0, os.path.join(sys._MEIPASS, "src"))