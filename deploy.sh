#!/bin/bash
set -e

ENV_FILE=${1:-.env.dev}
TARGET_FILE=${2:-}

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file $ENV_FILE not found!"
  exit 1
fi

# Export environment variables from file
export $(grep -v '^#' "$ENV_FILE" | xargs)

if [ -n "$TARGET_FILE" ]; then
  # Apply only the specified file
  if [ ! -f "$TARGET_FILE" ]; then
    echo "Target file $TARGET_FILE not found!"
    exit 1
  fi
  echo "Applying $TARGET_FILE..."
  envsubst < "$TARGET_FILE" | kubectl apply -f -
else
  # Find all .yaml files recursively under k8s/
  find k8s -type f -name '*.yaml' | while read -r file; do
    echo "Applying $file..."
    envsubst < "$file" | kubectl apply -f -
  done
fi

echo "✅ Deployment finished for $DOMAIN"
