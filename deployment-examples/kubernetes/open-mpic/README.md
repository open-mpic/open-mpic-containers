# Open MPIC on k8s

## Kubernetes Deployment with Istio

This guide provides instructions on setting up Open MPIC on Kubernetes using Kustomize
It deploys two imaginary regions for test purposes: `mordor-east-1` and `shire-west-1`.

Also included is a traffic generator to have some traffic to monitor with Kiali.

## Prerequisites

- `hey`
- `jq`

## Test commands

### CAA Checker

```bash
curl -H 'Content-Type: application/json'\
      -d '{
  "check_type": "caa",
  "domain_or_ip_target": "example.com"
}' \
      -X POST \
      "http://localhost/mpic" \
| jq .
```

```bash
hey -n 500 -m POST -H "Content-Type: application/json" -d '{
  "check_type": "caa",
  "domain_or_ip_target": "example.com"
}' "http://localhost/mpic"
```

### DCV Checker

```bash
curl -H 'Content-Type: application/json' \
-H 'scenario: jason' \
      -d '{
  "check_type": "dcv",
  "domain_or_ip_target": "dns-01.integration-testing.open-mpic.org",
  "dcv_check_parameters": {

  "validation_details": {
    "validation_method": "acme-dns-01",
    "key_authorization": "7FwkJPsKf-TH54wu4eiIFA3nhzYaevsL7953ihy-tpo"
    }
  }
}' \
      -X POST \
      "http://localhost/mpic" \
| jq .
```

```bash
hey -n 500 -m POST -H "Content-Type: application/json" -d '{
  "check_type": "dcv",
  "domain_or_ip_target": "dns-01.integration-testing.open-mpic.org",
  "dcv_check_parameters": {

  "validation_details": {
    "validation_method": "acme-dns-01",
    "key_authorization": "7FwkJPsKf-TH54wu4eiIFA3nhzYaevsL7953ihy-tpo"
    }
  }
}' "http://localhost/mpic"
```
