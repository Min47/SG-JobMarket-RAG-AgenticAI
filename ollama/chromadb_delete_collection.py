import chromadb

client = chromadb.PersistentClient(path="./chroma_db")

# 1. Delete the entire collection
try:
    client.delete_collection(name="job_data")
    print("Collection deleted.")
except ValueError:
    print("Collection did not exist.")