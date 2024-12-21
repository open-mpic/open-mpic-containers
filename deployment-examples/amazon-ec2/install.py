#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import json
import pprint
import yaml

import get_ips
import ssh_utils
import time


def parse_args(raw_args):
    parser = argparse.ArgumentParser()
    dirname = os.path.dirname(os.path.realpath(__file__))
    parser.add_argument("-c", "--config",
                        default=f"{dirname}/config.yaml")
    parser.add_argument("-a", "--aws_region_config",
                        default=f"{dirname}/aws_region_config.yaml")
    parser.add_argument("-k", "--api_key_file",
                        default=f"{dirname}/keys/api.key")
    parser.add_argument("-j", "--hash_secret_file",
                        default=f"{dirname}/keys/hash-secret.txt")
    parser.add_argument("-f", "--tf_state",
                        default=f"{dirname}/open-tofu/terraform.tfstate")
    parser.add_argument("-i", "--identity_file",
                        default=f"{dirname}/keys/aws.pem")
    parser.add_argument("-d", "--docker_compose_template_file",
                        default=f"{dirname}/compose.yaml.template")
    parser.add_argument("-n", "--nginx_template_file",
                        default=f"{dirname}/mpic-site.conf.template")
    parser.add_argument("-t", "--tmp_dir",
                        default=f"{dirname}/tmp")
    parser.add_argument("-x", "--dns_suffix_file",
                        default=f"{dirname}/dns-suffix.txt")
    return parser.parse_args(raw_args)




