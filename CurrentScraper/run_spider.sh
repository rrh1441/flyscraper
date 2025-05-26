cat > run_spider.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
set -x

# Container paths, not local machine paths
ROOT=/app
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/cron.log"

mkdir -p "$LOG_DIR"
cd "$ROOT"

iso_now() { date -Is; }

echo "[$(iso_now)] 🚀 Spider starting on Fly.io..."
echo "  - PWD: $(pwd)"
echo "  - USER: ${USER:-unknown}"

# Check environment variables
if [[ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
    echo "  - SUPABASE_SERVICE_ROLE_KEY: [SET - ${#SUPABASE_SERVICE_ROLE_KEY} chars]"
else
    echo "  - ERROR: SUPABASE_SERVICE_ROLE_KEY not found!"
    exit 1
fi

# Test network connectivity
echo "[$(iso_now)] 🌐 Testing Supabase connectivity..."
if curl -s --max-time 10 -I https://mqoqdddzrwvonklsprgb.supabase.co | head -1; then
    echo "  - Supabase URL reachable ✅"
else
    echo "  - Supabase URL unreachable ❌"
    exit 1
fi

# No virtual env needed in container - packages are installed globally
echo "[$(iso_now)] 🐍 Python environment ready"

# Test Supabase connection
echo "[$(iso_now)] 🔑 Testing Supabase connection..."
python3 -c "
import os
from supabase import create_client
try:
    url = 'https://mqoqdddzrwvonklsprgb.supabase.co'
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    print(f'Using key: {key[:8]}...{key[-4:]} (length: {len(key)})')
    client = create_client(url, key)
    result = client.table('tennis_courts_fly').select('id').limit(1).execute()
    print(f'✅ Supabase connection successful - found {len(result.data)} records')
except Exception as e:
    print(f'❌ Supabase connection failed: {e}')
    print(f'Error type: {type(e).__name__}')
    import traceback
    traceback.print_exc()
    exit(1)
"

echo "[$(iso_now)] 🕷️ Starting Scrapy spider..."
exec scrapy crawl AncSpider --loglevel=INFO
EOF