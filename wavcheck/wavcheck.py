import os
import sys
import json
import time
import base64
import argparse
from pprint import pprint
from collections import namedtuple
from string import Template

from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException


DATADIR = '/home/toolkit/ToolKit/data/wavcheck'


FIELD_MANAGER = 'field_manager'
NAMESPACE = 'dataproc'
LOG_INTERVAL = 2

Secret = namedtuple('Secret', ['username', 'password'])
normpath = lambda x: x.replace('\\', '/')

FILTERS = ['noise', 'clip', 'snr', 'energylost', 'am_detect', 'disturb_detect']


def init_api_client():
    kube_config_path = os.environ.get('KUBE_CONFIG')
    if not kube_config_path:
        print("Unable to find env var: KUBE_CONFIG")
        sys.exit(1)

    if not os.path.exists(kube_config_path):
        print("Unable to find kube config: %s" % kube_config_path)
        sys.exit(1)

    config.load_kube_config(kube_config_path)
    # Configure API key authorization: BearerToken
    configuration = client.Configuration()
    # configuration.api_key['authorization'] = 'YOUR_API_KEY'
    # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
    # configuration.api_key_prefix['authorization'] = 'Bearer'
    return client.ApiClient(configuration)


def get_mountinpath(inputpath, username):
    if inputpath != 'online':
        mountinpath = {
            "name": "source-data-storage",
            "flexVolume": {
              "driver": "fstab/cifs",
              "fsType": "cifs",
              "secretRef": {
                "name": "%s-cifs-secret" % username
              },
              "options": {
                "networkPath": "%s" % inputpath,
                "mountOptions": ""
              }
            }
          }
    else:
        mountinpath = {
            "name": "source-data-storage",
            "cephfs": {
                "monitors": [
                    "10.10.9.204:6789",
                    "10.10.9.205:6789",
                    "10.10.9.206:6789"
                ],
                "secretRef": {
                    "name": "cephfs-secret"
                },
                "user": "k8sfs",
                "path": "/k8sfs/satellite",
                "readOnly": True
            }
        }
    return mountinpath


def combine(args):
    # 参数拼接
    filter_args = []
    for filter in FILTERS:
        if getattr(args, filter):
            if getattr(args, 'args_'+filter):
                filter_args.append('-'.join([filter, getattr(args, 'args_'+filter)]))
            else:
                filter_args.append(filter)
    return '@'.join(filter_args)

def get_secret(secret):
    try:
        username, password = secret.split(':')
    except ValueError as e:
        print("secret not provided as required: %s" % secret)
        sys.exit(1)
    return Secret(username, password)

def get_groups(fileobj):
    groups = []
    for line in fileobj.readlines():
        task_id, group = line.split(',')
        groups.append((task_id.strip(), group.strip()))
    return json.dumps(groups)

def get_context(args):
    mounted_in_path = normpath(args.input)
    mounted_out_path = normpath(args.result)
    secret = get_secret(args.secret)
    mount_in_info = get_mountinpath(mounted_in_path, secret.username)
    detect_type = combine(args)
    groupsinfo = get_groups(args.groupsinfo) if args.groupsinfo else ''


    encrypt = lambda x: base64.b64encode(x.encode()).decode()
    context = {
        "group": encrypt(groupsinfo),
        "jobName": args.name,
        "mountinpath": mount_in_info,
        "resultPath": mounted_out_path,
        "cifsSecretRef":  "%s-cifs-secret" % secret.username,
        "username": encrypt(secret.username),
        "password": encrypt(secret.password),
        "args": detect_type,
        "image": 'registry.cn-beijing.aliyuncs.com/shujutang/audiofilters:v0.2'
    }
    return context

