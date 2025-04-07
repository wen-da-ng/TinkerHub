import os
import csv
import pandas as pd
from typing import List, Dict, Any, Union, Optional
from pathlib import Path
from pydantic import BaseModel

# For PDF support
try:
    import PyPDF2
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False

class Document(BaseModel):
    """Represents a document or chunk of a document."""
    content: str
    metadata: Dict[str, Any] = {}

class DocumentLoader:
    """Base class for document loaders."""
    
    def load(self, source: Union[str, Path]) -> List[Document]:
        """Load documents from a source."""
        raise NotImplementedError("Subclasses must implement this method")

class TextLoader(DocumentLoader):
    """Loader for plain text files."""
    
    def load(self, source: Union[str, Path]) -> List[Document]:
        """Load a text file."""
        path = Path(source)
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        metadata = {
            "source": str(path),
            "filename": path.name,
            "filetype": "text"
        }
        
        return [Document(content=text, metadata=metadata)]

class PDFLoader(DocumentLoader):
    """Loader for PDF files."""
    
    def load(self, source: Union[str, Path]) -> List[Document]:
        """Load a PDF file."""
        if not HAS_PDF_SUPPORT:
            raise ImportError("PyPDF2 is required for PDF support. Install it with 'pip install PyPDF2'")
        
        path = Path(source)
        documents = []
        
        with open(path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text.strip():  # Only add non-empty pages
                    metadata = {
                        "source": str(path),
                        "filename": path.name,
                        "filetype": "pdf",
                        "page": i + 1
                    }
                    documents.append(Document(content=text, metadata=metadata))
        
        return documents

class CSVLoader(DocumentLoader):
    """Loader for CSV files."""
    
    def __init__(self, content_columns: Optional[List[str]] = None):
        """Initialize the CSV loader."""
        self.content_columns = content_columns
    
    def load(self, source: Union[str, Path]) -> List[Document]:
        """Load a CSV file."""
        path = Path(source)
        df = pd.read_csv(path)
        
        documents = []
        for i, row in df.iterrows():
            if self.content_columns:
                content_dict = {col: row[col] for col in self.content_columns if col in row}
            else:
                content_dict = row.to_dict()
            
            content = "\n".join([f"{k}: {v}" for k, v in content_dict.items()])
            
            metadata = {
                "source": str(path),
                "filename": path.name,
                "filetype": "csv",
                "row": i + 1
            }
            
            documents.append(Document(content=content, metadata=metadata))
        
        return documents

def load_documents(file_path: Union[str, Path]) -> List[Document]:
    """Load documents from a file based on its extension."""
    path = Path(file_path)
    ext = path.suffix.lower()
    
    if ext == '.txt':
        loader = TextLoader()
    elif ext == '.pdf':
        loader = PDFLoader()
    elif ext == '.csv':
        loader = CSVLoader()
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
    
    return loader.load(path)