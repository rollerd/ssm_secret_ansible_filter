#!/usr/bin/python3

import boto3
import botocore
import sys
import argparse
from jinja2 import Template

# Map environment name to assumed role arn for that account. Expects that the environment is in the base of the ssm path eg /dev/some/ssm/secret
ROLE_MAP = {"dev": ["<arn for dev service account>","external_id"], "staging": ["<arn for staging service account>","external_id"], "prod": [None, None]}

class FilterModule(object):
    def filters(self):
      return {'get_ssm': fetch_ssm_secret}


def get_client(path, env):
    split_path = path.split("/")
    environment = split_path[1]
    assumed_role = ROLE_MAP[env][0]
    external_id = ROLE_MAP[env][1]

    sts_client = boto3.client('sts')
    if assumed_role:
        assumed_role_object=sts_client.assume_role(RoleArn=assumed_role, RoleSessionName="Assumed_{0}".format(environment), ExternalId=external_id)
        credentials=assumed_role_object['Credentials']
        client = boto3.client("ssm", aws_access_key_id=credentials['AccessKeyId'], aws_secret_access_key=credentials['SecretAccessKey'], aws_session_token=credentials['SessionToken'])
    else:
        client = boto3.client("ssm")


    return client


def fetch_ssm_secret(path, env):

    boto_client = get_client(path, env)

    try:
        response = boto_client.get_parameter(Name=path, WithDecryption=True)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "ParameterNotFound":
            print(f"Could not find SSM param at: {path}")
            sys.exit(1)
        else:
            print(e)
            sys.exit(1)

    param_value = response['Parameter']['Value']
    return param_value


def render_secrets(filename):
    try:
        template = Template(open(filename).read())
        rendered_template = template.render(ssm_path=fetch_ssm_secret)
        with open(filename, 'w') as f:
            f.write(rendered_template)
    except FileNotFoundError as f:
        print(f"\u001b[33mCould not find secret template file with name: '{filename}'\u001b[0m")


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Replace secrets')
    parser.add_argument('-f', dest="filename", required=True, help='The secrets filename to render')
    args = parser.parse_args()

    filename = args.filename

    render_secrets(filename)
