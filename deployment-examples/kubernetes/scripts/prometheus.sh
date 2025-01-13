#!/bin/sh

# This script will install or uninstall Prometheus on your Kubernetes cluster

usage() {
  echo "Usage: $0 {create|destroy}"
  exit 1
}

if [ $# -ne 1 ]; then
  usage
fi

case $1 in
  create)
    kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.24/samples/addons/prometheus.yaml
    echo "Prometheus installation initiated."
    ;;
  destroy)
    kubectl delete -f https://raw.githubusercontent.com/istio/istio/release-1.24/samples/addons/prometheus.yaml
    echo "Prometheus uninstallation initiated."
    ;;
  *)
    usage
    ;;
esac
