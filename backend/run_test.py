import asyncio
import httpx
import uvicorn
from multiprocessing import Process
import time

def run_server():
    import sys
    sys.path.append(".")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="error")

async def test_api():
    server_process = Process(target=run_server)
    server_process.start()
    
    print("Waiting for server to start...")
    await asyncio.sleep(15) # Wait for models to load
    
    url = "http://127.0.0.1:8000/tickets"
    data = {
        "title": "Cannot print document",
        "description": "The printer is offline and I cannot print my documents.",
        "userId": "test-123",
        "userEmail": "test@test.com"
    }
    
    async with httpx.AsyncClient() as client:
        print("Creating ticket...")
        res = await client.post(url, json=data)
        ticket = res.json()
        print(f"Created ticket: {ticket['_id']} | Status: {ticket['status']}")
        
        print("Waiting 15 seconds for background pipeline to complete...")
        await asyncio.sleep(15)
        
        print("Checking ticket status...")
        res = await client.get(f"{url}?userId=test-123")
        tickets = res.json()
        
        # find the ticket we just created
        t = next((tk for tk in tickets if tk['_id'] == ticket['_id']), None)
        if t:
            print(f"Final Status: {t['status']}")
            if "resolution" in t and t["resolution"]:
                print(f"Resolution Result: {t['resolution']['result']}")
            else:
                print("No resolution attached!")
        else:
            print("Ticket not found.")
            
    server_process.terminate()
    server_process.join()

if __name__ == "__main__":
    asyncio.run(test_api())
