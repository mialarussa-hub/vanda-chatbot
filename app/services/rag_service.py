"""
RAG Service per VANDA chatbot.

Gestisce:
- Similarity search su Supabase vector database usando pgvector
- Retrieval di documenti rilevanti con filtri metadata
- Formattazione context per LLM

IMPORTANTE: Usa PostgreSQL stored function con pgvector per performance ottimali.
"""

from supabase import create_client, Client
from app.config import settings
from app.models.schemas import DocumentChunk, MetadataFilter, DocumentMetadata
from app.services.config_service import get_config_service
from typing import List, Optional, Dict, Any
from loguru import logger


class RAGService:
    """
    Servizio per Retrieval-Augmented Generation.

    Gestisce la ricerca di documenti simili nel database vettoriale Supabase
    usando pg vector con stored functions per performance ottimali.
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

            # Carica configurazioni dinamiche da DB (con fallback a settings)
            self._load_dynamic_config()

            self.embedding_dimension = 1536  # OpenAI text-embedding-3-small

            logger.info(f"RAG Service initialized - Table: {self.table_name}")

        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            raise

    def _load_dynamic_config(self):
        """Carica configurazioni dinamiche da DB con fallback a settings"""
        try:
            config_service = get_config_service()

            # Carica parametri RAG
            rag_params = config_service.get_rag_parameters()
            self.default_match_count = rag_params.get("match_count", settings.RAG_DEFAULT_MATCH_COUNT)
            self.default_match_threshold = rag_params.get("match_threshold", settings.RAG_DEFAULT_MATCH_THRESHOLD)
            self.max_context_length = rag_params.get("max_context_length", 8000)
            self.enable_metadata_filters = rag_params.get("enable_metadata_filters", True)

            logger.info("Dynamic RAG configuration loaded from DB")

        except Exception as e:
            logger.warning(f"Failed to load dynamic RAG config, using settings fallback: {e}")
            # Fallback completo a settings
            self.default_match_count = settings.RAG_DEFAULT_MATCH_COUNT
            self.default_match_threshold = settings.RAG_DEFAULT_MATCH_THRESHOLD
            self.max_context_length = 8000
            self.enable_metadata_filters = True

    def reload_config(self) -> bool:
        """
        Ricarica le configurazioni dal database.

        Returns:
            True se ricaricamento riuscito, False altrimenti
        """
        try:
            logger.info("Reloading RAG configuration from database...")

            # Svuota cache
            config_service = get_config_service()
            config_service.clear_cache()

            # Ricarica config
            self._load_dynamic_config()

            logger.info(
                f"RAG configuration reloaded - Match count: {self.default_match_count}, "
                f"Threshold: {self.default_match_threshold}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to reload RAG configuration: {e}")
            return False

    def search_similar_documents(
        self,
        query_embedding: List[float],
        match_count: Optional[int] = None,
        match_threshold: Optional[float] = None,
        metadata_filter: Optional[MetadataFilter] = None
    ) -> List[DocumentChunk]:
        """
        Cerca documenti simili usando PostgreSQL stored function con pgvector.

        Usa la funzione match_documents() che sfrutta l'operatore <=> di pgvector
        e l'indice HNSW per ricerche veloci e similarity scores accurate (0.7-0.9).

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
                f"🔍 Vector search via RPC - "
                f"match_count: {match_count}, threshold: {match_threshold}"
            )

            # ================================================================
            # VECTOR SEARCH: Usa PostgreSQL stored function (pgvector)
            # ================================================================

            # Chiama la funzione database usando RPC
            # La funzione usa l'operatore <=> (cosine distance) di pgvector
            # e l'indice HNSW per ricerca veloce
            response = self.client.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': match_threshold,
                    'match_count': match_count
                }
            ).execute()

            if not response.data:
                logger.warning("No documents found matching the similarity threshold")
                return []

            logger.info(f"✅ Retrieved {len(response.data)} similar documents")

            results = response.data

            # Applica filtri metadata client-side se forniti
            if metadata_filter:
                results = self._filter_results_by_metadata(results, metadata_filter)
                logger.info(f"After metadata filtering: {len(results)} documents")

            # Log similarity scores per debugging
            if results:
                similarities = [r['similarity'] for r in results]
                logger.info(f"📊 Similarity range: {min(similarities):.3f} - {max(similarities):.3f}")

                # Log top 5 documenti
                logger.info("📋 Top 5 documents:")
                for idx, r in enumerate(results[:5], 1):
                    heading = r['metadata'].get('heading', 'NO TITLE')
                    priority = r['metadata'].get('priority', 0)
                    logger.info(f"  [{idx}] {heading} | Priority: {priority} | Sim: {r['similarity']:.3f}")

            # Converti in DocumentChunk Pydantic models
            chunks = []
            for r in results:
                try:
                    chunks.append(DocumentChunk(
                        id=r['id'],
                        content=r['content'],
                        metadata=DocumentMetadata(**r['metadata']),
                        similarity=round(r['similarity'], 4)
                    ))
                except Exception as e:
                    logger.error(f"Error creating DocumentChunk: {e}")
                    continue

            logger.info(
                f"Found {len(chunks)} relevant documents "
                f"(threshold: {match_threshold})"
            )

            return chunks

        except Exception as e:
            logger.error(f"Error in similarity search: {e}", exc_info=True)
            return []

    def _filter_results_by_metadata(
        self,
        results: List[Dict[str, Any]],
        metadata_filter: MetadataFilter
    ) -> List[Dict[str, Any]]:
        """
        Applica filtri metadata ai risultati della ricerca (client-side).

        NOTA: Per performance migliori, questi filtri dovrebbero essere
        integrati nella funzione PostgreSQL match_documents().

        Args:
            results: Lista di risultati dalla ricerca
            metadata_filter: Filtri da applicare

        Returns:
            Lista filtrata di risultati
        """
        filtered = []

        for result in results:
            metadata = result.get('metadata', {})

            # Controlla ogni condizione del filtro
            if metadata_filter.category and metadata.get('category') != metadata_filter.category:
                continue
            if metadata_filter.subcategory and metadata.get('subcategory') != metadata_filter.subcategory:
                continue
            if metadata_filter.client and metadata.get('client') != metadata_filter.client:
                continue
            if metadata_filter.brand and metadata.get('brand') != metadata_filter.brand:
                continue
            if metadata_filter.client_type and metadata.get('client_type') != metadata_filter.client_type:
                continue
            if metadata_filter.visibility and metadata.get('visibility') != metadata_filter.visibility:
                continue
            if metadata_filter.featured is not None and metadata.get('featured') != metadata_filter.featured:
                continue
            if metadata_filter.min_priority is not None and metadata.get('priority', 0) < metadata_filter.min_priority:
                continue
            if metadata_filter.project_scale and metadata.get('project_scale') != metadata_filter.project_scale:
                continue
            if metadata_filter.document_type and metadata.get('document_type') != metadata_filter.document_type:
                continue

            filtered.append(result)

        return filtered

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
                # Costruisci sezione documento con TUTTI i metadati rilevanti
                doc_section = f"[DOCUMENTO {i}]"

                if include_metadata:
                    # Metadati principali
                    if doc.metadata.heading:
                        doc_section += f"\nTitolo: {doc.metadata.heading}"

                    if doc.metadata.document_type:
                        doc_section += f"\nTipo: {doc.metadata.document_type}"

                    if doc.metadata.category:
                        doc_section += f"\nCategoria: {doc.metadata.category}"

                    if doc.metadata.subcategory:
                        doc_section += f"\nSottocategoria: {doc.metadata.subcategory}"

                    # Informazioni cliente/brand
                    if doc.metadata.client:
                        doc_section += f"\nCliente: {doc.metadata.client}"

                    if doc.metadata.brand:
                        doc_section += f"\nBrand: {doc.metadata.brand}"

                    if doc.metadata.client_type:
                        doc_section += f"\nTipologia: {doc.metadata.client_type}"

                    # URL (CRITICO per evitare allucinazioni di link!)
                    if doc.metadata.url:
                        doc_section += f"\nURL: {doc.metadata.url}"

                    # Priorità e visibilità (per sistema di ordinamento)
                    if doc.metadata.priority is not None:
                        doc_section += f"\nPriority: {doc.metadata.priority}"

                    if doc.metadata.featured is not None:
                        doc_section += f"\nFeatured: {'Sì' if doc.metadata.featured else 'No'}"

                    if doc.metadata.visibility:
                        doc_section += f"\nVisibility: {doc.metadata.visibility}"

                    if doc.metadata.project_scale:
                        doc_section += f"\nScale: {doc.metadata.project_scale}"

                    # Tags e similarity
                    if doc.metadata.tags:
                        doc_section += f"\nTags: {doc.metadata.tags}"

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
