#!/bin/bash
set -e

ENV_FILE=${1:-.env.dev}

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file $ENV_FILE not found!"
  exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

for file in k8s/*.yaml; do
  echo "Applying $(basename $file)..."
  envsubst < "$file" | kubectl apply -f -
done

echo "✅ Deployment finished for $DOMAIN"
