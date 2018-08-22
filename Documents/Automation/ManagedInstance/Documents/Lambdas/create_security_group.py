import boto3
import traceback
import cfnresponse


def find_security_groups(ec2, vpc_id, group_name):
    security_groups = ec2.describe_security_groups(Filters=[
        {"Name": "group-name", "Values": [group_name]},
        {"Name": "vpc-id", "Values": [vpc_id]}
    ])["SecurityGroups"]
    for security_group in security_groups:
        if security_group["GroupName"] == group_name and security_group["VpcId"] == vpc_id:
            return security_group
    return None


def handler_create(event, context):
    group_name = event["ResourceProperties"].get("GroupName", None)
    cidr = event["ResourceProperties"].get("AccessCidr", "")
    vpc_id = event["ResourceProperties"].get("VpcId", None)
    platform = event["ResourceProperties"].get("Platform", None)

    ec2 = boto3.client('ec2')
    security_group_id = None
    try:
        security_group = find_security_groups(ec2, vpc_id, group_name)
        if security_group is not None:
            data = {"SecurityGroupId": security_group["GroupId"]}
            cfnresponse.send(event, context, cfnresponse.SUCCESS, data, "existing:{}:{}".format(vpc_id, group_name))
            return

        response = ec2.create_security_group(
            GroupName=group_name,
            Description='Security Group created from Lambda',
            VpcId=vpc_id)
        security_group_id = response['GroupId']

        if len(cidr) > 0:
            if platform == 'windows':
                data = ec2.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=[
                        {'IpProtocol': 'tcp',
                         'FromPort': 3389,
                         'ToPort': 3389,
                         'IpRanges': [{'CidrIp': cidr}]}
                    ])
                print('Ingress Successfully Set %s' % data)
            else:
                data = ec2.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=[
                        {'IpProtocol': 'tcp',
                         'FromPort': 22,
                         'ToPort': 22,
                         'IpRanges': [{'CidrIp': cidr}]}
                    ])
                print('Ingress Successfully Set %s' % data)

        data = {"SecurityGroupId": security_group_id}
        cfnresponse.send(event, context, cfnresponse.SUCCESS, data, "created:{}:{}".format(vpc_id, security_group_id))
    except Exception as e:
        print str(e)
        traceback.print_exc()
        delete_all(ec2, vpc_id, security_group_id)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, "created:{}:{}".format(vpc_id, security_group_id))


def handler_update(event, context):
    cfnresponse.send(event, context, cfnresponse.FAILED, {}, event["PhysicalResourceId"])


def handler_delete(event, context):
    cf = boto3.client("cloudformation")
    stack = cf.describe_stacks(StackName=event["StackId"])["Stacks"][0]
    resource_id = event["PhysicalResourceId"]
    if resource_id.startswith("existing:") or stack["StackStatus"] == "DELETE_IN_PROGRESS":
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, event["PhysicalResourceId"])
        return
    _, vpc_id, group_id = event["PhysicalResourceId"].split(":")

    try:
        delete_all(boto3.client('ec2'), vpc_id, group_id)

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, resource_id)
    except Exception as e:
        print str(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, resource_id)


def delete_all(ec2, vpc_id, group_id):
    if group_id is not None:
        try:
            ec2.delete_security_group(GroupId=group_id)
        except Exception as e:
            str(e)


def handler(event, context):
    if event["RequestType"] == "Create":
        handler_create(event, context)
    elif event["RequestType"] == "Update":
        handler_update(event, context)
    else:
        handler_delete(event, context)
