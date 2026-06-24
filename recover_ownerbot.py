import json
import glob

log_path = r"C:\Users\mxsab\.gemini\antigravity-ide\brain\c7afe8d4-41fe-462c-b508-f40adff8a209\.system_generated\logs\transcript.jsonl"
snippets = {}

with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data.get("type") == "VIEW_FILE" and "main.dart" in str(data.get("content", "")) and "ownerbot_frontend" in str(data.get("content", "")):
            content = data.get("content", "")
            # We want to find the latest version. Let's just dump all lines that look like "number: code"
            for row in content.split('\n'):
                if ":" in row:
                    try:
                        num = int(row.split(":")[0])
                        code = ":".join(row.split(":")[1:])[1:] # skip the space after colon
                        snippets[num] = code
                    except:
                        pass

# Print lines 50 to 300 to reconstruct
for i in range(50, 300):
    if i in snippets:
        print(f"{i}: {snippets[i]}")