# Main function. Optional raw_args array for specifying command line arguments in calls from other python scripts. If raw_args=none, argparse will get the arguments from the command line.
def main(raw_args=None):
    args = parse_args(raw_args)

    dns_suffix = None
    with open(args.dns_suffix_file) as f:
        dns_suffix = f.read().strip()

    hash_secret = None
    with open(args.hash_secret_file) as f:
        hash_secret = f.read().strip()
    
    config = {}
    with open(args.config) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading YAML config at {args.config}. Project not configured. Error details: {exec}.")
            exit()

    aws_region_config = {}
    with open(args.aws_region_config) as stream:
        try:
            aws_region_config = yaml.safe_load(stream)['available_regions']
        except yaml.YAMLError as exc:
            print(f"Error loading YAML config at {args.aws_region_config}. Project not configured. Error details: {exec}.")
            exit()

    api_key = None
    with open(args.api_key_file) as f:
        api_key = f.read().strip()
    
    remotes = get_ips.extract_ips(args.tf_state, dns_suffix)

    ips = [ip for ip in remotes]
    ls_results = ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "ls")
    startup_script_complete = False
    while not startup_script_complete:
        all_nodes_startup_script_done = True
        for ls_result in ls_results.values():
            if "done.txt" not in ls_result:
                all_nodes_startup_script_done = False
                break
        if all_nodes_startup_script_done:
            startup_script_complete = True
            break
        print("Startup script not done... Sleeping 5 sec.")
        time.sleep(5)
    print("Startup scripts done. Home dir at remote nodes.")
    pprint.pp(ls_results)

    if not os.path.isdir(args.tmp_dir):
        os.mkdir(args.tmp_dir)


    # Install nginx
    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo apt install -y nginx")

    # Disable default site.
    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo rm /etc/nginx/sites-enabled/default")
    
    # Increase host hash bucket size to allow for long hostnames.
    #ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo sed -i '/server_names_hash_bucket_size/c\server_names_hash_bucket_size 128;' /etc/nginx/nginx.conf")
    
    
    


    with open(args.nginx_template_file) as stream:
        nginx_template_string = stream.read()
        for ip in remotes:
            nginx_template_string_region = nginx_template_string[:]
            nginx_template_string_region = nginx_template_string_region.replace("{{public-dns}}", remotes[ip]['dns'])
            nginx_template_string_region = nginx_template_string_region.replace("{{api-key}}", api_key)
            conf_file_path = args.tmp_dir + f"/mpic-site-{remotes[ip]['dns']}.conf"
            with open(conf_file_path, 'w') as conf_file:
                conf_file.write(nginx_template_string_region)
            ssh_utils.copy_file_to_remote(conf_file_path, "/home/ubuntu/mpic-site.conf", ip, args.identity_file)

    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo cp /home/ubuntu/mpic-site.conf /etc/nginx/sites-available/mpic-site.conf")
    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo ln -s /etc/nginx/sites-available/mpic-site.conf /etc/nginx/sites-enabled/mpic-site.conf")

    pprint.pp(ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo snap install --classic certbot"))

    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo ln -s /snap/bin/certbot /usr/bin/certbot")
    
    cmds = []
    for ip in ips:
        cmds.append(f"sudo certbot --nginx --non-interactive --agree-tos --register-unsafely-without-email -d {remotes[ip]['dns']}")
    
    pprint.pp(ssh_utils.run_cmds_at_remotes(ips, args.identity_file, cmds))


    with open(args.docker_compose_template_file) as stream:
        # Read the template file to a string.
        docker_compose_template = stream.read()

        perspectives = config['perspectives']

        dcv_endpoints = {}
        caa_endpoints = {}

        perspective_names = "|".join(perspectives)
        for perspective in perspectives:
            domains = [remotes[ip]['dns'] for ip in remotes if remotes[ip]['region'] == perspective]
            # FIXME don't use a list, use a single entry point which will do load balancing.
            dcv_endpoints[perspective] = [{"url": f"https://{domain}/dcv", "headers": {"x-api-key": api_key, "Content-Type": "application/json"}} for domain in domains]
            caa_endpoints[perspective] = [{"url": f"https://{domain}/caa", "headers": {"x-api-key": api_key, "Content-Type": "application/json"}} for domain in domains]
        
        dcv_endpoints_json = json.dumps(dcv_endpoints)
        caa_endpoints_json = json.dumps(caa_endpoints)
        print(dcv_endpoints_json)
        print(caa_endpoints_json)
        for ip in remotes:
            docker_compose_template_string_region = docker_compose_template[:]

            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{hash-secret}}", hash_secret)
            
            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{perspective-names}}", perspective_names)
            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{dcv-remotes-json}}", dcv_endpoints_json)
            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{caa-remotes-json}}", caa_endpoints_json)
            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{default-perspective-count}}", str(config['default-perspective-count']))

            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{enforce-distinct-rir-regions}}", "1" if config['enforce-distinct-rir-regions'] else "0")
            
            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{default-caa-domains}}", "|".join(config['caa-domains']))
            
            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{code}}", remotes[ip]['region'])
            
            rir = [region['rir'] for region in aws_region_config if region['code'] == remotes[ip]['region']][0]

            docker_compose_template_string_region = docker_compose_template_string_region.replace("{{rir}}", rir)
            
            # Replace absolout max attempt count if present.
            if "absolute-max-attempts" in config:
                docker_compose_template_string_region = docker_compose_template_string_region.replace("{{absoloute-max-attempts-key}}", f"absolute_max_attempts: \"{config['absolute-max-attempts']}\"")
            else:
                docker_compose_template_string_region = docker_compose_template_string_region.replace("{{absoloute-max-attempts-key}}", "")
            filename = args.tmp_dir + "/compose." + ip + ".yaml"
            with open(filename, 'w') as f:
                f.write(docker_compose_template_string_region)
            ssh_utils.copy_file_to_remote(filename, "/home/ubuntu/compose.yaml", ip, args.identity_file)
    ssh_utils.copy_file_to_remotes(ips, args.aws_region_config, "/home/ubuntu/available_perspectives.yaml", args.identity_file)

    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo docker compose down")
    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo docker compose up --build --force-recreate --no-deps -d")
    ssh_utils.run_cmd_at_remotes(ips, args.identity_file, "sudo service nginx reload")


# Invoke this script after provisioning via open-tofu to print the API's url.


# Main module init for direct invocation. 
if __name__ == '__main__':
    main()
