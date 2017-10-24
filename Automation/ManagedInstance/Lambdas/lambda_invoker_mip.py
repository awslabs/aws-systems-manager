"Lambda handler"
from __future__ import print_function

import json
import boto3

print('Loading function')

POLICY_ARNS = ['arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM']

def lambda_handler(event, context):
    "Lambda handler"
    print("Received event: " + json.dumps(event, indent=2))

    rolename = event['rolename']
    # get SSM client
    iam = boto3.client('iam')

    try:
        response = iam.get_role(
            RoleName=rolename
        )

        if response :
            print("Role " + rolename + " exists. Quitting")
            return
    except:
        print("Role " + rolename + " does not exist. Creating")

    my_access_control_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "ssm.amazonaws.com",
                        "ec2.amazonaws.com"
                    ]
                    },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        # Get the desired role
        response = iam.create_role(
            RoleName=rolename,
            Description='Role created from Lambda',
            AssumeRolePolicyDocument=json.dumps(my_access_control_policy)
            )

        if response:
            for policy in POLICY_ARNS:
                iam.attach_role_policy(
                    RoleName=rolename,
                    PolicyArn=policy
                )
        print("Role " + rolename + " created")
    except:
        print("Error in creating role " + rolename)
        return

    try:
        # create the instance profile
        response = iam.create_instance_profile(
            InstanceProfileName=rolename
        )

        if response:
            iam.add_role_to_instance_profile(
                InstanceProfileName=rolename,
                RoleName=rolename
            )
            print("Instance profile " + rolename + " created")
    except:
        print("Error in creating instance profile " + rolename)