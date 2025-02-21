#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import boto3
from botocore.exceptions import ClientError
import requests
import os
import sys
import io

# EC2 Metadata 
USER_DATA_URL = 'http://169.254.169.254/latest/user-data'
META_DATA_URL = 'http://169.254.169.254/latest/meta-data'
EC2_DATA_FILE = 'ec2InsDatafile'

# Metadata parameters
ec2_params = {
    'Instance ID': 'instance-id',
    'Reservation ID': 'reservation-id',
    'Public IP': 'public-ipv4',
    'Public Hostname': 'public-hostname',
    'Private IP': 'local-ipv4',
    'Security Groups': 'security-groups',
    'AMI ID': 'ami-id'
}

try:
    fh = io.open(EC2_DATA_FILE, 'w', encoding='utf-8')
except IOError:
    print("Error while opening file for writing")
    sys.exit(1)

# Collect metadata
for param, path in ec2_params.items():
    try:
        response = requests.get(META_DATA_URL + '/' + path, timeout=2)
        response.raise_for_status()
        data = u"{}: {}".format(param, response.text.strip())
    except requests.RequestException as e:
        print("Error retrieving {}: {}".format(param, e))
        data = u"{}: ERROR".format(param)

    try:
        fh.write(data + u'\n')
    except IOError:
        print("Error writing {} to file".format(param))

# Get OS information
def get_command_output(command):
    return os.popen(command).read().strip()

os_name = get_command_output("grep '^NAME=' /etc/os-release | cut -d'=' -f2")
os_version = get_command_output("grep '^VERSION=' /etc/os-release | cut -d'=' -f2")
os_users = get_command_output("grep -E 'bash|sh' /etc/passwd | awk -F: '{print $1}'")

# Write OS data to file
try:
    fh.write(u"OS NAME: {}\n".format(os_name))
    fh.write(u"OS VERSION: {}\n".format(os_version))
    fh.write(u"Login able users: {}\n".format(os_users))
except IOError:
    print("Error writing OS details to file")

fh.close()

# Upload to S3
S3_BUCKET_NAME = 'new-bucket-e05ab0e0'
s3_conn = boto3.client('s3')

try:
    response = requests.get(META_DATA_URL + '/instance-id', timeout=2)
    response.raise_for_status()
    instance_id = response.text.strip()
except requests.RequestException as e:
    print("Error retrieving instance ID: {}".format(e))
    instance_id = "unknown"

try:
    with io.open(EC2_DATA_FILE, 'r', encoding='utf-8') as fh:
        s3_conn.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='system_info_{}.txt'.format(instance_id),
            Body=fh.read()
        )
    print("File uploaded to S3 bucket {} as system_info_{}.txt".format(S3_BUCKET_NAME, instance_id))
except ClientError as e:
    print("S3 Upload Failed: {}".format(e))
