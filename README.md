# k8s

Production configuration of the single-node k3s cluster (`d2c-combined-01`).

## Layout

| Path | Target on the node |
|---|---|
| `manifests/*.yaml` | `kubectl apply -f manifests/<file>.yaml` |
| `host/k3s/config.yaml` | `/etc/rancher/k3s/config.yaml` (restart k3s) |
| `host/k3s/manifests/*.yaml` | `/var/lib/rancher/k3s/server/manifests/` (k3s applies them) |
| `host/sysctl/*` | `/etc/sysctl.d/` |
| `host/systemd/*` | `/etc/systemd/system/` |
| `host/scripts/*` | `/root/` |

Secret values are never stored here. Manifests reference the in-cluster secrets (`shared-secrets` and others) by name.

## Notes

- StatefulSets in `manifests/data-services.yaml` use `updateStrategy: OnDelete`: delete the pod to roll out a change.
- The ipBlocks of the `api-external-integrations` and `api-telegram-egress` NetworkPolicies are rewritten every minute by the `d2c-steam-egress` and `d2c-telegram-egress` timers.
- The frontend image is deployed by the `d2c-frontend-update` timer from successful `master` builds.
- cert-manager v1.21.3 is installed from the upstream release manifest.
- Changing the kubelet CPU manager policy requires: no Guaranteed pods running, stop k3s, delete `/var/lib/kubelet/cpu_manager_state`, edit `host/k3s/config.yaml`, start k3s.

## Rollback

`git checkout <commit> -- manifests host`, then re-apply the changed files to the node.
