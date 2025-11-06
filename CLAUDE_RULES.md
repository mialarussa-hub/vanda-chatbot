# Regole di Sviluppo per Claude

## REGOLA D'ORO: Chiedere Sempre Permesso

**PRIMA** di modificare o creare qualsiasi file, **DEVI**:

1. **FERMARTI** e spiegare il piano
2. Dire **COSA** vuoi modificare (file, linee, codice)
3. Spiegare **PERCHÉ** (quale problema risolve)
4. **ATTENDERE** esplicito consenso ("procedi", "ok", "vai")
5. **SOLO DOPO** procedere con le modifiche

## Workflow Obbligatorio

```
❌ SBAGLIATO:
- Analizzare problema
- Modificare file direttamente
- Informare utente dopo

✅ CORRETTO:
- Analizzare problema
- FERMARSI
- Spiegare: "Ho trovato il problema in [file]. Vorrei modificare [cosa] per [perché]. Posso procedere?"
- Attendere risposta
- Procedere solo dopo consenso
```

## Eccezioni

Puoi procedere SENZA chiedere solo per:
- Leggere file (Read, Glob, Grep)
- Eseguire comandi di lettura (git status, ls, cat, etc.)
- Analisi e ricerche

## Parametri Configurabili

NON hardcodare valori se esiste un pannello admin o configurazione database.

Esempio:
- ❌ `match_count=5, match_threshold=0.60` (hardcoded)
- ✅ `match_count=None, match_threshold=None` (usa defaults da admin panel)

## Ricorda

L'utente ha strumenti (admin panel, database config) per configurare il sistema.
Usa gli strumenti esistenti, non creare workaround.

---

**Queste regole sono SEMPRE attive. Leggile ad ogni riavvio.**
