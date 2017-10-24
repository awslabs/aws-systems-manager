#!/usr/bin/env python
"Create the required roles for running lambda"

import sys
import json
import boto3

POLICY_ARNS = ['arn:aws:iam::aws:policy/AWSLambdaExecute',
               'arn:aws:iam::aws:policy/AmazonSSMFullAccess',
               'arn:aws:iam::aws:policy/IAMFullAccess',
               'arn:aws:iam::aws:policy/AmazonEC2FullAccess']

def usage():
    "Prints the usage of this script"
    print(
        '{0} <role name>'
        .format(sys.argv[0])
    )
    sys.exit(2)

def test_role(rolename):
    "test if required role exists"
    # Create IAM client
    iam = boto3.client('iam')

    try:
        # Get the desired role
        response = iam.get_role(
            RoleName=rolename
            )
        if response <> None:
            return True
    except:
        return False

def create_role(rolename):
    "Create the role if it doesn't exist"

    if test_role(rolename):
        print("Role " + rolename + " already exists. Skipping")
        return

    # Create IAM client
    iam = boto3.client('iam')

    try:
        # access control policy document

        my_access_control_policy = {
            "Version": "2012-10-17",
            "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                    },
                        "Action": "sts:AssumeRole"
                    }
                ]
        }
        # Get the desired role
        response = iam.create_role(
            RoleName=rolename,
            Description='Role created for accessing AWS resources from Lambda functions',
            AssumeRolePolicyDocument=json.dumps(my_access_control_policy)
            )

        if response:
            for policy in POLICY_ARNS:
                iam.attach_role_policy(
                    RoleName=rolename,
                    PolicyArn=policy
                )

            print "Role " + rolename + " created"
    except:
        print "Error in creating in role" + rolename


if len(sys.argv) < 2:
    usage()

create_role(sys.argv[1])
