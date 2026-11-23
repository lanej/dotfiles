"""Compatibility entrypoint for the standalone driver configuration helper."""
from pathlib import Path
import os
import sys

package = Path(sys.argv[1]).resolve()
os.execvp("python3", ["python3", str(package / "scripts/configure.py"), *sys.argv[1:]])
