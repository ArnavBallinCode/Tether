import re
from pathlib import Path

file_path = Path("/Users/arnavangarkar/Desktop/Arnav/dev/Razorpay/promise-integrity-agent-main/frontend/src/pages/PipelineFlow.jsx")
content = file_path.read_text()

nodes_str = """const initialNodes = [
  { id: 'detect', type: 'custom', position: { x: 50, y: 200 }, data: { name: 'Detect', count: 0, active: false } },
  { id: 'diagnose', type: 'custom', position: { x: 400, y: 100 }, data: { name: 'Diagnose', count: 0, active: false } },
  { id: 'decide', type: 'custom', position: { x: 750, y: 200 }, data: { name: 'Decide', count: 0, active: false } },
  { id: 'policy', type: 'custom', position: { x: 1100, y: 100 }, data: { name: 'Policy Gate', count: 0, active: false } },
  { id: 'execute', type: 'custom', position: { x: 1450, y: 200 }, data: { name: 'Execute', count: 0, active: false } },
  { id: 'verify', type: 'custom', position: { x: 1800, y: 100 }, data: { name: 'Verify', count: 0, active: false } },
];"""

content = re.sub(r'const initialNodes = \[.*?\];', nodes_str, content, flags=re.DOTALL)
file_path.write_text(content)
print("React Flow nodes repositioned!")
