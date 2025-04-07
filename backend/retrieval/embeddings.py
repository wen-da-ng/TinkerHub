from typing import List, Union, Dict, Any
import numpy as np
from pydantic import BaseModel

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class Embedding(BaseModel):
    """Represents a text embedding."""
    text: str
    vector: List[float]
    metadata: Dict[str, Any] = {}


class EmbeddingGenerator:
    """Base class for embedding generators."""
    
    def generate(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> List[Embedding]:
        """Generate embeddings for a list of texts."""
        raise NotImplementedError("Subclasses must implement this method")


class SentenceTransformerEmbedding(EmbeddingGenerator):
    """Embedding generator using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding generator."""
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers is required for this embedding generator. "
                "Install it with 'pip install sentence-transformers'"
            )
        
        self.model = SentenceTransformer(model_name)
    
    def generate(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> List[Embedding]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        # Convert to list of Embedding objects
        result = []
        for i, (text, vector) in enumerate(zip(texts, embeddings)):
            # Get metadata for this text if available
            meta = {}
            if metadata and i < len(metadata):
                meta = metadata[i]
            
            # Create Embedding object
            embedding = Embedding(
                text=text,
                vector=vector.tolist(),
                metadata=meta
            )
            result.append(embedding)
        
        return result


class DummyEmbedding(EmbeddingGenerator):
    """Dummy embedding generator for testing."""
    
    def __init__(self, vector_size: int = 384):
        """Initialize the dummy embedding generator."""
        self.vector_size = vector_size
    
    def generate(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> List[Embedding]:
        """Generate fake embeddings for a list of texts."""
        if not texts:
            return []
        
        # Generate random embeddings
        result = []
        for i, text in enumerate(texts):
            # Get metadata for this text if available
            meta = {}
            if metadata and i < len(metadata):
                meta = metadata[i]
            
            # Create a dummy vector (random but deterministic based on text)
            seed = sum(ord(c) for c in text)
            np.random.seed(seed)
            vector = np.random.rand(self.vector_size).tolist()
            
            # Create Embedding object
            embedding = Embedding(
                text=text,
                vector=vector,
                metadata=meta
            )
            result.append(embedding)
        
        return result


def get_embedding_generator(embedding_type: str = "sentence-transformer", **kwargs) -> EmbeddingGenerator:
    """Get an embedding generator based on the specified type."""
    if embedding_type == "sentence-transformer":
        try:
            return SentenceTransformerEmbedding(**kwargs)
        except ImportError:
            print("sentence-transformers not available, falling back to dummy embeddings")
            return DummyEmbedding(**kwargs)
    elif embedding_type == "dummy":
        return DummyEmbedding(**kwargs)
    else:
        raise ValueError(f"Unsupported embedding type: {embedding_type}")