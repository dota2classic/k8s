touch /etc/rancher/k3s/podnodeselector.yaml

echo 'podNodeSelectorPluginConfig:
        clusterDefaultNodeSelector: "node-type!=gameserver"
        gameservers: "node-type=gameserver"' > /etc/rancher/k3s/podnodeselector.yaml

touch /etc/rancher/k3s/config.yaml
echo "kube-apiserver-arg:
        - enable-admission-plugins=PodNodeSelector
        - admission-control-config-file=/etc/rancher/k3s/podnodeselector.yaml" > /etc/rancher/k3s/config.yaml
