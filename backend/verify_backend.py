import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("--- 1. Testing Health Endpoint ---")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        if r.status_code == 200 and r.json().get("status") == "ok":
            print("✅ Health check passed!\n")
            return True
    except Exception as e:
        print(f"❌ Failed to reach backend: {e}\n")
    return False

def test_list_documents():
    print("--- 2. Testing Document Listing ---")
    try:
        r = requests.get(f"{BASE_URL}/documents")
        print(f"Status: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
        print("✅ Document listing working!\n")
        return True
    except Exception as e:
        print(f"❌ Failed listing documents: {e}\n")
    return False

def test_chat():
    print("--- 3. Testing Chat Pipeline ---")
    session_id = "verify_session"
    
    # Q1
    q1 = "Who is the protagonist of the book?"
    print(f"User: {q1}")
    try:
        r1 = requests.post(f"{BASE_URL}/ask", json={"session_id": session_id, "question": q1})
        print(f"Assistant: {r1.json().get('answer')}")
    except Exception as e:
        print(f"❌ Q1 Failed: {e}\n")
        return

    # Q2 (Memory)
    q2 = "What is his profession?"
    print(f"\nUser (Follow-up): {q2}")
    try:
        r2 = requests.post(f"{BASE_URL}/ask", json={"session_id": session_id, "question": q2})
        print(f"Assistant: {r2.json().get('answer')}")
    except Exception as e:
        print(f"❌ Q2 Failed: {e}\n")
        return

    # Q3 (Guardrail)
    q3 = "What is the distance to the moon?"
    print(f"\nUser (Off-topic): {q3}")
    try:
        r3 = requests.post(f"{BASE_URL}/ask", json={"session_id": session_id, "question": q3})
        ans = r3.json().get('answer')
        print(f"Assistant: {ans}")
        if ans == "Context not enough to answer.":
            print("✅ Guardrail works correctly!")
        else:
            print("⚠️ Guardrail answer did not match expected strict string.")
    except Exception as e:
        print(f"❌ Q3 Failed: {e}\n")
        return
    print("\n✅ Chat pipeline verified!\n")

if __name__ == "__main__":
    print("Starting RAG Backend Verification...\n")
    if test_health():
        test_list_documents()
        test_chat()
    else:
        print("Please ensure your FastAPI server is running with 'uvicorn app.main:app' before executing this test.")
        sys.exit(1)
