import json
import boto3

import cfnresponse

POLICY_ARNS = ['arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM']


def handler_create(event, context):
    name = event["ResourceProperties"].get("InstanceProfileName", None)
    iam = boto3.client('iam')
    try:
        if name is None:
            raise Exception("InstanceProfileName must be defined")

        try:
            if iam.get_instance_profile(InstanceProfileName=name):
                cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, "existing:{}".format(name))
                return
        except iam.exceptions.NoSuchEntityException:
            pass

        print("Role " + name + " does not exist. Creating")

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

        # Get the desired role
        iam.create_role(
            RoleName=name,
            Description='Role created from Lambda',
            AssumeRolePolicyDocument=json.dumps(my_access_control_policy))

        for policy in POLICY_ARNS:
            iam.attach_role_policy(RoleName=name, PolicyArn=policy)
        print("Role " + name + " created")

        # create the instance profile
        iam.create_instance_profile(InstanceProfileName=name)

        iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=name)
        print("Instance profile " + name + " created")
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, "created:{}".format(name))
    except Exception as e:
        print str(e)
        delete_all(iam, name)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, "created:{}".format(name))


def handler_update(event, context):
    cfnresponse.send(event, context, cfnresponse.FAILED, {}, event["PhysicalResourceId"])


def handler_delete(event, context):
    cf = boto3.client("cloudformation")
    stack = cf.describe_stacks(StackName=event["StackId"])["Stacks"][0]
    resource_id = event["PhysicalResourceId"]
    if resource_id.startswith("existing:") or stack["StackStatus"] == "DELETE_IN_PROGRESS":
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, event["PhysicalResourceId"])
        return
    _, name = event["PhysicalResourceId"].split(":")

    try:
        delete_all(boto3.client('iam'), name)
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, resource_id)
    except Exception as e:
        print str(e)
        delete_all(boto3.client('iam'), name)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, resource_id)


def delete_all(iam, name):
    clean_policies(iam, name)
    clean_instance_profile(iam, name)
    delete_instance_profile(iam, name)
    delete_role(iam, name)


def clean_policies(iam, name):
    try:
        attached = iam.list_attached_role_policies(RoleName=name)
        for policy in attached["AttachedPolicies"]:
            iam.detach_role_policy(RoleName=name, PolicyArn=policy["PolicyArn"])
    except Exception as e:
        print str(e)


def clean_instance_profile(iam, name):
    try:
        instance_profile = iam.get_instance_profile(InstanceProfileName=name)
        for role in instance_profile["InstanceProfile"].get("Roles", []):
            iam.remove_role_from_instance_profile(
                InstanceProfileName=name,
                RoleName=role["RoleName"]
            )
    except Exception as e:
        print str(e)


def delete_instance_profile(iam, name):
    try:
        iam.delete_instance_profile(InstanceProfileName=name)
    except Exception as e:
        print str(e)


def delete_role(iam, name):
    try:
        iam.delete_role(RoleName=name)
    except Exception as e:
        print str(e)


def handler(event, context):
    if event["RequestType"] == "Create":
        handler_create(event, context)
    elif event["RequestType"] == "Update":
        handler_update(event, context)
    else:
        handler_delete(event, context)
