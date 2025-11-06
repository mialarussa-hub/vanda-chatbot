"""
RAG Service per VANDA chatbot.

Gestisce:
- Similarity search su Supabase vector database
- Retrieval di documenti rilevanti con filtri metadata
- Formattazione context per LLM
- Calcolo cosine similarity
"""

from supabase import create_client, Client
from app.config import settings
from app.models.schemas import DocumentChunk, MetadataFilter, DocumentMetadata
from typing import List, Optional, Dict, Any
from loguru import logger
import numpy as np
import json


class RAGService:
    """
    Servizio per Retrieval-Augmented Generation.

    Gestisce la ricerca di documenti simili nel database vettoriale Supabase
    e la preparazione del context per il LLM.
    """

    def __init__(self):
        """
        Inizializza connessione Supabase e configurazioni.

        Raises:
            Exception: Se la connessione a Supabase fallisce
        """
        try:
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            self.table_name = settings.SUPABASE_TABLE_NAME

            # Configurazioni RAG
            self.default_match_count = settings.RAG_DEFAULT_MATCH_COUNT
            self.default_match_threshold = settings.RAG_DEFAULT_MATCH_THRESHOLD
            self.embedding_dimension = 1536  # OpenAI text-embedding-3-small

            logger.info(f"RAG Service initialized - Table: {self.table_name}")

        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            raise

    def search_similar_documents(
        self,
        query_embedding: List[float],
        match_count: Optional[int] = None,
        match_threshold: Optional[float] = None,
        metadata_filter: Optional[MetadataFilter] = None
    ) -> List[DocumentChunk]:
        """
        Cerca documenti simili usando vector similarity search.

        Questo metodo:
        1. Valida l'embedding della query
        2. Applica filtri metadata opzionali
        3. Recupera tutti i documenti matching
        4. Calcola cosine similarity client-side
        5. Filtra per threshold e ordina per similarity
        6. Ritorna top-k risultati

        NOTA: In produzione, questa logica dovrebbe essere spostata in una
        stored procedure PostgreSQL per performance ottimali. Per ora
        calcoliamo la similarity client-side per semplicità.

        Args:
            query_embedding: Vettore embedding della query (1536 dimensioni)
            match_count: Numero massimo di risultati (default: da settings)
            match_threshold: Soglia minima similarity 0-1 (default: da settings)
            metadata_filter: Filtri opzionali per metadata JSONB

        Returns:
            Lista di DocumentChunk ordinati per similarity (maggiore a minore)

        Raises:
            ValueError: Se l'embedding ha dimensioni errate
        """
        try:
            # Usa valori default se non specificati
            if match_count is None:
                match_count = self.default_match_count
            if match_threshold is None:
                match_threshold = self.default_match_threshold

            # Validazione embedding
            if len(query_embedding) != self.embedding_dimension:
                raise ValueError(
                    f"Expected {self.embedding_dimension} dimensions, "
                    f"got {len(query_embedding)}"
                )

            logger.info(
                f"Searching similar documents - "
                f"match_count: {match_count}, threshold: {match_threshold}"
            )

            # Costruisci query base
            # NOTA: Selezioniamo embedding solo per il calcolo similarity
            query = self.client.table(self.table_name).select("id, content, metadata, embedding")

            # Applica filtri metadata se forniti
            if metadata_filter:
                query = self._apply_metadata_filters(query, metadata_filter)

            # OTTIMIZZAZIONE: Limita il numero di documenti recuperati dal database
            # per ridurre il tempo di query e il processing client-side
            # Prendiamo match_count * 3 per avere margine dopo il filtering per threshold
            query = query.limit(match_count * 3)

            # Esegui query
            response = query.execute()

            if not response.data:
                logger.warning("No documents found in database matching filters")
                return []

            logger.info(f"Retrieved {len(response.data)} documents from database")

            # Calcola similarity per ogni documento
            results = []
            for doc in response.data:
                try:
                    # Estrai embedding del documento
                    doc_embedding = doc.get('embedding')
                    if not doc_embedding:
                        logger.warning(f"Document {doc.get('id')} has no embedding, skipping")
                        continue

                    # Se embedding è una stringa JSON, parsala in array
                    if isinstance(doc_embedding, str):
                        doc_embedding = json.loads(doc_embedding)

                    # Calcola cosine similarity
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)

                    # Filtra per threshold
                    if similarity >= match_threshold:
                        results.append({
                            'id': doc['id'],
                            'content': doc['content'],
                            'metadata': doc['metadata'],
                            'similarity': similarity
                        })

                except Exception as e:
                    logger.error(f"Error processing document {doc.get('id')}: {e}")
                    continue

            # Ordina per similarity (decrescente), poi per priority (decrescente)
            # A parità di similarity, mostra prima i progetti con priority alta
            results.sort(
                key=lambda x: (
                    x['similarity'],
                    x['metadata'].get('priority', 0)  # Priority 0 se non presente
                ),
                reverse=True
            )
            results = results[:match_count]

            # Converti in DocumentChunk Pydantic models
            chunks = []
            for r in results:
                try:
                    chunks.append(DocumentChunk(
                        id=r['id'],
                        content=r['content'],
                        metadata=DocumentMetadata(**r['metadata']),
                        similarity=round(r['similarity'], 4)  # Arrotonda a 4 decimali
                    ))
                except Exception as e:
                    logger.error(f"Error creating DocumentChunk: {e}")
                    continue

            logger.info(
                f"Found {len(chunks)} relevant documents "
                f"(threshold: {match_threshold})"
            )

            if chunks:
                logger.debug(
                    f"Top similarity score: {chunks[0].similarity:.4f}, "
                    f"Bottom: {chunks[-1].similarity:.4f}"
                )

            return chunks

        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []

    def _apply_metadata_filters(
        self,
        query: Any,
        metadata_filter: MetadataFilter
    ) -> Any:
        """
        Applica filtri metadata JSONB alla query Supabase.

        Supabase supporta operatori JSONB per filtrare campi nested:
        - eq: uguaglianza
        - gte: maggiore o uguale
        - etc.

        Args:
            query: Query Supabase builder
            metadata_filter: Filtri da applicare

        Returns:
            Query modificata con filtri applicati
        """
        try:
            # Filtra per category
            if metadata_filter.category:
                query = query.eq("metadata->>category", metadata_filter.category)
                logger.debug(f"Applied filter: category={metadata_filter.category}")

            # Filtra per subcategory
            if metadata_filter.subcategory:
                query = query.eq("metadata->>subcategory", metadata_filter.subcategory)
                logger.debug(f"Applied filter: subcategory={metadata_filter.subcategory}")

            # Filtra per client (nome specifico)
            if metadata_filter.client:
                query = query.eq("metadata->>client", metadata_filter.client)
                logger.debug(f"Applied filter: client={metadata_filter.client}")

            # Filtra per client_type
            if metadata_filter.client_type:
                query = query.eq("metadata->>client_type", metadata_filter.client_type)
                logger.debug(f"Applied filter: client_type={metadata_filter.client_type}")

            # Filtra per brand
            if metadata_filter.brand:
                query = query.eq("metadata->>brand", metadata_filter.brand)
                logger.debug(f"Applied filter: brand={metadata_filter.brand}")

            # Filtra per visibility
            if metadata_filter.visibility:
                query = query.eq("metadata->>visibility", metadata_filter.visibility)
                logger.debug(f"Applied filter: visibility={metadata_filter.visibility}")

            # Filtra per featured (boolean)
            if metadata_filter.featured is not None:
                # JSONB memorizza boolean come true/false lowercase
                featured_str = str(metadata_filter.featured).lower()
                query = query.eq("metadata->>featured", featured_str)
                logger.debug(f"Applied filter: featured={featured_str}")

            # Filtra per min_priority (numeric comparison)
            if metadata_filter.min_priority is not None:
                # Per confronti numerici su JSONB, castare a int
                query = query.filter(
                    "metadata->>priority",
                    "gte",
                    str(metadata_filter.min_priority)
                )
                logger.debug(f"Applied filter: priority>={metadata_filter.min_priority}")

            # Filtra per project_scale
            if metadata_filter.project_scale:
                query = query.eq("metadata->>project_scale", metadata_filter.project_scale)
                logger.debug(f"Applied filter: project_scale={metadata_filter.project_scale}")

            # Filtra per document_type
            if metadata_filter.document_type:
                query = query.eq("metadata->>document_type", metadata_filter.document_type)
                logger.debug(f"Applied filter: document_type={metadata_filter.document_type}")

            return query

        except Exception as e:
            logger.error(f"Error applying metadata filters: {e}")
            return query

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calcola cosine similarity tra due vettori.

        Formula: similarity = (A · B) / (||A|| * ||B||)

        Dove:
        - A · B = dot product
        - ||A|| = norma euclidea di A
        - ||B|| = norma euclidea di B

        Result range: [-1, 1]
        - 1 = identici
        - 0 = ortogonali (non correlati)
        - -1 = opposti

        Args:
            vec1: Primo vettore
            vec2: Secondo vettore

        Returns:
            Cosine similarity score [0, 1]
        """
        try:
            v1 = np.array(vec1, dtype=np.float32)
            v2 = np.array(vec2, dtype=np.float32)

            # Calcola dot product
            dot_product = np.dot(v1, v2)

            # Calcola norme
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            # Evita divisione per zero
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero vector detected in similarity calculation")
                return 0.0

            # Cosine similarity
            similarity = dot_product / (norm1 * norm2)

            # Assicura range [0, 1] (a volte può essere leggermente negativo per errori numerici)
            similarity = max(0.0, min(1.0, similarity))

            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def format_context_for_llm(
        self,
        documents: List[DocumentChunk],
        include_metadata: bool = True,
        max_context_length: Optional[int] = None
    ) -> str:
        """
        Formatta documenti recuperati in context string per LLM.

        Crea una stringa formattata con informazioni rilevanti dai documenti
        per fornire context al LLM nella generazione della risposta.

        Args:
            documents: Lista di DocumentChunk da formattare
            include_metadata: Se True, include metadata rilevanti
            max_context_length: Lunghezza massima context (truncate se supera)

        Returns:
            String formattato pronto per essere usato come context LLM
        """
        if not documents:
            return "Nessuna informazione rilevante trovata nel database."

        try:
            context_parts = []

            for i, doc in enumerate(documents, 1):
                # Estrai metadata utili
                heading = doc.metadata.heading or "Senza titolo"
                category = doc.metadata.category or "N/A"
                client_type = doc.metadata.client_type or "N/A"
                tags = doc.metadata.tags or ""

                # Costruisci sezione documento
                doc_section = f"[DOCUMENTO {i}]"

                if include_metadata:
                    doc_section += f"\nTitolo: {heading}"
                    doc_section += f"\nCategoria: {category}"

                    if client_type != "N/A":
                        doc_section += f"\nTipo Cliente: {client_type}"

                    if tags:
                        doc_section += f"\nTags: {tags}"

                    if doc.similarity:
                        doc_section += f"\nRilevanza: {doc.similarity:.2%}"

                doc_section += f"\n\nContenuto:\n{doc.content}\n"
                doc_section += "\n" + "-" * 80

                context_parts.append(doc_section)

            # Unisci tutti i documenti
            full_context = "\n\n".join(context_parts)

            # Header context
            header = (
                "INFORMAZIONI RILEVANTI DAL DATABASE VANDA DESIGNERS:\n"
                f"(Trovati {len(documents)} documenti rilevanti)\n"
                + "=" * 80 + "\n\n"
            )

            context = header + full_context

            # Truncate se necessario
            if max_context_length and len(context) > max_context_length:
                logger.warning(
                    f"Context truncated: {len(context)} -> {max_context_length} chars"
                )
                context = context[:max_context_length] + "\n\n[...context truncated...]"

            logger.info(
                f"Formatted context: {len(documents)} docs, {len(context)} chars"
            )

            return context

        except Exception as e:
            logger.error(f"Error formatting context: {e}")
            return "Errore nella formattazione del context."

    def get_document_by_id(self, doc_id: int) -> Optional[DocumentChunk]:
        """
        Recupera un documento specifico per ID primario.

        Utile per recuperare documenti referenziati o fare fetch diretti.

        Args:
            doc_id: ID primario del documento nel database

        Returns:
            DocumentChunk se trovato, None altrimenti
        """
        try:
            logger.debug(f"Fetching document by ID: {doc_id}")

            response = self.client.table(self.table_name)\
                .select("id, content, metadata")\
                .eq("id", doc_id)\
                .execute()

            if response.data and len(response.data) > 0:
                doc = response.data[0]

                chunk = DocumentChunk(
                    id=doc['id'],
                    content=doc['content'],
                    metadata=DocumentMetadata(**doc['metadata']),
                    similarity=None  # Non calcolata per fetch diretto
                )

                logger.info(f"Document {doc_id} retrieved successfully")
                return chunk

            logger.warning(f"Document {doc_id} not found")
            return None

        except Exception as e:
            logger.error(f"Error fetching document {doc_id}: {e}")
            return None

    def get_documents_by_category(
        self,
        category: str,
        limit: int = 10
    ) -> List[DocumentChunk]:
        """
        Recupera documenti per categoria (senza similarity search).

        Utile per browsing o listing di documenti.

        Args:
            category: Nome categoria da filtrare
            limit: Numero massimo documenti da ritornare

        Returns:
            Lista di DocumentChunk
        """
        try:
            logger.info(f"Fetching documents by category: {category} (limit: {limit})")

            response = self.client.table(self.table_name)\
                .select("id, content, metadata")\
                .eq("metadata->>category", category)\
                .limit(limit)\
                .execute()

            if not response.data:
                logger.warning(f"No documents found for category: {category}")
                return []

            chunks = []
            for doc in response.data:
                try:
                    chunks.append(DocumentChunk(
                        id=doc['id'],
                        content=doc['content'],
                        metadata=DocumentMetadata(**doc['metadata']),
                        similarity=None
                    ))
                except Exception as e:
                    logger.error(f"Error parsing document: {e}")
                    continue

            logger.info(f"Retrieved {len(chunks)} documents for category: {category}")
            return chunks

        except Exception as e:
            logger.error(f"Error fetching documents by category: {e}")
            return []

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Ritorna statistiche sul database documenti.

        Utile per monitoring e debugging.

        Returns:
            Dictionary con statistiche (count, categorie, etc.)
        """
        try:
            logger.info("Fetching database statistics")

            # Count totale documenti
            response = self.client.table(self.table_name)\
                .select("id", count="exact")\
                .execute()

            total_docs = response.count if response.count else 0

            # Questo è un esempio - in produzione potresti fare query più complesse
            stats = {
                "total_documents": total_docs,
                "table_name": self.table_name,
                "embedding_dimension": self.embedding_dimension,
                "status": "connected" if total_docs > 0 else "empty"
            }

            logger.info(f"Database stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error fetching database stats: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Crea istanza singleton del servizio RAG
# In questo modo viene inizializzato una volta sola all'avvio dell'app
try:
    rag_service = RAGService()
    logger.info("Global RAG service instance created")
except Exception as e:
    logger.error(f"Failed to create global RAG service: {e}")
    rag_service = None
