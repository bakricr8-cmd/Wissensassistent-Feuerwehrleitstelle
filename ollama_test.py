import json
from urllib.request import Request, urlopen

daten = {
    "model": "qwen3:4b-instruct",
    "messages": [
        {"role": "user", "content": "Antworte nur mit dem Wort Hallo."}
    ],
    "stream": False,
    "options": {"num_predict": 64}
}

anfrage = Request(
    "http://127.0.0.1:11434/api/chat",
    data=json.dumps(daten).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urlopen(anfrage, timeout=180) as antwort:
    print(json.load(antwort)["message"]["content"])