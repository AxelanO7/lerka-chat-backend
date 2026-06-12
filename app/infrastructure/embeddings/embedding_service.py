import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List
from fastembed import TextEmbedding
from app.core.config import settings

class EmbeddingService:
    _instance = None
    _model = None
    _executor = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def initialize(self):
        if self._model is None:
            # fastembed TextEmbedding initialization
            self._model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
            self._executor = ThreadPoolExecutor(max_workers=4)

    def embed_text_sync(self, text: str) -> List[float]:
        # Fastembed query embedding (returns a generator)
        embeddings = list(self._model.embed([text]))
        return [float(x) for x in embeddings[0]]

    async def get_embedding(self, text: str) -> List[float]:
        if self._model is None:
            self.initialize()
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self.embed_text_sync,
            text
        )

# Global singleton
embedding_service = EmbeddingService()
