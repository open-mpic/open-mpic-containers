#!/bin/bash

# This script will install, or uninstall Kiali on your Kubernetes cluster

function usage() {
  echo "Usage: $0 {create|destroy}"
  exit 1
}

if [ $# -ne 1 ]; then
  usage
fi

case $1 in
  create)
    helm install \
      --namespace istio-system \
      --set auth.strategy="anonymous" \
      --set external_services.grafana.url="http://grafana.istio-system:3000" \
      --repo https://kiali.org/helm-charts \
      kiali-server \
      kiali-server
    echo "Kiali installation initiated."
    ;;
  destroy)
    helm uninstall --namespace istio-system kiali-server
    echo "Kiali uninstallation initiated."
    ;;
  *)
    usage
    ;;
esac