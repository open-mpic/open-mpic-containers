# Open MPIC on k8s

## Prerequisites

- `hey`
- `jq`
- `kustomize`
- `kubectl`

## Deploy Open MPIC

```bash
cd deployment-examples/kubernetes/open-mpic
kustomize build . | kubectl apply -f -
```

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
