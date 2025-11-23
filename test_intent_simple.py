"""
Test semplice per Intent Classifier (senza dipendenze).

Importa direttamente il modulo intent_classifier
senza passare da __init__.py per evitare problemi di dipendenze.
"""

# Import diretto del file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "intent_classifier",
    "D:\\PROGETTI\\AGENTIKA\\WEB\\vanda-chatbot\\app\\services\\intent_classifier.py"
)
intent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intent_module)

# Usa la classe IntentClassifier
IntentClassifier = intent_module.IntentClassifier
intent_classifier = IntentClassifier()

# Query di test
test_cases = [
    # PORTFOLIO
    ("Mostrami i vostri progetti", "portfolio"),
    ("Avete fatto lavori a Burgos?", "portfolio"),
    ("Quali progetti avete realizzato?", "portfolio"),
    ("Vorrei vedere il vostro portfolio", "portfolio"),
    ("Mi mostri esempi di interior design?", "portfolio"),

    # SERVIZI
    ("Quali servizi offrite?", "servizi"),
    ("Cosa fate esattamente?", "servizi"),
    ("Fate consulenze di interior design?", "servizi"),
    ("Quanto costa una ristrutturazione?", "servizi"),
    ("Come funziona il vostro processo?", "servizi"),

    # INFORMAZIONI
    ("Chi siete?", "informazioni"),
    ("Dove si trova lo studio?", "informazioni"),
    ("Come posso contattarvi?", "informazioni"),
    ("Parlami del vostro team", "informazioni"),
    ("Chi è Vanda?", "informazioni"),

    # AMBIGUE (nessuna categoria)
    ("Ciao", None),
    ("Grazie", None),
    ("Ok", None),
]

print("=" * 80)
print("TEST INTENT CLASSIFIER - QUICK TEST")
print("=" * 80)
print()

correct = 0
total = len(test_cases)

for query, expected_category in test_cases:
    detected = intent_classifier.detect_category(query)
    is_correct = detected == expected_category

    if is_correct:
        correct += 1
        status = "✅"
    else:
        status = "❌"

    print(f"{status} \"{query}\"")
    print(f"   Expected: {expected_category}")
    print(f"   Detected: {detected}")
    print()

print("=" * 80)
print(f"RISULTATO: {correct}/{total} corretti ({(correct/total)*100:.1f}%)")
print("=" * 80)
