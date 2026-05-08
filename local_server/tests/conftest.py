import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "local_server" / "src"

for p in (str(SRC), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
