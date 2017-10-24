"Lambda handler"
from __future__ import print_function

import json
import boto3
from botocore.exceptions import ClientError

print('Loading function')

def lambda_handler(event, context):
    "Lambda handler"
    print("Received event: " + json.dumps(event, indent=2))

    groupname = event['groupname']
    platform = event['platform']

    # get EC2 client
    ec2 = boto3.client('ec2')

    response = ec2.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    try:
        response = ec2.create_security_group(GroupName=groupname,
                                             Description='Security Group created from Lambda',
                                             VpcId=vpc_id)
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

        if platform.lower() == 'windows':
            data = ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 3389,
                     'ToPort': 3389,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ])
            print('Ingress Successfully Set %s' % data)
        else:
            data = ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 22,
                     'ToPort': 22,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ])
            print('Ingress Successfully Set %s' % data)
    except ClientError as ex:
        print(ex)
