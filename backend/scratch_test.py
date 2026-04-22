import asyncio
import sys
import os

# Ensure the backend directory is in the path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.model_loader import ModelLoader
from knowledge_base.kb_loader import KnowledgeBaseLoader
from agents.resolution_agent import ResolutionAgent

async def test():
    print("Loading models...")
    ml = ModelLoader()
    kb = KnowledgeBaseLoader(ml)
    ra = ResolutionAgent(ml, kb)
    
    query = "My computer screen is flickering randomly. The monitor connected to my workstation has started flickering randomly since this morning. It happens every few minutes and makes it impossible to work. The monitor is a Dell U2722D connected via DisplayPort."
    
    print("Searching...")
    best_match = ra._search_kb(query)
    
    if best_match:
        print(f"Match found! Score threshold check passed.")
        print(f"Title: {best_match['title']}")
        print(f"Result: {best_match['result']}")
    else:
        print("No match found or below threshold.")
        
    # Let's see the raw scores
    import numpy as np
    embedding = ml.embedder.encode([query], normalize_embeddings=True)
    embedding = np.array(embedding, dtype=np.float32)
    distances, indices = kb.index.search(embedding, 3)
    print("Top 3 FAISS Matches:")
    for i in range(3):
        idx = int(indices[0][i])
        score = float(distances[0][i])
        if idx != -1:
            print(f"  {i+1}. Score: {score:.4f} -> {kb.entries[idx]['title']}")

if __name__ == "__main__":
    asyncio.run(test())
