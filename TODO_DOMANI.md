# 📋 TODO - PROSSIMA SESSIONE

**Data creazione:** 5 Gennaio 2025
**Priorità:** ⭐⭐⭐ ALTA

---

## 🔥 TASK PRIORITARIO: Setup GitHub Auto-Deploy

### Obiettivo
Collegare GitHub repository a Google Cloud Build per deploy automatici.

### Benefici
- ✅ **Deploy automatico**: `git push` → deploy automatico (no più deploy.bat)
- ✅ **Risparmio tempo**: Da 6 step manuali a 3 step automatici
- ✅ **Versionamento**: Ogni commit tracciato e rollback facile
- ✅ **Zero errori**: Niente più comandi manuali sbagliati

### Tempo stimato
⏱️ 10-15 minuti setup completo

---

## 📝 STEP DA SEGUIRE

### 1. Verifica Repository GitHub
- [ ] Repo esistente? Se no, crearlo
- [ ] Codice pushato su GitHub?
- [ ] Branch principale: `main` o `master`?

### 2. Collega GitHub a Google Cloud
```bash
gcloud builds connections create github vanda-github --region=europe-west1
```
**Nota:** Si aprirà browser per autorizzare GitHub

### 3. Crea Trigger Automatico
```bash
gcloud builds triggers create github \
  --name="vanda-auto-deploy" \
  --repo-owner="TUO_USERNAME_GITHUB" \
  --repo-name="NOME_REPO" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --region=europe-west1
```

### 4. Crea file cloudbuild.yaml
Creare nella root del progetto:

```yaml
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/vanda-chatbot', '.']

  # Push image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/vanda-chatbot']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'vanda-chatbot'
      - '--image=gcr.io/$PROJECT_ID/vanda-chatbot'
      - '--region=europe-west1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=1Gi'
      - '--cpu=1'
      - '--timeout=60s'
      - '--max-instances=10'
      - '--min-instances=0'
      - '--set-env-vars=ENV=production,LOG_LEVEL=INFO,SUPABASE_TABLE_NAME=documents,RAG_DEFAULT_MATCH_COUNT=3,RAG_DEFAULT_MATCH_THRESHOLD=0.60,LLM_DEFAULT_MODEL=gpt-4o-mini,LLM_DEFAULT_TEMPERATURE=0.5,LLM_MAX_TOKENS=800,LLM_STREAM_ENABLED=true'
      - '--set-secrets=OPENAI_API_KEY=openai-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest'

timeout: 1200s  # 20 minuti max
```

### 5. Test
```bash
# Fai una piccola modifica
echo "# Test deploy" >> README.md

# Commit e push
git add .
git commit -m "test: Trigger auto-deploy"
git push

# Monitora build
gcloud builds list --limit=5
gcloud builds log [BUILD_ID] --stream
```

---

## 🎯 WORKFLOW FINALE

### Prima (Manuale):
```
1. Modifica Python ✏️
2. Testa locale 🧪
3. Apri CMD 💻
4. cd directory 📁
5. Lancia deploy.bat ⚙️
6. Aspetta 3-5 minuti ⏳
7. Verifica produzione ✅
```

### Dopo (Automatico):
```
1. Modifica Python ✏️
2. Testa locale 🧪
3. git add . && git commit -m "fix" && git push 🚀
4. Deploy automatico in background ✅
```

**Risparmio tempo:** ~3 minuti per deploy + zero errori umani!

---

## 📚 DOCUMENTAZIONE

**Google Cloud Build:**
https://cloud.google.com/build/docs/automating-builds/github/build-repos-from-github

**Cloud Run Deployment:**
https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run

---

## 🔧 TROUBLESHOOTING PREVENTIVO

### Se fallisce connessione GitHub:
```bash
# Verifica connessioni esistenti
gcloud builds connections list --region=europe-west1

# Ricrea connessione
gcloud builds connections delete vanda-github --region=europe-west1
gcloud builds connections create github vanda-github --region=europe-west1
```

### Se trigger non parte:
- Verifica branch name sia corretto (main vs master)
- Controlla che cloudbuild.yaml sia nella root
- Verifica permessi IAM Cloud Build Service Account

### Se build fallisce:
```bash
# Vedi log dettagliato
gcloud builds log [BUILD_ID] --stream

# Verifica secrets accessibili
gcloud secrets list
```

---

## ✅ CHECKLIST COMPLETAMENTO

Una volta fatto tutto:

- [ ] GitHub collegato a Google Cloud
- [ ] Trigger creato e attivo
- [ ] cloudbuild.yaml committato
- [ ] Test deploy funzionante
- [ ] Documentato workflow in README.md
- [ ] Eliminato deploy.bat (opzionale, tienilo come backup)

---

## 💡 NOTE AGGIUNTIVE

**Costi:** Cloud Build ha 120 minuti gratis/giorno. Ogni deploy ~2-3 minuti = ~40-60 deploy gratis/giorno. Più che sufficiente!

**Sicurezza:** I secrets rimangono su Google Secret Manager, non vanno su GitHub.

**Rollback:** Se un deploy rompe qualcosa, facile tornare indietro dal Cloud Console.

---

**Status attuale:** ⏸️ DA FARE
**Quando fatto:** Aggiorna questo file con ✅ COMPLETATO

---

🎯 **OBIETTIVO:** Deploy automatici con `git push` invece di comandi manuali!
