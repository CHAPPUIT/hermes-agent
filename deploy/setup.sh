#!/usr/bin/env bash
# Deploy Hermes OKE on OVH server
# Usage: scp -r deploy/ ubuntu@79.137.54.148:~/hermes-oke/ && ssh ubuntu@79.137.54.148 "cd ~/hermes-oke && bash setup.sh"

set -euo pipefail

echo "=== Hermes OKE Deployment ==="

# Create data directory structure
mkdir -p data/{memories,sessions,skills,cron,logs,plugins,hooks}

# Copy plugin and skills if not already symlinked
if [ ! -d "plugins/maestro" ]; then
    echo "WARNING: plugins/maestro not found. Mount it via docker-compose volume."
fi

# Create config.yaml
cat > data/config.yaml << 'YAML'
# Hermes OKE Configuration
model:
  default: "gemma4:e4b"
  provider: custom
  base_url: "http://localhost:8888/v1"
  context_length: 131072

smart_model_routing:
  enabled: true
  cheap_model: "gemma4:e4b"

fallback_providers:
  - provider: custom
    model: "gemma4:e4b"
    base_url: "http://localhost:11434/v1"
  - provider: anthropic
    model: "claude-sonnet-4-20250514"

agent:
  max_turns: 90

compression:
  enabled: true
  threshold: 0.50
  target_ratio: 0.20

skills:
  external_dirs:
    - /opt/data/external-skills/oke

memory:
  memory_enabled: true
  user_profile_enabled: true

terminal:
  backend: local
  timeout: 180

display:
  show_cost: true

security:
  tirith_enabled: true

delegation:
  model: "gemma4:e4b"
  provider: custom
  max_iterations: 50
YAML

# Create SOUL.md
cat > data/SOUL.md << 'SOUL'
Tu es l'assistant comptable OKE, propulse par Hermes Agent.

## Role
Tu aides les experts-comptables, collaborateurs et clients avec :
- La comptabilite generale (ecritures, balance, bilan, compte de resultat)
- La paie (bulletins, DSN, cotisations, absences)
- Le fiscal (TVA, liasse fiscale, declarations)
- L'analyse financiere (SIG, ratios, comparatifs)

## Outils disponibles
Tu disposes de 18 tools OKE pour acceder aux donnees en temps reel.
Utilise-les systematiquement au lieu de deviner.

## Regles
- Langue : francais. Termes techniques comptables en francais.
- Toujours verifier avant de modifier (preview avant ecriture)
- Ne jamais afficher les NIR, IBAN ou donnees sensibles en clair
- Signaler les anomalies avec un niveau de gravite (critique/warning/info)
- Proposer une verification manuelle en cas de doute
- Les montants sont en EUR, arrondis au centime
SOUL

echo "=== Pulling Hermes image ==="
docker pull nousresearch/hermes-agent:latest

echo "=== Starting Hermes OKE ==="
docker compose up -d

echo "=== Waiting for startup ==="
sleep 10

echo "=== Health check ==="
curl -s http://localhost:8642/health || echo "API server not ready yet, check logs: docker logs hermes-oke"

echo ""
echo "=== Deployment complete ==="
echo "API Server: http://localhost:8642/v1 (Bearer token required)"
echo "Trust Proxy: http://localhost:8888 (already running)"
echo "Ollama: http://localhost:11434"
echo ""
echo "Logs: docker logs -f hermes-oke"
