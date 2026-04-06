#!/usr/bin/env bash
# Setup OKE profiles for multi-tenant Hermes Agent
# Usage: ./scripts/setup-oke-profiles.sh <cabinet-name> [company-id]

set -euo pipefail

CABINET="${1:?Usage: $0 <cabinet-name> [company-id]}"
COMPANY_ID="${2:-}"

echo "Creating Hermes profile: $CABINET"

# Create profile with full clone (skills, config, memory)
hermes profile create "$CABINET" --clone-all

# Set OKE-specific env vars in profile
PROFILE_ENV="$HOME/.hermes/profiles/$CABINET/.env"

if [ -n "$COMPANY_ID" ]; then
    echo "" >> "$PROFILE_ENV"
    echo "# OKE Configuration for $CABINET" >> "$PROFILE_ENV"
    echo "OKE_COMPANY_ID=$COMPANY_ID" >> "$PROFILE_ENV"
    echo "Company ID set: $COMPANY_ID"
fi

echo ""
echo "Profile '$CABINET' created."
echo ""
echo "Usage:"
echo "  hermes -p $CABINET                  # Start with this profile"
echo "  hermes -p $CABINET chat -q '...'    # One-shot query"
echo ""
echo "To configure:"
echo "  hermes profile show $CABINET        # View details"
echo "  Edit $PROFILE_ENV to add API keys"
echo ""
echo "Gateway (run on each profile):"
echo "  hermes -p $CABINET gateway setup    # Configure messaging"
