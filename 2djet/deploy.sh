#!/bin/bash
# Deploy the N2 jet page onto themithrilcompany.com.
#
# URL:
#   https://themithrilcompany.com/N2jet.html
set -euo pipefail

SERVER="${SERVER:-root@143.110.131.237}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
DEPLOY_PATH="/var/www/N2jet"
NGINX_SITE="/etc/nginx/sites-enabled/themithrilcompany.com"
ROOT="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -i "$SSH_KEY" -o BatchMode=yes "$SERVER")
RSYNC_SSH="ssh -i $SSH_KEY -o BatchMode=yes"

echo "═══════════════════════════════════════════"
echo " N2 jet → $SERVER:$DEPLOY_PATH"
echo "═══════════════════════════════════════════"

"${SSH[@]}" "mkdir -p '$DEPLOY_PATH'"

rsync -avz \
  --exclude='.git' \
  --exclude='deploy.sh' \
  --exclude='deploy/' \
  --exclude='.DS_Store' \
  -e "$RSYNC_SSH" \
  "$ROOT/N2jet.html" \
  "$SERVER:$DEPLOY_PATH/"

SNIPPET_LOCAL="$ROOT/deploy/nginx-n2jet.snippet"
if [ ! -f "$SNIPPET_LOCAL" ]; then
  echo "ERROR: missing $SNIPPET_LOCAL" >&2
  exit 1
fi

echo "Updating nginx locations in $NGINX_SITE …"
scp -i "$SSH_KEY" -o BatchMode=yes "$SNIPPET_LOCAL" "$SERVER:/tmp/nginx-n2jet.snippet"

"${SSH[@]}" bash -s <<'ENDSSH'
set -euo pipefail
SITE=/etc/nginx/sites-enabled/themithrilcompany.com
SNIP=/tmp/nginx-n2jet.snippet
mkdir -p /etc/nginx/bak
cp -a "$SITE" "/etc/nginx/bak/themithrilcompany.com.bak.n2jet.$(date +%Y%m%d%H%M%S)"

python3 - <<'PY'
from pathlib import Path
import re

site = Path("/etc/nginx/sites-enabled/themithrilcompany.com")
snip = Path("/tmp/nginx-n2jet.snippet").read_text()
text = site.read_text()

text2 = re.sub(
    r"\n?# BEGIN N2jet.*?# END N2jet\n?",
    "\n",
    text,
    flags=re.S,
)

marker = "    location / {"
idx = text2.find(marker)
if idx == -1:
    marker = "    listen 443 ssl"
    idx = text2.find(marker)
if idx == -1:
    raise SystemExit("Could not find insertion point in nginx site config")

block = "\n" + snip.rstrip() + "\n\n"
text2 = text2[:idx] + block + text2[idx:]
site.write_text(text2)
print("Nginx site updated with N2jet locations")
PY

nginx -t
systemctl reload nginx
echo "nginx reloaded OK"
ENDSSH

echo ""
echo "Deployed."
echo "  https://themithrilcompany.com/N2jet.html"
