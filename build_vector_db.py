"""
Build Vector Database for Lab Report Decoder
Uses Hugging Face sentence-transformers for embeddings
"""

import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import glob

def load_documents_from_directory(directory: str) -> list:
    """Load all text files from a directory"""
    documents = []
    
    if not os.path.exists(directory):
        print(f"⚠️  Directory not found: {directory}")
        return documents
    
    # Find all .txt files
    txt_files = glob.glob(os.path.join(directory, "**", "*.txt"), recursive=True)
    
    for filepath in txt_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    documents.append({
                        'content': content,
                        'source': filepath,
                        'filename': os.path.basename(filepath)
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return documents

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size * 0.5:  # Only if break point is reasonable
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks

def build_knowledge_base():
    """Build the vector database from medical documents"""
    
    print("📚 Loading medical documents...")
    
    # Load documents from data directory
    data_dir = 'data/'
    all_documents = []
    
    if not os.path.exists(data_dir):
        print(f"⚠️  Creating data directory: {data_dir}")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'lab_markers'), exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'nutrition'), exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'conditions'), exist_ok=True)
        print("⚠️  Please add medical reference documents to the data/ folder")
        return None
    
    # Load from all subdirectories
    for subdir in ['lab_markers', 'nutrition', 'conditions']:
        subdir_path = os.path.join(data_dir, subdir)
        docs = load_documents_from_directory(subdir_path)
        all_documents.extend(docs)
    
    if not all_documents:
        print("⚠️  No documents found in data/ directory")
        print("Please add .txt files with medical information")
        return None
    
    print(f"✅ Loaded {len(all_documents)} documents")
    
    # Chunk documents
    print("✂️  Splitting documents into chunks...")
    all_chunks = []
    all_metadata = []
    
    for doc in all_documents:
        chunks = chunk_text(doc['content'], chunk_size=1000, overlap=200)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                'source': doc['source'],
                'filename': doc['filename'],
                'chunk_id': i
            })
    
    print(f"✅ Created {len(all_chunks)} text chunks")
    
    # Load embedding model
    print("🧠 Loading embedding model (this may take a moment)...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Embedding model loaded")
    
    # Create embeddings
    print("🔄 Creating embeddings (this may take a few minutes)...")
    embeddings = embedding_model.encode(
        all_chunks,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    print(f"✅ Created {len(embeddings)} embeddings")
    
    # Create ChromaDB collection
    print("💾 Building ChromaDB vector store...")
    
    # Initialize client
    db_path = "./chroma_db"
    client = chromadb.PersistentClient(path=db_path)
    
    # Delete existing collection if it exists
    try:
        client.delete_collection("lab_reports")
        print("🗑️  Deleted existing collection")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(
        name="lab_reports",
        metadata={"description": "Medical lab report information"}
    )
    
    # Add documents in batches
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i + batch_size]
        batch_embeddings = embeddings[i:i + batch_size].tolist()
        batch_ids = [f"doc_{j}" for j in range(i, i + len(batch_chunks))]
        batch_metadata = all_metadata[i:i + batch_size]
        
        collection.add(
            documents=batch_chunks,
            embeddings=batch_embeddings,
            ids=batch_ids,
            metadatas=batch_metadata
        )
    
    print("✅ Vector database built successfully!")
    print(f"📍 Database location: {db_path}")
    print(f"📊 Total vectors: {len(all_chunks)}")
    
    return collection

def test_retrieval(collection):
    """Test the retrieval system"""
    if collection is None:
        print("\n⚠️  No collection to test")
        return
    
    print("\n🔍 Testing retrieval system...")
    
    # Load embedding model for queries
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    test_queries = [
        "What does low hemoglobin mean?",
        "What foods are high in iron?",
        "Normal range for glucose"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        
        # Create query embedding
        query_embedding = embedding_model.encode(query).tolist()
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2
        )
        
        if results and results['documents']:
            print(f"  ✅ Found {len(results['documents'][0])} relevant documents")
            print(f"  📄 Top result preview: {results['documents'][0][0][:150]}...")
        else:
            print("  ❌ No results found")

if __name__ == "__main__":
    print("🚀 Building Lab Report Decoder Vector Database\n")
    
    # Build the database
    collection = build_knowledge_base()
    
    # Test it
    if collection:
        test_retrieval(collection)
        print("\n🎉 Setup complete! You can now run the Flask application.")
    else:
        print("\n⚠️  Please add medical documents to the data/ folder and run again.")