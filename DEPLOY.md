# VANDA Chatbot - Guida Deploy su Google Cloud Run

## Prerequisiti

### 1. Account Google Cloud
- Crea account su https://console.cloud.google.com
- Abilita fatturazione (free tier: 2M richieste/mese gratis)

### 2. Installa Google Cloud SDK
```bash
# Windows
https://cloud.google.com/sdk/docs/install

# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
```

### 3. Autenticazione
```bash
# Login
gcloud auth login

# Configura progetto (sostituisci con il tuo PROJECT_ID)
gcloud config set project vanda-chatbot-prod

# Verifica config
gcloud config list
```

---

## Deploy Rapido (Opzione 1 - Consigliata)

### Deploy con un solo comando

Cloud Run builda automaticamente l'immagine Docker dal codice sorgente:

```bash
# Dalla root del progetto
gcloud run deploy vanda-chatbot \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60s \
  --max-instances 10 \
  --set-env-vars "ENV=production,LOG_LEVEL=INFO" \
  --set-secrets "OPENAI_API_KEY=openai-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest"
```

**Nota**: I secrets devono essere prima creati in Google Secret Manager (vedi sezione sotto).

---

## Setup Secrets (Google Secret Manager)

### 1. Abilita Secret Manager API
```bash
gcloud services enable secretmanager.googleapis.com
```

### 2. Crea secrets
```bash
# OpenAI API Key
echo -n "sk-proj-..." | gcloud secrets create openai-key --data-file=-

# Supabase URL
echo -n "https://fxveihbatyrlovdvhcbl.supabase.co" | gcloud secrets create supabase-url --data-file=-

# Supabase Key
echo -n "eyJhbGci..." | gcloud secrets create supabase-key --data-file=-

# Supabase Table Name (opzionale)
echo -n "documents" | gcloud secrets create supabase-table --data-file=-
```

### 3. Verifica secrets
```bash
gcloud secrets list
```

### 4. Permessi (se necessario)
```bash
# Dai permessi al service account di Cloud Run
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding openai-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Deploy con Secrets

```bash
gcloud run deploy vanda-chatbot \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 60s \
  --set-env-vars "ENV=production,LOG_LEVEL=INFO,SUPABASE_TABLE_NAME=documents,RAG_DEFAULT_MATCH_COUNT=3,RAG_DEFAULT_MATCH_THRESHOLD=0.60,LLM_DEFAULT_MODEL=gpt-4o-mini,LLM_DEFAULT_TEMPERATURE=0.5,LLM_MAX_TOKENS=500,LLM_STREAM_ENABLED=true" \
  --set-secrets "OPENAI_API_KEY=openai-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest"
```

---

## Deploy con Docker (Opzione 2)

### 1. Build immagine locale
```bash
docker build -t vanda-chatbot .
```

### 2. Test locale
```bash
docker run -p 8080:8080 --env-file .env vanda-chatbot
```

### 3. Push a Google Artifact Registry

#### Abilita API
```bash
gcloud services enable artifactregistry.googleapis.com
```

#### Crea repository
```bash
gcloud artifacts repositories create vanda \
  --repository-format=docker \
  --location=europe-west1 \
  --description="VANDA Chatbot Docker images"
```

#### Configura Docker
```bash
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

#### Tag e push
```bash
# Sostituisci PROJECT_ID
PROJECT_ID=$(gcloud config get-value project)

docker tag vanda-chatbot \
  europe-west1-docker.pkg.dev/${PROJECT_ID}/vanda/chatbot:latest

docker push europe-west1-docker.pkg.dev/${PROJECT_ID}/vanda/chatbot:latest
```

#### Deploy da Artifact Registry
```bash
gcloud run deploy vanda-chatbot \
  --image europe-west1-docker.pkg.dev/${PROJECT_ID}/vanda/chatbot:latest \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-secrets "OPENAI_API_KEY=openai-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest"
```

---

## Post-Deploy

### 1. Ottieni URL servizio
```bash
gcloud run services describe vanda-chatbot \
  --region europe-west1 \
  --format='value(status.url)'
```

Output esempio: `https://vanda-chatbot-xxxxx-ew.a.run.app`

### 2. Test health check
```bash
SERVICE_URL=$(gcloud run services describe vanda-chatbot --region europe-west1 --format='value(status.url)')

curl $SERVICE_URL/health
```

### 3. Test chat endpoint
```bash
curl -X POST $SERVICE_URL/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Ciao, parlami dei vostri servizi",
    "stream": false
  }'
```

---

## Configurazione Custom Domain (agentika.io)

### Opzione A: Cloud Run Domain Mapping

```bash
# Mappa dominio personalizzato
gcloud run domain-mappings create \
  --service vanda-chatbot \
  --domain vanda.agentika.io \
  --region europe-west1
```

Cloud Run ti darà i record DNS da configurare:
```
CNAME vanda.agentika.io → ghs.googlehosted.com
```

### Opzione B: Load Balancer + Backend

1. Crea Load Balancer HTTP(S)
2. Configura backend verso Cloud Run
3. Mappa path `/vanda-chatbot/*` → Cloud Run URL
4. Configura SSL certificate

