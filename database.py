import chromadb
from sentence_transformers import SentenceTransformer
import config

def get_db_connection():
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=config.DB_PATH)
    collection = client.get_or_create_collection(name=config.COLLECTION_NAME)
    return collection, model

# Updated to accept 'where' clause
def query_logs(prompt, collection, model, n_results=5, where_filter=None):
    vector = model.encode(prompt).tolist()
    
    results = collection.query(
        query_embeddings=[vector],
        n_results=n_results,
        where=where_filter # <--- Pass the filter here (e.g., {"timestamp": {"$gt": 12345}})
    )
    
    if results['documents']:
        return "\n".join(results['documents'][0])
    return "No relevant logs found."