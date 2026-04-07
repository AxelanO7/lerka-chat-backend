from abc import ABC, abstractmethod
from typing import List, Dict, Any

class Document(ABC):
    id: str
    content: str
    metadata: Dict[str, Any]

class VectorStore(ABC):
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> None:
        pass

    @abstractmethod
    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Document]:
        pass 