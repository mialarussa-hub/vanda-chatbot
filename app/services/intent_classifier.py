"""
Intent Classifier per VANDA Chatbot.

Classifica automaticamente l'intento dell'utente per applicare
filtri category appropriati alla ricerca RAG.

Categories supportate:
- portfolio: Progetti, lavori realizzati, case studies
- servizi: Servizi offerti, consulenze, cosa fa lo studio
- informazioni: Info sullo studio, contatti, team, storia
"""

from typing import Optional, Dict, List
from loguru import logger


class IntentClassifier:
    """
    Classificatore di intenti basato su keywords.

    Analizza la query dell'utente e determina automaticamente
    se appartiene a una delle categorie predefinite.
    """

    # Definizione keywords per categoria
    CATEGORY_KEYWORDS = {
        "portfolio": [
            # Progetti e lavori
            "progetto", "progetti", "portfolio", "lavoro", "lavori",
            "realizzato", "realizzati", "realizzazione",
            # Case studies
            "case study", "esempio", "esempi",
            # Verbi di richiesta
            "mostra", "mostrami", "vedi", "vedere", "guarda", "guardare",
            "visto", "fatto", "fatti",
            # Risultati
            "risultati", "completato", "completati",
            # Specifici
            "interior", "design", "ristrutturazione", "arredamento",
            "appartamento", "casa", "ufficio", "negozio", "locale",
            # Nomi clienti comuni (aggiungi se necessario)
            "burgos", "campana", "cliente"
        ],

        "servizi": [
            # Servizi principali
            "servizio", "servizi", "offrite", "offre", "cosa fate", "cosa fa",
            "consulenza", "consulenze", "progettazione", "design",
            # Tipologie servizio
            "arredamento", "interior design", "ristrutturazione",
            "render", "rendering", "3d", "planimetria",
            "su misura", "personalizzato", "personalizzati",
            # Domande tipiche
            "come funziona", "come lavorate", "processo", "metodo",
            "quanto costa", "prezzo", "prezzi", "costo", "costi",
            # Capabilities
            "potete", "riuscite", "fate", "offrite", "disponibile"
        ],

        "informazioni": [
            # Info studio
            "chi siete", "chi sei", "chi è vanda", "vanda",
            "presentazione", "storia", "da quanto", "quando",
            # Team
            "team", "staff", "persone", "architetti", "designer",
            # Contatti
            "contatto", "contatti", "contattare", "email", "telefono",
            "dove", "dove siete", "sede", "indirizzo", "ubicazione",
            "trovare", "trovarvi",
            # Orari e disponibilità
            "orario", "orari", "quando", "appuntamento",
            # Azienda
            "azienda", "studio", "società", "attività"
        ]
    }

    def __init__(self):
        """Inizializza il classificatore."""
        logger.info("Intent Classifier initialized")

    def detect_category(self, query: str) -> Optional[str]:
        """
        Rileva automaticamente la categoria dalla query utente.

        Args:
            query: Messaggio dell'utente

        Returns:
            Nome categoria ("portfolio" | "servizi" | "informazioni")
            o None se nessun match
        """
        if not query or len(query.strip()) == 0:
            return None

        query_lower = query.lower()

        # Calcola score per ogni categoria
        scores = self._calculate_scores(query_lower)

        # Log dei punteggi
        logger.debug(f"Intent scores: {scores}")

        # Trova categoria con score massimo
        if not scores or all(score == 0 for score in scores.values()):
            logger.info("❓ No clear category intent detected")
            return None

        max_category = max(scores, key=scores.get)
        max_score = scores[max_category]

        # Richiedi almeno 1 match per considerarlo valido
        if max_score > 0:
            logger.info(f"🎯 Detected category: {max_category} (score: {max_score})")
            return max_category

        return None

    def _calculate_scores(self, query_lower: str) -> Dict[str, int]:
        """
        Calcola score di matching per ogni categoria.

        Args:
            query_lower: Query in lowercase

        Returns:
            Dict con score per categoria
        """
        scores = {}

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            # Conta quante keywords matchano
            score = sum(1 for keyword in keywords if keyword in query_lower)
            scores[category] = score

        return scores

    def get_detailed_analysis(self, query: str) -> Dict[str, any]:
        """
        Analisi dettagliata dell'intento (per debugging/monitoring).

        Args:
            query: Messaggio dell'utente

        Returns:
            Dict con categoria, scores, keywords matchate
        """
        query_lower = query.lower()
        scores = self._calculate_scores(query_lower)
        detected_category = self.detect_category(query)

        # Trova keywords matchate per ogni categoria
        matched_keywords = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in query_lower]
            if matched:
                matched_keywords[category] = matched

        return {
            "query": query,
            "detected_category": detected_category,
            "scores": scores,
            "matched_keywords": matched_keywords,
            "confidence": max(scores.values()) if scores else 0
        }

    def add_keywords(self, category: str, keywords: List[str]) -> bool:
        """
        Aggiunge keywords personalizzate a una categoria.

        Utile per estendere il classificatore con termini specifici.

        Args:
            category: Nome categoria
            keywords: Lista di keywords da aggiungere

        Returns:
            True se aggiunto con successo
        """
        if category not in self.CATEGORY_KEYWORDS:
            logger.warning(f"Category {category} not found")
            return False

        # Converti a lowercase e aggiungi
        new_keywords = [kw.lower() for kw in keywords]
        self.CATEGORY_KEYWORDS[category].extend(new_keywords)

        logger.info(f"Added {len(new_keywords)} keywords to category {category}")
        return True


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Crea istanza singleton
intent_classifier = IntentClassifier()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def detect_category_intent(query: str) -> Optional[str]:
    """
    Helper function per rilevare categoria dall'intento.

    Shortcut per intent_classifier.detect_category()

    Args:
        query: Messaggio utente

    Returns:
        Nome categoria o None
    """
    return intent_classifier.detect_category(query)


def get_intent_analysis(query: str) -> Dict[str, any]:
    """
    Helper function per analisi dettagliata intento.

    Args:
        query: Messaggio utente

    Returns:
        Dict con analisi completa
    """
    return intent_classifier.get_detailed_analysis(query)
