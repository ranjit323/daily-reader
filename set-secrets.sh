#!/bin/bash
# Set GitHub secrets for daily-reader.
# Leave any prompt blank to keep the existing value.

REPO="ranjit323/daily-reader"

echo ""
echo "Daily Reader — GitHub Secrets Setup"
echo "────────────────────────────────────"
echo "Press Enter to keep an existing secret unchanged."
echo ""

prompt_secret() {
  local name="$1"
  local label="$2"

  read -r -p "$label: " value
  if [ -z "$value" ]; then
    echo "  — unchanged"
  else
    gh secret set "$name" --repo "$REPO" --body "$value"
    echo "  ✓ $name saved"
  fi
}

prompt_secret "FT_EMAIL"           "FT email"
prompt_secret "FT_PASSWORD"        "FT password"
prompt_secret "GMAIL_ADDRESS"      "Gmail address"
prompt_secret "GMAIL_APP_PASSWORD" "Gmail App Password"
prompt_secret "ECONOMIST_EMAIL"    "Economist email"
prompt_secret "ECONOMIST_PASSWORD" "Economist password"
prompt_secret "LRB_EMAIL"          "LRB email"
prompt_secret "LRB_PASSWORD"       "LRB password"
prompt_secret "NLR_EMAIL"          "NLR email"
prompt_secret "NLR_PASSWORD"       "NLR password"

echo ""
echo "────────────────────────────────────"
echo "Done. Trigger a run at:"
echo "https://github.com/$REPO/actions/workflows/morning.yml"
echo ""
