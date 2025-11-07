"""
Test inline per Intent Classifier (zero dipendenze).
"""

# Implementazione inline semplificata dell'Intent Classifier
class SimpleIntentClassifier:
    CATEGORY_KEYWORDS = {
        "portfolio": [
            "progetto", "progetti", "portfolio", "lavoro", "lavori",
            "realizzato", "realizzati", "realizzazione",
            "case study", "esempio", "esempi",
            "mostra", "mostrami", "vedi", "vedere", "guarda", "guardare",
            "visto", "fatto", "fatti",
            "risultati", "completato", "completati",
            "interior", "design", "ristrutturazione", "arredamento",
            "appartamento", "casa", "ufficio", "negozio", "locale",
            "burgos", "campana", "cliente"
        ],
        "servizi": [
            "servizio", "servizi", "offrite", "offre", "cosa fate", "cosa fa",
            "consulenza", "consulenze", "progettazione", "design",
            "arredamento", "interior design", "ristrutturazione",
            "render", "rendering", "3d", "planimetria",
            "su misura", "personalizzato", "personalizzati",
            "come funziona", "come lavorate", "processo", "metodo",
            "quanto costa", "prezzo", "prezzi", "costo", "costi",
            "potete", "riuscite", "fate", "offrite", "disponibile"
        ],
        "informazioni": [
            "chi siete", "chi sei", "chi è vanda", "vanda",
            "presentazione", "storia", "da quanto", "quando",
            "team", "staff", "persone", "architetti", "designer",
            "contatto", "contatti", "contattare", "email", "telefono",
            "dove", "dove siete", "sede", "indirizzo", "ubicazione",
            "trovare", "trovarvi",
            "orario", "orari", "quando", "appuntamento",
            "azienda", "studio", "società", "attività"
        ]
    }

    def detect_category(self, query):
        if not query or len(query.strip()) == 0:
            return None

        query_lower = query.lower()
        scores = {}

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            scores[category] = score

        if not scores or all(score == 0 for score in scores.values()):
            return None

        max_category = max(scores, key=scores.get)
        return max_category if scores[max_category] > 0 else None


# Crea istanza
classifier = SimpleIntentClassifier()

# Query di test
test_cases = [
    # PORTFOLIO
    ("Mostrami i vostri progetti", "portfolio"),
    ("Avete fatto lavori a Burgos?", "portfolio"),
    ("Quali progetti avete realizzato?", "portfolio"),
    ("Vorrei vedere il vostro portfolio", "portfolio"),
    ("Mi mostri esempi di interior design?", "portfolio"),
    ("Progetti di ristrutturazione", "portfolio"),

    # SERVIZI
    ("Quali servizi offrite?", "servizi"),
    ("Cosa fate esattamente?", "servizi"),
    ("Fate consulenze di interior design?", "servizi"),
    ("Quanto costa una ristrutturazione?", "servizi"),
    ("Come funziona il vostro processo?", "servizi"),
    ("Fate rendering 3D?", "servizi"),
    ("Offrite progettazione su misura?", "servizi"),

    # INFORMAZIONI
    ("Chi siete?", "informazioni"),
    ("Dove si trova lo studio?", "informazioni"),
    ("Come posso contattarvi?", "informazioni"),
    ("Parlami del vostro team", "informazioni"),
    ("Chi è Vanda?", "informazioni"),
    ("Qual è il vostro indirizzo?", "informazioni"),

    # AMBIGUE (nessuna categoria)
    ("Ciao", None),
    ("Grazie", None),
    ("Ok", None),
    ("Interessante", None),
]

print("=" * 90)
print("TEST INTENT CLASSIFIER")
print("=" * 90)
print()

correct = 0
total = len(test_cases)

for query, expected_category in test_cases:
    detected = classifier.detect_category(query)
    is_correct = detected == expected_category

    if is_correct:
        correct += 1
        status = "[OK]"
    else:
        status = "[FAIL]"

    print(f"{status} \"{query}\"")
    exp_str = str(expected_category) if expected_category else "None"
    det_str = str(detected) if detected else "None"
    print(f"   Expected: {exp_str:15s} | Detected: {det_str:15s}")

    if not is_correct:
        print(f"   WARNING: MISMATCH!")

    print()

print("=" * 90)
print(f"RISULTATO FINALE: {correct}/{total} corretti ({(correct/total)*100:.1f}%)")
print("=" * 90)

# Calcola accuracy per categoria
categories = ["portfolio", "servizi", "informazioni"]
for cat in categories:
    cat_tests = [(q, e) for q, e in test_cases if e == cat]
    cat_correct = sum(1 for q, e in cat_tests if classifier.detect_category(q) == e)
    cat_total = len(cat_tests)
    if cat_total > 0:
        print(f"{cat.upper():15s}: {cat_correct}/{cat_total} ({(cat_correct/cat_total)*100:.1f}%)")
