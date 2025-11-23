"""
Test per Intent Classifier.

Testa il classificatore di intenti con diverse query
per verificare che rilevi correttamente le categorie.
"""

import sys
from pathlib import Path

# Aggiungi la directory app al path
sys.path.insert(0, str(Path(__file__).parent))

# Import diretto della classe (evita problemi con altri servizi)
from app.services.intent_classifier import IntentClassifier

# Crea istanza locale per il test
intent_classifier = IntentClassifier()


def test_intent_classifier():
    """Testa il classificatore con query di esempio."""

    # Query di test per categoria PORTFOLIO
    portfolio_queries = [
        "Mostrami i vostri progetti",
        "Avete fatto lavori a Burgos?",
        "Quali progetti avete realizzato?",
        "Vorrei vedere il vostro portfolio",
        "Mi mostri esempi di interior design?",
        "Avete case study da mostrarmi?",
        "Progetti di ristrutturazione appartamenti"
    ]

    # Query di test per categoria SERVIZI
    servizi_queries = [
        "Quali servizi offrite?",
        "Cosa fate esattamente?",
        "Fate consulenze di interior design?",
        "Quanto costa una ristrutturazione?",
        "Offrite servizi di progettazione?",
        "Come funziona il vostro processo?",
        "Fate rendering 3D?",
        "Potete fare arredamento su misura?"
    ]

    # Query di test per categoria INFORMAZIONI
    info_queries = [
        "Chi siete?",
        "Dove si trova lo studio?",
        "Come posso contattarvi?",
        "Qual è il vostro indirizzo email?",
        "Parlami del vostro team",
        "Da quanto tempo fate questo lavoro?",
        "Dove siete ubicati?",
        "Chi è Vanda?"
    ]

    # Query ambigue (dovrebbero ritornare None o categoria più generica)
    ambiguous_queries = [
        "Ciao",
        "Buongiorno",
        "Grazie",
        "Ok",
        "Interessante"
    ]

    print("=" * 80)
    print("TEST INTENT CLASSIFIER")
    print("=" * 80)

    # Test PORTFOLIO
    print("\n📁 PORTFOLIO QUERIES:")
    print("-" * 80)
    for query in portfolio_queries:
        result = intent_classifier.get_detailed_analysis(query)
        category = result['detected_category']
        score = result['confidence']
        matched = result['matched_keywords']

        status = "✅" if category == "portfolio" else "❌"
        print(f"{status} \"{query}\"")
        print(f"   → Category: {category} (score: {score})")
        if matched:
            print(f"   → Matched: {matched}")
        print()

    # Test SERVIZI
    print("\n🛠️  SERVIZI QUERIES:")
    print("-" * 80)
    for query in servizi_queries:
        result = intent_classifier.get_detailed_analysis(query)
        category = result['detected_category']
        score = result['confidence']
        matched = result['matched_keywords']

        status = "✅" if category == "servizi" else "❌"
        print(f"{status} \"{query}\"")
        print(f"   → Category: {category} (score: {score})")
        if matched:
            print(f"   → Matched: {matched}")
        print()

    # Test INFORMAZIONI
    print("\nℹ️  INFORMAZIONI QUERIES:")
    print("-" * 80)
    for query in info_queries:
        result = intent_classifier.get_detailed_analysis(query)
        category = result['detected_category']
        score = result['confidence']
        matched = result['matched_keywords']

        status = "✅" if category == "informazioni" else "❌"
        print(f"{status} \"{query}\"")
        print(f"   → Category: {category} (score: {score})")
        if matched:
            print(f"   → Matched: {matched}")
        print()

    # Test AMBIGUE
    print("\n❓ AMBIGUOUS QUERIES (should return None or low confidence):")
    print("-" * 80)
    for query in ambiguous_queries:
        result = intent_classifier.get_detailed_analysis(query)
        category = result['detected_category']
        score = result['confidence']

        status = "✅" if category is None else "⚠️"
        print(f"{status} \"{query}\"")
        print(f"   → Category: {category} (score: {score})")
        print()

    print("=" * 80)
    print("TEST COMPLETATO")
    print("=" * 80)


if __name__ == "__main__":
    test_intent_classifier()
