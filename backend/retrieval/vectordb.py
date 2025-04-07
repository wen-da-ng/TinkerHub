from typing import List, Dict, Any, Optional, Tuple
import os
import uuid
from pathlib import Path
from .embeddings import Embedding, EmbeddingGenerator

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class VectorDatabase:
    """Base class for vector databases."""
    
    def add_embeddings(self, embeddings: List[Embedding]) -> None:
        """Add embeddings to the database."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def search(self, query: str, embedding_generator: EmbeddingGenerator, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the database for similar documents."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def clear(self) -> None:
        """Clear the database."""
        raise NotImplementedError("Subclasses must implement this method")


class ChromaVectorDB(VectorDatabase):
    """Vector database using ChromaDB."""
    
    def __init__(self, collection_name: str = "documents", persist_directory: Optional[str] = None):
        """Initialize the ChromaDB vector database."""
        if not HAS_CHROMADB:
            raise ImportError(
                "chromadb is required for this vector database. "
                "Install it with 'pip install chromadb'"
            )
        
        # Set up ChromaDB client
        settings = Settings()
        if persist_directory:
            os.makedirs(persist_directory, exist_ok=True)
            settings = Settings(persist_directory=persist_directory, anonymized_telemetry=False)
        
        self.client = chromadb.Client(settings)
        
        # Create or get collection
        try:
            self.collection = self.client.get_collection(collection_name)
            print(f"Found existing collection: {collection_name}")
        except Exception as e:
            # This will catch InvalidCollectionException
            print(f"Creating new collection: {collection_name}")
            self.collection = self.client.create_collection(collection_name)
    
    def add_embeddings(self, embeddings: List[Embedding]) -> None:
        """Add embeddings to the database."""
        if not embeddings:
            print("No embeddings to add")
            return
        
        print(f"Adding {len(embeddings)} embeddings to ChromaDB")
        
        try:
            # Extract data for ChromaDB
            ids = [str(uuid.uuid4()) for _ in embeddings]
            documents = [embedding.text for embedding in embeddings]
            vectors = [embedding.vector for embedding in embeddings]
            metadatas = [embedding.metadata for embedding in embeddings]
            
            # Add to collection in smaller batches to avoid issues
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                end = min(i + batch_size, len(ids))
                print(f"Adding batch {i//batch_size + 1}/{(len(ids)-1)//batch_size + 1}")
                self.collection.add(
                    ids=ids[i:end],
                    documents=documents[i:end],
                    embeddings=vectors[i:end],
                    metadatas=metadatas[i:end]
                )
            
            print("Successfully added all embeddings to ChromaDB")
        except Exception as e:
            print(f"Error adding embeddings to ChromaDB: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def search(self, query: str, embedding_generator: EmbeddingGenerator, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the database for similar documents."""
        # Generate query embedding
        query_embeddings = embedding_generator.generate([query])
        if not query_embeddings:
            return []
        
        query_vector = query_embeddings[0].vector
        
        # Search collection
        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=top_k
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            result = {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if "distances" in results else None
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def clear(self) -> None:
        """Clear the database."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(self.collection.name)


class InMemoryVectorDB(VectorDatabase):
    """Simple in-memory vector database for testing."""
    
    def __init__(self):
        """Initialize an empty in-memory vector database."""
        self.embeddings = []
    
    def add_embeddings(self, embeddings: List[Embedding]) -> None:
        """Add embeddings to the database."""
        self.embeddings.extend(embeddings)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    
    def search(self, query: str, embedding_generator: EmbeddingGenerator, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the database for similar documents."""
        if not self.embeddings:
            return []
        
        # Generate query embedding
        query_embeddings = embedding_generator.generate([query])
        if not query_embeddings:
            return []
        
        query_vector = query_embeddings[0].vector
        
        # Calculate similarities
        similarities = []
        for i, embedding in enumerate(self.embeddings):
            similarity = self._cosine_similarity(query_vector, embedding.vector)
            similarities.append((i, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Format top_k results
        results = []
        for i, similarity in similarities[:top_k]:
            embedding = self.embeddings[i]
            result = {
                "id": str(i),
                "text": embedding.text,
                "metadata": embedding.metadata,
                "distance": 1.0 - similarity  # Convert similarity to distance
            }
            results.append(result)
        
        return results
    
    def clear(self) -> None:
        """Clear the database."""
        self.embeddings = []


def get_vector_database(db_type: str = "chroma", **kwargs) -> VectorDatabase:
    """Get a vector database based on the specified type."""
    if db_type == "chroma":
        try:
            return ChromaVectorDB(**kwargs)
        except ImportError:
            print("ChromaDB not available, falling back to in-memory vector database")
            return InMemoryVectorDB()
    elif db_type == "in-memory":
        return InMemoryVectorDB()
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")