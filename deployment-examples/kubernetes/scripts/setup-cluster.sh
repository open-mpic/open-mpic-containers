#!/bin/sh

# check if the correct number of arguments is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 {create|destroy}"
    exit 1
fi

# get the action from the first argument
ACTION=$1

if [ "$ACTION" = "create" ]; then
    ./istio.sh $ACTION || exit 1
    ./grafana.sh $ACTION || exit 1
    ./prometheus.sh $ACTION || exit 1
    ./kiali.sh $ACTION || exit 1
elif [ "$ACTION" = "destroy" ]; then
    ./grafana.sh $ACTION || exit 1
    ./prometheus.sh $ACTION || exit 1
    ./kiali.sh $ACTION || exit 1
    ./istio.sh $ACTION || exit 1
else
    echo "Usage: $0 {create|destroy}"
    exit 1
fi