---

## Monitoring & Logs

### Visualizza logs in tempo reale
```bash
gcloud run services logs tail vanda-chatbot --region europe-west1
```

### Visualizza logs su Google Cloud Console
```
https://console.cloud.google.com/logs/query
```

Filtra per:
```
resource.type="cloud_run_revision"
resource.labels.service_name="vanda-chatbot"
```

### Metrics
```
https://console.cloud.google.com/run/detail/europe-west1/vanda-chatbot/metrics
```

Monitora:
- Request count
- Request latency (p50, p95, p99)
- Error rate
- Instance count
- CPU/Memory usage

---

## Scaling & Performance

### Auto-scaling configurazione
```bash
gcloud run services update vanda-chatbot \
  --region europe-west1 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80
```

### Ottimizzazioni
- `--min-instances 1` → elimina cold start (costa di più)
- `--max-instances 10` → limita costi massimi
- `--concurrency 80` → max richieste per istanza
- `--cpu-boost` → boost CPU al startup (riduce cold start)

---

## Update Deploy

### Deploy nuova versione
```bash
# Deploy con traffic immediato al 100%
gcloud run deploy vanda-chatbot \
  --source . \
  --region europe-west1

# Deploy con traffic split (canary deployment)
gcloud run deploy vanda-chatbot \
  --source . \
  --region europe-west1 \
  --no-traffic  # Non inviare traffic alla nuova versione

# Gradualmente passa traffic
gcloud run services update-traffic vanda-chatbot \
  --region europe-west1 \
  --to-latest=50  # 50% traffic alla nuova versione

# Se tutto OK, porta al 100%
gcloud run services update-traffic vanda-chatbot \
  --region europe-west1 \
  --to-latest=100
```

---

## Rollback

### Visualizza revisioni
```bash
gcloud run revisions list --service vanda-chatbot --region europe-west1
```

### Rollback a revisione precedente
```bash
# Ottieni nome revisione (es: vanda-chatbot-00002-abc)
gcloud run services update-traffic vanda-chatbot \
  --region europe-west1 \
  --to-revisions vanda-chatbot-00002-abc=100
```

---

## Costi Stimati

### Cloud Run Pricing (eu-west1)
- **Richieste**: $0.40 per milione
- **CPU**: $0.00002400 per vCPU-secondo
- **Memory**: $0.0000025 per GiB-secondo
- **Networking**: $0.12 per GB egress

### Free Tier (sempre disponibile)
- 2 milioni richieste/mese
- 360,000 GiB-seconds
- 180,000 vCPU-seconds
- 1 GB networking egress

### Esempio: 10k richieste/mese
- Richieste: $0.004
- CPU (1 vCPU, 5s avg): ~$1.20
- Memory (1GiB, 5s avg): ~$1.25
- **Totale: ~$2.50/mese** 🎉

### Esempio: 100k richieste/mese
- Richieste: $0.04
- CPU: ~$12
- Memory: ~$12.50
- **Totale: ~$25/mese**

---

## Troubleshooting

### Errore: "Permission denied"
```bash
# Verifica permessi IAM
gcloud projects get-iam-policy $(gcloud config get-value project)

# Aggiungi ruolo Cloud Run Admin
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="user:tua-email@gmail.com" \
  --role="roles/run.admin"
```

### Errore: "Service not found"
```bash
# Lista servizi
gcloud run services list --region europe-west1

# Verifica region corretta
gcloud config set run/region europe-west1
```

### Cold start troppo lento
```bash
# Abilita min-instances
gcloud run services update vanda-chatbot \
  --region europe-west1 \
  --min-instances 1
```

### Timeout errors
```bash
# Aumenta timeout (max 60min per Cloud Run 2nd gen)
gcloud run services update vanda-chatbot \
  --region europe-west1 \
  --timeout 120s
```

---

## CI/CD Automation

### GitHub Actions example

Crea `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy vanda-chatbot \
            --source . \
            --platform managed \
            --region europe-west1 \
            --set-secrets "OPENAI_API_KEY=openai-key:latest,..."
```

---

## Checklist Finale

- [ ] Secrets configurati su Secret Manager
- [ ] App deployata su Cloud Run
- [ ] Health check funzionante (`/health`)
- [ ] Test chat endpoint (`/api/chat`)
- [ ] Logs visibili e senza errori
- [ ] Custom domain configurato (opzionale)
- [ ] Monitoring attivo
- [ ] Auto-scaling testato
- [ ] Costi monitorati

---

## Link Utili

- **Cloud Run Console**: https://console.cloud.google.com/run
- **Logs**: https://console.cloud.google.com/logs
- **Monitoring**: https://console.cloud.google.com/monitoring
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager
- **Billing**: https://console.cloud.google.com/billing

---

## Supporto

Per problemi o domande:
1. Controlla logs: `gcloud run services logs tail vanda-chatbot --region europe-west1`
2. Verifica secrets: `gcloud secrets list`
3. Test health check: `curl SERVICE_URL/health`

---

**🚀 Deploy completato! Il chatbot VANDA è live su Cloud Run!**
