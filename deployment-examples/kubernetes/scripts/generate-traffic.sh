#!/bin/bash

hey -n 500 -m POST -H "Content-Type: application/json" -d '{
  "check_type": "caa",
  "domain_or_ip_target": "example.com"
}' "http://localhost/mpic"

hey -n 500 -m POST -H "Content-Type: application/json" -d '{
  "check_type": "dcv",
  "domain_or_ip_target": "dns-01.integration-testing.open-mpic.org",
  "dcv_check_parameters": {
    "validation_method": "acme-dns-01",
    "key_authorization_hash": "7FwkJPsKf-TH54wu4eiIFA3nhzYaevsL7953ihy-tpo"
    }
}' "http://localhost/mpic"