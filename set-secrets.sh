#!/bin/bash
# Set all GitHub secrets for daily-reader in one go.
# Run from anywhere: bash set-secrets.sh

REPO="ranjit323/daily-reader"

echo ""
echo "Daily Reader — GitHub Secrets Setup"
echo "────────────────────────────────────"
echo "Values are hidden as you type. Press Enter after each one."
echo "Leave blank and press Enter to skip any optional secret."
echo ""

prompt_secret() {
  local name="$1"
  local label="$2"
  local required="$3"

  while true; do
    read -r -p "$label: " value
    if [ -z "$value" ]; then
      if [ "$required" = "required" ]; then
        echo "  ✗ Required — please enter a value"
      else
        echo "  — skipped"
        return
      fi
    else
      gh secret set "$name" --repo "$REPO" --body "$value"
      echo "  ✓ $name saved"
      return
    fi
  done
}

echo "── Required ──────────────────────────"
prompt_secret "FT_EMAIL"           "FT account email"         required
prompt_secret "FT_PASSWORD"        "FT password"              required
prompt_secret "GMAIL_ADDRESS"      "Gmail address"            required
prompt_secret "GMAIL_APP_PASSWORD" "Gmail App Password"       required

echo ""
echo "── Optional (full article bodies) ───"
echo "If you have subscriptions, enter credentials for full text."
echo ""
prompt_secret "ECONOMIST_EMAIL"    "Economist email"          optional
prompt_secret "ECONOMIST_PASSWORD" "Economist password"       optional
prompt_secret "LRB_EMAIL"          "LRB email"                optional
prompt_secret "LRB_PASSWORD"       "LRB password"             optional
prompt_secret "NLR_EMAIL"          "NLR email"                optional
prompt_secret "NLR_PASSWORD"       "NLR password"             optional

echo ""
echo "────────────────────────────────────"
echo "Done. Trigger a run at:"
echo "https://github.com/$REPO/actions/workflows/morning.yml"
echo ""
