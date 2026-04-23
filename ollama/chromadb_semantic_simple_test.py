import chromadb
from langchain_ollama import OllamaEmbeddings

# 1. Re-define the Custom Embedding Class
class QwenOllamaEff:
    def __init__(self):
        # Initialize the model once to avoid re-loading overhead
        self.model = OllamaEmbeddings(model="qwen3-embedding:8b")

    def __call__(self, input: list) -> list:
        # Chroma calls this for bulk documents
        return self.model.embed_documents(input)

    def embed_query(self, input: str) -> list:
        if isinstance(input, list):
            input = input[0]
        
        # Get the single embedding
        embedding = self.model.embed_query(input)
        
        return [embedding]

    def name(self) -> str:
        return "QwenOllamaEff"

def run_semantic_test(query_text: str, n_results: int = 30):
    client = chromadb.PersistentClient(path="./chroma_db")
    
    try:
        collection = client.get_collection(
            name="job_data", 
            embedding_function=QwenOllamaEff()
        )
    except ValueError:
        print("Collection not found.")
        return

    print(f"\n--- Searching for: '{query_text}' ---")
    
    print("Executing semantic search query...")
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
        where={"source": "JobStreet"}
    )
    print("Query executed. Processing results...\n\n")

    if not results['ids'][0]:
        print("No results found.")
        return

    # --- SQL GENERATION BLOCK ---
    sql_ids = []
    case_statements = []
    
    for i in range(len(results['ids'][0])):
        job_id = results['metadatas'][0][i]['job_id']
        dist = results['distances'][0][i]
        
        sql_ids.append(f"'{job_id}'")
        case_statements.append(f"WHEN '{job_id}' THEN {dist:.4f}")
        
        # Original terminal display logic
        doc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        print(f"[Result {i+1}] (Distance: {dist:.4f}) | Job ID: {meta['job_id']} | Chunk: {meta['chunk_index']}")
        print(f"Content: {doc[:300]}...") 
        print("-" * 30)

    # Print the formatted SQL for easy copy-pasting
    formatted_ids = ", ".join(set(sql_ids)) # set() to handle multiple chunks from same job
    formatted_cases = "\n        ".join(case_statements)
    
    print("\n" + "="*50)
    print("--- GENERATED SQL FOR VERIFICATION ---")
    print(f"""
SELECT 
    cj.job_title,
    cj.job_description,
    CASE cj.job_id 
        {formatted_cases}
        ELSE NULL 
    END AS semantic_dist,
    '|' AS sep, 
    cj.* FROM cleaned_jobs cj 
WHERE cj.job_id IN ({formatted_ids})
ORDER BY semantic_dist ASC;
    """)
    print("="*50 + "\n")

# --- EXECUTION ---
if __name__ == "__main__":
    # Test 1: Broad Role Search
    run_semantic_test("Software Engineer experienced in Python and SQL")
    
    # Test 2: Specific Technology Search
    # run_semantic_test("Machine Learning engineer with PyTorch experience")