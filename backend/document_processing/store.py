from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import os
import json
from .loaders import Document

class DocumentStore:
    """Simple in-memory document store."""
    
    def __init__(self):
        """Initialize an empty document store."""
        self.documents: List[Document] = []
        self.document_index: Dict[str, List[int]] = {}  # Maps source paths to document indices
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the store."""
        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            
            self.documents.append(doc)
            doc_index = len(self.documents) - 1
            
            if source not in self.document_index:
                self.document_index[source] = []
            self.document_index[source].append(doc_index)
    
    def get_documents(self, source: Optional[str] = None) -> List[Document]:
        """Get documents from the store."""
        if source is None:
            return self.documents
        
        indices = self.document_index.get(source, [])
        return [self.documents[i] for i in indices]
    
    def clear(self) -> None:
        """Clear the document store."""
        self.documents = []
        self.document_index = {}