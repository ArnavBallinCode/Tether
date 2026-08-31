import re
from pathlib import Path

file_path = Path("tether/api/main.py")
content = file_path.read_text()

# Remove all instances of from __future__ import annotations
content = content.replace("from __future__ import annotations\n", "")

# Remove the incorrectly placed import time if it's before the docstring
if content.startswith("import time\n"):
    content = content[len("import time\n"):]

# Add them properly at the top
content = "from __future__ import annotations\nimport time\n" + content
file_path.write_text(content)
