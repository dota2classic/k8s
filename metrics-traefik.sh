apiVersion: v1
kind: Service
metadata:
  name: traefik-metrics
  namespace: kube-system
spec:
  selector:
    app.kubernetes.io/instance: traefik-kube-system
    app.kubernetes.io/name: traefik
  ports:
    - name: metrics
      port: 9100
      targetPort: 9100
