import requests
import time

def test_api():
    url = "http://127.0.0.1:8000/tickets"
    data = {
        "title": "Cannot print document",
        "description": "The printer is offline and I cannot print my documents.",
        "userId": "test-123",
        "userEmail": "test@test.com"
    }
    
    # 1. Create ticket
    print("Creating ticket...")
    res = requests.post(url, json=data)
    ticket = res.json()
    print(f"Created ticket: {ticket['_id']} | Status: {ticket['status']}")
    
    # 2. Wait 5 seconds for background pipeline to finish
    print("Waiting 5 seconds for pipeline...")
    time.sleep(5)
    
    # 3. Check status again
    print("Checking ticket status...")
    res = requests.get(f"{url}?userId=test-123")
    tickets = res.json()
    t = tickets[0]
    print(f"Status: {t['status']}")
    if "resolution" in t and t["resolution"]:
        print(f"Resolution Result: {t['resolution']['result']}")
    else:
        print("No resolution attached!")

if __name__ == "__main__":
    test_api()
