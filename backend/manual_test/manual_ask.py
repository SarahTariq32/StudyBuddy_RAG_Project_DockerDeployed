import requests

r = requests.post(
    "http://127.0.0.1:8000/ask",
    json={"session_id": "test", "question": "Who is the protagonist?"}
)

print("Status:", r.status_code)
print("Raw response:", r.json())