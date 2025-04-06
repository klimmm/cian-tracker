import sys
from pathlib import Path

from main import server

current_dir = str(Path(__file__).parent.absolute())
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    server.run()