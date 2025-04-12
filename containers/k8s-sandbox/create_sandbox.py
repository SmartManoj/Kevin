import sys
import subprocess
import copy
import os

from time import sleep

import yaml

BASE_DEPLOYMENT_PATH = os.path.join(os.path.dirname(__file__), "deployment.yaml")
BASE_SERVICE_PATH = os.path.join(os.path.dirname(__file__), "service.yaml")

def load_yaml(path):
    with open(path, "r") as f:
        return list(yaml.safe_load_all(f))

def customize_deployment(base, sandbox_name):
    sandbox_name = f"sandbox-{sandbox_name}"
    dep = copy.deepcopy(base[0])
    dep['metadata']['name'] = f"{sandbox_name}-deployment"
    dep['spec']['selector']['matchLabels']['app'] = sandbox_name
    dep['spec']['template']['metadata']['labels']['app'] = sandbox_name
    dep['spec']['template']['spec']['containers'][0]['name'] = sandbox_name
    return dep

def customize_service(base, sandbox_name):
    sandbox_name = f"sandbox-{sandbox_name}"
    svc = copy.deepcopy(base[0])
    svc['metadata']['name'] = f"{sandbox_name}-service"
    svc['spec']['selector']['app'] = sandbox_name
    return svc

def deploy_manifests(manifests):
    yaml_str = ""
    for manifest in manifests:
        yaml_str += yaml.dump(manifest)
        yaml_str += "---\n"
    proc = subprocess.Popen(
        ["kubectl", "apply", "-f", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = proc.communicate(yaml_str)
    print(out)
    if proc.returncode != 0:
        print(err, file=sys.stderr)
        sys.exit(proc.returncode)

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_sandbox.py <sandbox-name>")
        sys.exit(1)
    sandbox_name = sys.argv[1]
    base_dep = load_yaml(BASE_DEPLOYMENT_PATH)
    base_svc = load_yaml(BASE_SERVICE_PATH)
    dep = customize_deployment(base_dep, sandbox_name)
    svc = customize_service(base_svc, sandbox_name)
    deploy_manifests([dep, svc])
    cmd = "kubectl get service sandbox-%s-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}:{.spec.ports[0].port}'" % sandbox_name
    while True:
        ip = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        # without quotes
        ip = ip.replace("'", "")
        host = ip.split(":")[0]
        if host:
            print('host', host)
            break
        sleep(1)
    print(ip)

if __name__ == "__main__":
    main()