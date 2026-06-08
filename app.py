import requests

prompt = input("Ask something: ")

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False
    }
)

print("\nResponse:\n")
print(response.json()["response"])