import chromadb

# 1. Connect to the local folder you created
client = chromadb.PersistentClient(path="./chroma_db")

# 2. Get the collection
collection = client.get_collection(name="job_data")

# 3. Peek at the first 5 records
print(f"Total jobs in ChromaDB: {collection.count()}")
results = collection.peek(limit=5)

print("\n--- FIRST 5 RECORDS ---")
for i in range(len(results['ids'])):
    print(f"ID: {results['ids'][i]}")
    print(f"Metadata: {results['metadatas'][i]}")
    print(f"Text Snippet: {results['documents'][i][:100].replace('\n', ' ')}...") # First 100 chars
    print(f"Embedding Vector Length: {len(results['embeddings'][i])}")
    print(f"Embedding Vector Sample: {results['embeddings'][i][:10]}...") # First 10 values
    print("-" * 30)