kubectl create secret generic shared-secrets --from-env-file=./secrets/shared.env --dry-run=client -o yaml | kubectl apply -f -
