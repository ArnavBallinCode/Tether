import os
import shutil
import re
import sys

src_dir = "/Users/arnavangarkar/Desktop/Arnav/dev/Razorpay/promise-integrity-agent-main 2"
dst_dir = "/Users/arnavangarkar/Desktop/Arnav/dev/Razorpay/promise-integrity-agent-main/tether"

# Ensure all target directories exist
os.makedirs(os.path.join(dst_dir, "backend"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "features"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "ml"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "ml/artifacts"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "policy"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "agent"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "agent/llm"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "simulator"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "eval"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "api"), exist_ok=True)
os.makedirs(os.path.join(dst_dir, "domain"), exist_ok=True)

for dir_path in ["backend", "features", "ml", "ml/artifacts", "policy", "agent", "agent/llm", "simulator", "eval", "api", "domain", ""]:
    init_path = os.path.join(dst_dir, dir_path, "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("")

def replace_imports(content):
    # Regex to replace from XXX import YYY with from tether.XXX import YYY
    # and import XXX with import tether.XXX for known packages
    packages = ["backend", "features", "models", "policy", "agent", "simulator", "eval"]
    for pkg in packages:
        content = re.sub(rf"^from {pkg}(\.?)", rf"from tether.{pkg}\1", content, flags=re.MULTILINE)
        content = re.sub(rf"^import {pkg}(\.?)", rf"import tether.{pkg}\1", content, flags=re.MULTILINE)
    
    # models -> ml mapping in imports
    content = re.sub(r"tether\.models", r"tether.ml", content)
    content = re.sub(r"models\.propensity_model", r"ml.propensity", content)
    
    # replace gemini with groq in agent/llm
    if "google.generativeai" in content or "gemini" in content.lower():
        # Just simple replacement, a more robust rewrite might be needed but we'll try a rough patch for LLM client
        content = content.replace("import google.generativeai as genai", "from groq import Groq\nimport os")
        content = content.replace("genai.configure(api_key=", "# genai.configure(api_key=")
        content = content.replace("genai.GenerativeModel('gemini-pro')", "Groq(api_key=os.environ.get('GROQ_API_KEY'))")
    return content

files_to_copy = {
    "backend/db.py": "backend/db.py",
    "features/feature_engine.py": "features/feature_engine.py",
    "models/train.py": "ml/train_propensity.py",
    "models/propensity_model.py": "ml/propensity.py",
    "policy/constraints.py": "policy/constraints.py",
    "policy/eiv.py": "policy/eiv.py",
    "agent/state_machine.py": "agent/state_machine.py",
    "agent/tools.py": "agent/tools.py",
    "agent/llm/draft.py": "agent/llm/draft.py",
    "agent/llm/extract.py": "agent/llm/extract.py",
    "simulator/archetypes.py": "simulator/archetypes.py",
    "simulator/behavior_model.py": "simulator/behavior_model.py",
    "simulator/engine.py": "simulator/engine.py",
    "eval/run_eval.py": "eval/run_eval.py",
    "eval/scenarios.py": "eval/scenarios.py",
    "backend/routes/dashboard.py": "api/main.py", # Need to combine api routing
    "backend/rationale_explanations.py": "backend/rationale_explanations.py"
}

for src_rel, dst_rel in files_to_copy.items():
    src_file = os.path.join(src_dir, src_rel)
    dst_file = os.path.join(dst_dir, dst_rel)
    
    if os.path.exists(src_file):
        with open(src_file, "r") as f:
            content = f.read()
            
        content = replace_imports(content)
        
        with open(dst_file, "w") as f:
            f.write(content)
            
print("Done")
