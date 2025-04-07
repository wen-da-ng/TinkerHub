from typing import List, Dict, Any, Optional
import re
from .loaders import Document

class TextSplitter:
    """Base class for text splitters."""
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks."""
        raise NotImplementedError("Subclasses must implement this method")

class CharacterTextSplitter(TextSplitter):
    """Split text by character count."""
    
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200,
                 separator: str = "\n\n"):
        """Initialize the character text splitter."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks."""
        splits = text.split(self.separator)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for split in splits:
            if current_length + len(split) > self.chunk_size and current_chunk:
                chunks.append(self.separator.join(current_chunk))
                
                # Keep some overlap for context
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(s) for s in current_chunk) + len(self.separator) * (len(current_chunk) - 1)
            
            current_chunk.append(split)
            current_length += len(split) + len(self.separator)
        
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))
        
        return chunks
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks."""
        split_documents = []
        
        for doc in documents:
            splits = self.split_text(doc.content)
            
            for i, split in enumerate(splits):
                metadata = doc.metadata.copy()
                metadata["chunk"] = i + 1
                metadata["chunk_of"] = len(splits)
                
                split_documents.append(Document(content=split, metadata=metadata))
        
        return split_documents