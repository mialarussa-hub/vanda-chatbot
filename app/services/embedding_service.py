"""
Embedding Service per VANDA chatbot.

Gestisce la generazione di embeddings usando OpenAI API.
"""

from openai import OpenAI
from app.config import settings
from typing import List
from loguru import logger


class EmbeddingService:
    """
    Servizio per generare embeddings di testi usando OpenAI.

    Usa il modello text-embedding-3-small (1536 dimensioni).
    """

    def __init__(self):
        """Inizializza client OpenAI"""
        try:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "text-embedding-3-small"
            self.dimension = 1536

            logger.info(f"Embedding Service initialized - Model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize Embedding Service: {e}")
            raise

    def get_embedding(self, text: str) -> List[float]:
        """
        Genera embedding per un testo.

        Args:
            text: Testo da convertire in embedding

        Returns:
            Lista di 1536 floats (embedding vector)

        Raises:
            Exception: Se la generazione fallisce
        """
        try:
            # Pulisci testo
            text = text.strip().replace("\n", " ")

            if not text:
                raise ValueError("Text cannot be empty")

            logger.debug(f"Generating embedding for text: {text[:100]}...")

            # Chiama OpenAI API
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )

            # Estrai embedding
            embedding = response.data[0].embedding

            logger.debug(f"Embedding generated: {len(embedding)} dimensions")

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise


# Singleton instance
embedding_service = EmbeddingService()
