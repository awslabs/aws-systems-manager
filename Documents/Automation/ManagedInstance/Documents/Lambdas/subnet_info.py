import boto3
import traceback

import cfnresponse


def handler_subnet_info(event, context):
    try:
        ec2 = boto3.client('ec2')
        vpc_id = event["ResourceProperties"].get("VpcId", "")
        subnet_id = event["ResourceProperties"].get("SubnetId", "")

        data = {}

        if len(subnet_id) == 0 or subnet_id == "Default":
            subnet_id = ""
            for subnet in ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]).get('Subnets'):
                if subnet.get('DefaultForAz', False) and subnet['VpcId'] == vpc_id:
                    subnet_id = subnet['SubnetId']
                    break
            if len(subnet_id) == 0:
                raise Exception("Unable to find default subnet for vpc")
        data["SubnetId"] = subnet_id

        cfnresponse.send(event, context, cfnresponse.SUCCESS, data, event.get("PhysicalResourceId", None))
    except Exception as e:
        print str(e)
        traceback.print_exc()
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, event.get("PhysicalResourceId", None))


def handler_delete(event, context):
    # Nothing to do... this is a informational lambda and no resource is created.
    cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, event["PhysicalResourceId"])


def handler(event, context):
    if event["RequestType"] in ["Create", "Update"]:
        handler_subnet_info(event, context)
    elif event["RequestType"] in ["Delete"]:
        handler_delete(event, context)
