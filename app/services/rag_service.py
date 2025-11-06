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
from app.services.config_service import get_config_service
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

    # ========================================================================
    # HYBRID SEARCH - QUERY CLASSIFICATION & ENTITY EXTRACTION
    # ========================================================================

    def _classify_query_type(self, query: str) -> Dict[str, Any]:
        """
        Classifica il tipo di query per determinare la strategia di ricerca ottimale.

        Analizza la query per riconoscere:
        - Nomi propri/entità (es. "Campana di Ferro", "Zara", "Alessandro")
        - Categorie specifiche (es. "retail", "food", "lusso")
        - Query generiche/semantiche (es. "quali servizi", "progetti importanti")

        Args:
            query: Query utente da classificare

        Returns:
            Dictionary con:
                - type: "entity_based", "category_based", o "semantic"
                - entities: Lista di entità estratte (se trovate)
                - categories: Lista di categorie identificate (se trovate)
                - confidence: Livello di confidenza (0.0-1.0)

        Examples:
            >>> _classify_query_type("mostrami il progetto Campana di Ferro")
            {"type": "entity_based", "entities": ["Campana di Ferro"], "confidence": 0.9}

            >>> _classify_query_type("quali sono i progetti retail")
            {"type": "category_based", "categories": ["retail"], "confidence": 0.8}

            >>> _classify_query_type("parlami dei vostri servizi")
            {"type": "semantic", "confidence": 1.0}
        """
        import re

        query_lower = query.lower()
        result = {
            "type": "semantic",
            "entities": [],
            "categories": [],
            "confidence": 1.0
        }

        # ====================================================================
        # 1. ESTRAI ENTITÀ (NOMI PROPRI)
        # ====================================================================

        # Pattern per nomi propri italiani:
        # - Due o più parole con maiuscola iniziale
        # - Può includere articoli/preposizioni: "di", "del", "della", "dei", "degli"
        # - Es: "Campana di Ferro", "Casa T", "Zara Home", "Alessandro Paganini"
        entity_patterns = [
            # Pattern 1: Nome + preposizione + Nome (es. "Campana di Ferro")
            r'\b([A-Z][a-zàèéìòù]+(?:\s+(?:di|del|della|dei|degli|delle)\s+[A-Z][a-zàèéìòù]+)+)\b',
            # Pattern 2: Due o più parole con maiuscola (es. "Zara Home", "Casa T")
            r'\b([A-Z][a-zàèéìòù]+(?:\s+[A-Z][a-zàèéìòù]+)+)\b',
            # Pattern 3: Acronimi o nomi brevi maiuscoli (es. "WTC", "ZARA")
            r'\b([A-Z]{2,})\b',
            # Pattern 4: Nome + iniziale (es. "Alessandro P.", "Mario R.")
            r'\b([A-Z][a-zàèéìòù]+\s+[A-Z]\.?)\b',
        ]

        entities = []
        for pattern in entity_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)

        # Rimuovi duplicati preservando ordine
        entities = list(dict.fromkeys(entities))

        # Filtra false positive comuni
        false_positives = ["Vanda", "Vanda Designers", "Designers"]  # Nome dell'azienda stessa
        entities = [e for e in entities if e not in false_positives]

        if entities:
            result["entities"] = entities
            result["type"] = "entity_based"
            result["confidence"] = 0.9
            logger.debug(f"🔍 QUERY TYPE: entity_based | Entities: {entities}")
            return result

        # ====================================================================
        # 2. IDENTIFICA CATEGORIE
        # ====================================================================

        # Categorie note nel database (case-insensitive)
        known_categories = {
            "retail": ["retail", "negozio", "negozi", "store", "punto vendita"],
            "food": ["food", "ristorante", "ristoranti", "bar", "caffè", "cafe"],
            "lusso": ["lusso", "luxury", "premium", "alta gamma"],
            "hospitality": ["hospitality", "hotel", "albergo", "resort"],
            "residenziale": ["residenziale", "casa", "appartamento", "abitazione"],
            "uffici": ["ufficio", "uffici", "office", "coworking"],
            "showroom": ["showroom", "esposizione"],
            "corporate": ["corporate", "aziendale"]
        }

        categories_found = []
        for category, keywords in known_categories.items():
            for keyword in keywords:
                if keyword in query_lower:
                    categories_found.append(category)
                    break  # Trova solo una volta per categoria

        if categories_found:
            result["categories"] = categories_found
            result["type"] = "category_based"
            result["confidence"] = 0.8
            logger.debug(f"🔍 QUERY TYPE: category_based | Categories: {categories_found}")
            return result

        # ====================================================================
        # 3. DEFAULT: SEMANTIC SEARCH
        # ====================================================================

        logger.debug("🔍 QUERY TYPE: semantic (generic query)")
        return result

    def _search_by_entity(
        self,
        entity: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Cerca documenti per nome entità usando metadata filters.

        Cerca match esatti o parziali nei campi:
        - heading (titolo)
        - client (cliente)
        - brand (brand)
        - tags (tags)

        Args:
            entity: Nome entità da cercare (es. "Campana di Ferro")
            max_results: Numero massimo risultati

        Returns:
            Lista di documenti con formato:
                {
                    'id': int,
                    'content': str,
                    'metadata': dict,
                    'similarity': float,  # 1.0 per match esatti
                    'match_type': str     # 'client', 'heading', 'brand', 'tags'
                }
        """
        try:
            logger.info(f"🔎 Entity search: '{entity}'")

            results = []

            # Cerca in diversi campi metadata usando ILIKE (case-insensitive pattern matching)
            search_fields = [
                ("heading", "metadata->>heading"),
                ("client", "metadata->>client"),
                ("brand", "metadata->>brand"),
                # tags contiene stringhe separate da virgola, quindi usiamo contains
            ]

            for field_name, field_path in search_fields:
                try:
                    # Query con ILIKE per pattern matching case-insensitive
                    # Il pattern %entity% trova "entity" ovunque nella stringa
                    response = self.client.table(self.table_name)\
                        .select("id, content, metadata")\
                        .ilike(field_path, f"%{entity}%")\
                        .limit(max_results)\
                        .execute()

                    if response.data:
                        logger.info(f"  ✅ Found {len(response.data)} matches in '{field_name}'")
                        for doc in response.data:
                            # Evita duplicati (stesso documento già trovato in altro campo)
                            if not any(r['id'] == doc['id'] for r in results):
                                results.append({
                                    'id': doc['id'],
                                    'content': doc['content'],
                                    'metadata': doc['metadata'],
                                    'similarity': 1.0,  # Match esatto = similarity massima
                                    'match_type': field_name
                                })

                except Exception as e:
                    logger.warning(f"Error searching in {field_name}: {e}")
                    continue

            # Cerca anche nei tags (formato diverso: stringa con virgole)
            try:
                response = self.client.table(self.table_name)\
                    .select("id, content, metadata")\
                    .ilike("metadata->>tags", f"%{entity}%")\
                    .limit(max_results)\
                    .execute()

                if response.data:
                    logger.info(f"  ✅ Found {len(response.data)} matches in 'tags'")
                    for doc in response.data:
                        if not any(r['id'] == doc['id'] for r in results):
                            results.append({
                                'id': doc['id'],
                                'content': doc['content'],
                                'metadata': doc['metadata'],
                                'similarity': 1.0,
                                'match_type': 'tags'
                            })

            except Exception as e:
                logger.warning(f"Error searching in tags: {e}")

            # Ordina per priority (se presente) per mostrare progetti importanti per primi
            results.sort(
                key=lambda x: x['metadata'].get('priority', 0),
                reverse=True
            )

            results = results[:max_results]

            logger.info(f"🎯 Entity search completed: {len(results)} total matches")

            return results

        except Exception as e:
            logger.error(f"Error in entity search: {e}")
            return []

    def _merge_hybrid_results(
        self,
        entity_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Combina risultati da entity search e vector search in un'unica lista ordinata.

        Strategia di merge:
        1. Priorità ASSOLUTA ai match esatti da entity search (similarity 1.0)
        2. Aggiunge vector results rimanenti (evitando duplicati)
        3. Limita a max_results

        Args:
            entity_results: Risultati da ricerca entità (metadata-based)
            vector_results: Risultati da ricerca semantica (vector-based)
            max_results: Numero massimo risultati finali

        Returns:
            Lista merged e ordinata di risultati
        """
        try:
            logger.info(f"🔀 Merging results: {len(entity_results)} entity + {len(vector_results)} vector")

            merged = []
            seen_ids = set()

            # ================================================================
            # 1. PRIORITÀ: Match esatti da entity search
            # ================================================================
            for result in entity_results:
                if result['id'] not in seen_ids:
                    merged.append(result)
                    seen_ids.add(result['id'])

            logger.info(f"  📌 Added {len(merged)} entity matches (priority)")

            # ================================================================
            # 2. AGGIUNGI: Vector results (evita duplicati)
            # ================================================================
            vector_added = 0
            for result in vector_results:
                if result['id'] not in seen_ids:
                    merged.append(result)
                    seen_ids.add(result['id'])
                    vector_added += 1

                # Limita al numero massimo
                if len(merged) >= max_results:
                    break

            logger.info(f"  🔍 Added {vector_added} vector matches")

            # ================================================================
            # 3. ORDINA: Entity matches (1.0) in cima, poi per similarity
            # ================================================================
            # A parità di similarity, ordina per priority
            merged.sort(
                key=lambda x: (
                    x['similarity'],
                    x['metadata'].get('priority', 0)
                ),
                reverse=True
            )

            # Limita al numero massimo
            merged = merged[:max_results]

            logger.info(f"✅ Merge completed: {len(merged)} total results")

            # Log breakdown
            entity_count = sum(1 for r in merged if r['similarity'] == 1.0)
            vector_count = len(merged) - entity_count
            logger.info(f"  📊 Breakdown: {entity_count} entity matches + {vector_count} vector matches")

            return merged

        except Exception as e:
            logger.error(f"Error merging results: {e}")
            # Fallback: ritorna solo vector results
            return vector_results[:max_results]

    def search_similar_documents(
        self,
        query_embedding: List[float],
        match_count: Optional[int] = None,
        match_threshold: Optional[float] = None,
        metadata_filter: Optional[MetadataFilter] = None,
        query_text: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Cerca documenti simili usando HYBRID SEARCH (entity-based + vector-based).

        HYBRID SEARCH STRATEGY:
        1. Classifica la query (entity_based, category_based, semantic)
        2. Se entity_based: Cerca match esatti per entità nei metadata
        3. Esegue vector similarity search tradizionale
        4. Merge intelligente dei risultati (entity matches in cima)

        Questo metodo:
        1. Valida l'embedding della query
        2. Classifica la query per determinare strategia ottimale
        3. Applica filtri metadata opzionali
        4. Recupera documenti (entity search + vector search)
        5. Calcola cosine similarity client-side
        6. Filtra per threshold e ordina per similarity
        7. Ritorna top-k risultati

        NOTA: In produzione, questa logica dovrebbe essere spostata in una
        stored procedure PostgreSQL per performance ottimali. Per ora
        calcoliamo la similarity client-side per semplicità.

        Args:
            query_embedding: Vettore embedding della query (1536 dimensioni)
            match_count: Numero massimo di risultati (default: da settings)
            match_threshold: Soglia minima similarity 0-1 (default: da settings)
            metadata_filter: Filtri opzionali per metadata JSONB
            query_text: Testo originale della query (opzionale, per hybrid search)

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
                f"🔍 Searching similar documents - "
                f"match_count: {match_count}, threshold: {match_threshold}"
            )

            # ================================================================
            # HYBRID SEARCH: Classifica query ed esegui entity search
            # ================================================================

            entity_results = []
            query_classification = None

            if query_text:
                # Classifica la query per determinare strategia ottimale
                query_classification = self._classify_query_type(query_text)

                logger.info(
                    f"📋 Query classification: {query_classification['type']} "
                    f"(confidence: {query_classification['confidence']:.2f})"
                )

                # Se la query contiene entità, cerca match esatti nei metadata
                if query_classification['type'] == 'entity_based' and query_classification['entities']:
                    logger.info(f"🎯 HYBRID MODE: Entity-based search activated")
                    logger.info(f"  Entities detected: {query_classification['entities']}")

                    # Cerca per ogni entità rilevata
                    for entity in query_classification['entities']:
                        entity_matches = self._search_by_entity(
                            entity=entity,
                            max_results=match_count
                        )
                        entity_results.extend(entity_matches)

                    # Rimuovi duplicati da entity_results
                    seen_ids = set()
                    unique_entity_results = []
                    for result in entity_results:
                        if result['id'] not in seen_ids:
                            unique_entity_results.append(result)
                            seen_ids.add(result['id'])
                    entity_results = unique_entity_results

                    if entity_results:
                        logger.info(f"✅ Entity search: Found {len(entity_results)} exact matches")
                    else:
                        logger.warning("⚠️ Entity search: No exact matches found, falling back to pure vector search")

                elif query_classification['type'] == 'category_based' and query_classification['categories']:
                    # Se la query contiene categorie, applica filtro metadata
                    logger.info(f"🏷️ CATEGORY MODE: {query_classification['categories']}")
                    # Applica categoria al metadata_filter (se non già presente)
                    if not metadata_filter:
                        metadata_filter = MetadataFilter(category=query_classification['categories'][0])
                    elif not metadata_filter.category:
                        metadata_filter.category = query_classification['categories'][0]

            # ================================================================
            # VECTOR SEARCH: Esegui sempre vector similarity search
            # ================================================================

            logger.info("🧮 Executing vector similarity search...")

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
                logger.error("❌ NO DOCUMENTS FOUND IN DATABASE! Check table name and data.")
                return []

            logger.info(f"✅ Retrieved {len(response.data)} documents from database")

            # DEBUG: Verifica se embeddings sono presenti
            docs_with_embedding = sum(1 for doc in response.data if doc.get('embedding'))
            logger.info(f"📊 Documents with embedding: {docs_with_embedding}/{len(response.data)}")

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

            # DEBUG: Log dei risultati filtrati per threshold
            logger.info(f"📈 Results after threshold filter ({match_threshold}): {len(results)} documents")
            if results:
                similarities = [r['similarity'] for r in results]
                logger.info(f"📊 Similarity range: {min(similarities):.3f} - {max(similarities):.3f}")

                # Log i primi 5 documenti per vedere cosa viene trovato
                logger.info("🔍 Top 5 documents before sorting:")
                for idx, r in enumerate(results[:5], 1):
                    heading = r['metadata'].get('heading', 'NO TITLE')
                    priority = r['metadata'].get('priority', 0)
                    logger.info(f"  [{idx}] {heading} | Priority: {priority} | Sim: {r['similarity']:.3f}")
            else:
                logger.warning(f"⚠️ NO RESULTS after threshold filter! Try lowering threshold from {match_threshold}")

            # ================================================================
            # MERGE RESULTS: Combina entity results + vector results
            # ================================================================

            if entity_results and query_classification:
                # HYBRID MODE: Merge intelligente con priorità agli entity matches
                logger.info("🔀 HYBRID MERGE: Combining entity and vector results...")
                results = self._merge_hybrid_results(
                    entity_results=entity_results,
                    vector_results=results,
                    max_results=match_count
                )
                logger.info(f"✅ Hybrid search completed: {len(results)} merged results")
            else:
                # PURE VECTOR MODE: Ordina solo per similarity + priority
                logger.info("📊 VECTOR MODE: Sorting by similarity + priority...")
                results.sort(
                    key=lambda x: (
                        x['similarity'],
                        x['metadata'].get('priority', 0)  # Priority 0 se non presente
                    ),
                    reverse=True
                )
                results = results[:match_count]

            logger.info(f"🎯 Final results after sorting and limiting to {match_count}: {len(results)} documents")

            # DEBUG: Log titoli e priority dei documenti finali
            if results:
                logger.info("📋 Final documents being sent to LLM:")
                for idx, r in enumerate(results, 1):
                    heading = r['metadata'].get('heading', 'NO TITLE')
                    priority = r['metadata'].get('priority', 0)
                    similarity = r['similarity']
                    logger.info(f"  [{idx}] {heading} | Priority: {priority} | Similarity: {similarity:.3f}")

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
