#!/bin/bash

usage() {
  echo "Usage: $0 {create|destroy}"
  exit 1
}

if [ $# -ne 1 ]; then
  usage
fi

# Check if istioctl is installed
if ! command -v istioctl &> /dev/null
then
    echo "istioctl could not be found, please install it first."
    exit
fi

case $1 in
  create)
    # Install Istio with the demo profile
    istioctl install --set profile=demo --set values.sidecarInjectorWebhook.enableNamespacesByDefault=true -y
    echo "Istio installation with demo profile is complete."
    ;;
  destroy)
    # Uninstall Istio
    istioctl uninstall --purge -y
    kubectl delete namespace istio-system
    echo "Istio has been uninstalled."
    ;;
  *)
    usage
    ;;
esac