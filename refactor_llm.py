import os
import re

def rewrite_draft_py():
    path = "/Users/arnavangarkar/Desktop/Arnav/dev/Razorpay/promise-integrity-agent-main/tether/agent/llm/draft.py"
    with open(path, "r") as f:
        content = f.read()

    # Replace google imports
    content = content.replace("from google import genai", "from groq import Groq")
    content = content.replace("GEMINI_MODEL = \"gemini-3.6-flash\"", "GROQ_MODEL = \"llama3-8b-8192\"")
    
    # Replace init and client call
    content = re.sub(
        r"def __init__\(self, client: Optional\[genai\.Client\] = None, model: str = GEMINI_MODEL\):.*?\n\s+self\.model = model",
        "def __init__(self, client: Optional[Groq] = None, model: str = GROQ_MODEL):\n        self.client = client or Groq(api_key=os.environ.get(\"GROQ_API_KEY\"))\n        self.model = model",
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r"response = call_with_retry\(lambda: self\.client\.models\.generate_content\(\s*model=self\.model,\s*contents=prompt,\s*\)\)",
        "response = call_with_retry(lambda: self.client.chat.completions.create(\n            model=self.model,\n            messages=[{\"role\": \"user\", \"content\": prompt}],\n            temperature=0.0\n        ))",
        content,
        flags=re.DOTALL
    )
    
    content = content.replace("draft_text = (response.text or \"\").strip()", "draft_text = (response.choices[0].message.content or \"\").strip()")

    with open(path, "w") as f:
        f.write(content)

def rewrite_extract_py():
    path = "/Users/arnavangarkar/Desktop/Arnav/dev/Razorpay/promise-integrity-agent-main/tether/agent/llm/extract.py"
    with open(path, "r") as f:
        content = f.read()

    content = content.replace("from google import genai\nfrom google.genai import types", "import json\nfrom groq import Groq")
    content = content.replace("GEMINI_MODEL = \"gemini-3.6-flash\"", "GROQ_MODEL = \"llama3-8b-8192\"")

    content = re.sub(
        r"def __init__\(self, client: Optional\[genai\.Client\] = None, model: str = GEMINI_MODEL\):.*?\n\s+self\.model = model",
        "def __init__(self, client: Optional[Groq] = None, model: str = GROQ_MODEL):\n        self.client = client or Groq(api_key=os.environ.get(\"GROQ_API_KEY\"))\n        self.model = model",
        content,
        flags=re.DOTALL
    )

    extract_call_code = """
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(reply_text=reply_text, today=today) + "\\n\\nRespond with ONLY a valid JSON object matching the requested schema."
        
        response = call_with_retry(lambda: self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        ))
        
        raw_dict = json.loads(response.choices[0].message.content)
        raw = PromiseExtractionSchema(**raw_dict)
"""
    content = re.sub(
        r"response = call_with_retry\(lambda: self\.client\.models\.generate_content\(.*?raw: PromiseExtractionSchema = response\.parsed",
        extract_call_code.strip(),
        content,
        flags=re.DOTALL
    )

    with open(path, "w") as f:
        f.write(content)

rewrite_draft_py()
rewrite_extract_py()
print("Rewrote LLM files")
