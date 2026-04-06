# Trust Proxy — Hermes Agent

Micro-service FastAPI qui s'intercale entre Hermes Agent et les providers LLM cloud.

## Fonctions

- **Security scanning** : detection d'injections de prompt (FR/EN) et de secrets dans les messages
- **PII anonymization** : anonymisation des donnees sensibles francaises (NIR, SIRET, IBAN, telephone, email) avant envoi au cloud, deanonymisation au retour
- **Proxy transparent** : compatible OpenAI et Anthropic API, supporte le streaming SSE

## Lancement

```bash
cd trust-proxy
pip install -r requirements.txt
uvicorn proxy:app --port 8888
```

## Configuration Hermes

Dans la config du modele Hermes, pointer le base_url vers le proxy :

```yaml
model:
  base_url: http://localhost:8888/v1
```

Le proxy redirige vers le vrai provider via :
- Headers custom : `X-Trust-Target-URL`, `X-Trust-Api-Key`
- Ou variables d'environnement : `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- Ou detection automatique du provider selon le modele demande

## Endpoints

| Route | Description |
|---|---|
| `POST /v1/chat/completions` | Proxy OpenAI-compatible |
| `POST /v1/messages` | Proxy Anthropic-compatible |
| `GET /health` | Health check |

## Port

`8888` (fixe, pas de conflit avec OKE 4200-4202, MORPHEUS, etc.)
