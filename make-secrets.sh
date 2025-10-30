kubectl create secret generic shared-secrets --from-env-file=./secrets/shared.env --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic --namespace gameservers shared-gameserver-secrets --from-env-file=./secrets/gameserver.env --dry-run=client -o yaml | kubectl apply -f -
