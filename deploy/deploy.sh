#!/bin/bash
# Deploy or update bunq Nest on EC2
# Run from the repo root: bash deploy/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

echo "=== Pulling latest code ==="
git pull --ff-only 2>/dev/null || echo "Skipping git pull (not a git repo or no remote)"

COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file .env"

echo "=== Building and starting containers ==="
$COMPOSE up -d --build

echo ""
echo "=== Deployment complete ==="
echo "Frontend: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'YOUR_EC2_IP')"
echo ""
echo "Useful commands:"
echo "  $COMPOSE logs -f        # stream logs"
echo "  $COMPOSE restart        # restart"
echo "  $COMPOSE down           # stop"
