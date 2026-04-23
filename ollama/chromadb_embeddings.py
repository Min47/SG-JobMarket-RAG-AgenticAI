import mysql.connector
import re
from datetime import datetime, timezone
import chromadb
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings

# --- CONFIG ---
DB_CONFIG = {
    'user': 'root',
    'password': 'password',
    'host': 'localhost',
    'database': 'job_data',
    'charset': 'utf8mb4'
}

def stage3_semantic_embedding_qwen(
    db_config: dict, 
    chroma_path: str = "./chroma_db"
):
    """Refactored Stage 3: Semantic Chunking + Qwen3 8B Embedding."""
    
    # 1. Setup Chunking Model (Nomic - fast/efficient for finding breaks)
    # This uses Ollama under the hood
    chunker_embeddings = OllamaEmbeddings(model="nomic-embed-text")
    semantic_splitter = SemanticChunker(chunker_embeddings, breakpoint_threshold_type="percentile")

    # 2. Setup Embedding Model (Qwen3 8B - High quality 1024-dim)
    # We pass this to Chroma as the default embedding function
    class QwenOllamaEff:
        def __call__(self, input: list) -> list:
            emb = OllamaEmbeddings(model="qwen3-embedding:8b")
            return emb.embed_documents(input)

        def name(self) -> str:
            return "QwenOllamaEff"

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="job_data",
        embedding_function=QwenOllamaEff(),
        metadata={"hnsw:space": "cosine"}
    )

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT job_id, source, job_title, job_description FROM cleaned_jobs"
        cursor.execute(query)
        rows = cursor.fetchall()

        for i, row in enumerate(rows):
            print(f"\n[>] Starting Job: {row['job_id']} ({i+1}/{len(rows)})")

            # Step 1: Chunking
            print(f"  └─ Splitting text semantically...", end="", flush=True)
                
            full_text = f"TITLE: {row['job_title']}\nDESCRIPTION: {row['job_description']}\nJOB_ID: {row['job_id']}\nSOURCE: {row['source']}"

            # Instead of one big doc, this creates a list of logically split strings
            chunks = semantic_splitter.create_documents([full_text])

            print(f" Done ({len(chunks)} chunks found).")

            # Step 2: Embedding & Upserting
            print(f"  └─ Generating 1024-dim Qwen3 embeddings...", end="", flush=True)
            
            chunk_ids = []
            chunk_docs = []
            chunk_metas = []

            for i, chunk in enumerate(chunks):
                # Create unique ID for each chunk (job_id + index)
                chunk_ids.append(f"{row['job_id']}_ch{i}")
                chunk_docs.append(chunk.page_content)
                chunk_metas.append({
                    "job_id": row['job_id'],
                    "source": row['source'],
                    "chunk_index": i,
                    "model": "qwen3-8b",
                    "dim": 1024
                })

            # Upsert the chunks for this job
            if chunk_ids:
                collection.upsert(
                    ids=chunk_ids,
                    documents=chunk_docs,
                    metadatas=chunk_metas
                )
                print(f"Processed job {row['job_id']}: split into {len(chunk_ids)} semantic chunks.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# Run it
stage3_semantic_embedding_qwen(db_config=DB_CONFIG)