#################
# CREATE SECRET #
#################
def get_or_create_secret(api_client, name, namespace, manifest):
    api = client.apis.core_v1_api.CoreV1Api(api_client)
    resp = None
    try:
        resp = api.read_namespaced_secret(name=name, namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            exit(1)

    if not resp:
        print("Secret %s does not exist. Creating it..." % name)
        try:
            api_response = api.create_namespaced_secret(namespace, manifest, pretty='true')
        except ApiException as e:
            print("Exception when calling CoreV1Api->create_namespaced_secret: %s\n" % e)
            sys.exit(1)
        else:
            pprint(api_response)
            print("Secret created successfully.")


###############
# CREATE JOB #
##############
def get_or_create_job(api_client, name, namespace, manifest):
    batch_api = client.apis.BatchV1Api(api_client)
    resp = None
    try:
        resp = batch_api.read_namespaced_job(name=name, namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            sys.exit(1)

    if resp:
        print("Job %s is already existed." % name)

    else:
        print("Job %s does not exist. Creating it..." % name)
        try:
            api_response = batch_api.create_namespaced_job(namespace, manifest, pretty='true', field_manager=FIELD_MANAGER)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling BatchV1Api->create_namespaced_job: %s\n" % e)


    core_api = client.apis.core_v1_api.CoreV1Api(api_client)
    # redirects logs into local machine
    label_selector = 'job-name = %s' % name
    pods = core_api.list_namespaced_pod(namespace, label_selector=label_selector, watch=False)
    if pods.items and len(pods.items) == 1:
        pod_name = pods.items[0].metadata.name
        print("Try to connect to pod: %s" % pod_name)
    else:
        print("Unable to find proper pod with label selector: %s" % label_selector)
        sys.exit(1)

    while True:
        pod = core_api.read_namespaced_pod(pod_name, namespace)
        if pod.status.phase != 'Pending':
            break
        time.sleep(0.5)

    # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
    if pod.status.phase == 'Running':
        print("Job created successfully.")

        while pod.status.phase == 'Running':
            log = core_api.read_namespaced_pod_log(pod_name, namespace, pretty=True, since_seconds=LOG_INTERVAL)
            print(log)
            # update pod status
            pod = core_api.read_namespaced_pod(pod_name, namespace)
            time.sleep(LOG_INTERVAL)


        all_log = core_api.read_namespaced_pod_log(pod_name, namespace, pretty=True)
        with open(name+".log", "w") as f:
            f.write(all_log)


def get_manifest(filepath, context):
    with open(filepath) as f:
        data = f.read()
        manifest = json.loads(Template(data).substitute(context))
    return manifest


def update_mountpath(manifest, context):
    manifest["spec"]["template"]["spec"]["volumes"].append(context["mountinpath"])
    return manifest


def run(args):
    context = get_context(args)
    api_client = init_api_client()
    secret_manifest = get_manifest(os.path.join(DATADIR, 'secret_spec.json'), context)
    get_or_create_secret(api_client, context['cifsSecretRef'], NAMESPACE, secret_manifest)
    job_manifest = get_manifest(os.path.join(DATADIR, 'job_spec_wavcheck.json'), context)
    job_manifest = update_mountpath(job_manifest, context)
    print(job_manifest)
    get_or_create_job(api_client, context['jobName'], NAMESPACE, job_manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Launches a task on kuberbetes.")

    parser.add_argument('--name', type=str, required=True, help="Job名称，只能包含英文、数字、下划线、中划线")
    parser.add_argument('--input', type=str, required=True, help='数据源路径, 线上输入 online,线下数据ftp路径,如：//10.10.8.123/500小时中英混读语音采集标注',
                        default=None)
    parser.add_argument('--result', type=str, required=True, help='结果数据路径, ftp路径,使用“//10.10.8.123/500小时中英混读语音采集标注”这样格式',
                        default=None)
    parser.add_argument('--secret', type=str, required=True, help='ftp账户密码, 使用name:password格式,如xiaoming:zaixian2016',
                        default=None)

    parser.add_argument('--groupsinfo', type=argparse.FileType('r'), help='组号文件,excel文件第一列为任务id,第二列为组号')
    parser.add_argument('--noise', action='store_true', help='噪音检测器')
    parser.add_argument('--args_noise', type=str, help='噪音检测参数')
    parser.add_argument('--energylost', action='store_true', help='能量缺失检测器')
    parser.add_argument('--args_energylost', type=str, help='能量丢失检测器')
    parser.add_argument('--clip', action='store_true', help='截幅检测器')
    parser.add_argument('--args_clip', type=str, help='截幅检测器')
    parser.add_argument('--snr', action='store_true', help='信噪比检测器')
    parser.add_argument('--args_snr', type=str, help='信噪比检测器')
    parser.add_argument('--disturb_detect', action='store_true', help='干扰音检测器')
    parser.add_argument('--args_disturb_detect', type=str, help='干扰音检测器')
    # parser.add_argument('--emptyenergy', action='store_true', help='空能量检测器')
    # parser.add_argument('--args_emptyenergy', type=str, help='空能量检测器')
    parser.add_argument('--am_detect', action='store_true', help='振幅检测器')
    parser.add_argument('--args_am_detect', type=str, help='振幅检测器')

    args = parser.parse_args()
    run(args)

