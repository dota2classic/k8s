#!/bin/bash
set -e

ENV_FILE=${1:-.env.dev}

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file $ENV_FILE not found!"
  exit 1
fi

# Export environment variables from file
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Find all .yaml files recursively under k8s/
find k8s -type f -name '*.yaml' | while read -r file; do
  echo "Applying $file..."
  envsubst < "$file" | kubectl apply -f -
done

echo "✅ Deployment finished for $DOMAIN"
