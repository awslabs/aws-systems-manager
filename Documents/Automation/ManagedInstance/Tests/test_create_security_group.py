import os
import sys
import logging
import unittest

import ConfigParser
import boto3
import json
import mock

DOC_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPOROOT = os.path.dirname(DOC_DIR)

# Import shared testing code
sys.path.append(
    os.path.join(
        REPOROOT,
        'Testing'
    )
)
sys.path.append(os.path.join(
    DOC_DIR, "Documents/Lambdas"
))
sys.path.append(
    os.path.abspath(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "lib/"
    ))

)
import create_security_group
import ssm_testing  # noqa pylint: disable=import-error,wrong-import-position
import managedinstanceutil as util

CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(REPOROOT, 'Testing', 'defaults.cfg')))
CONFIG.read([os.path.join(REPOROOT, 'Testing', 'local.cfg')])

REGION = CONFIG.get('general', 'region')
PREFIX = CONFIG.get('general', 'resource_prefix')
SERVICE_ROLE_NAME = CONFIG.get('general', 'automation_service_role_name')

WINDOWS_AMI_ID = CONFIG.get('windows', 'windows2016.{}'.format(REGION))
LINUX_AMI_ID = CONFIG.get('linux', 'ami')
INSTANCE_TYPE = CONFIG.get('windows', 'instance_type')

SSM_DOC_NAME = PREFIX + 'automation-asg'
CFN_STACK_NAME = PREFIX + 'automation-asg'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

orig_client = boto3.client
ec2_client = boto3.client('ec2')
as_client = boto3.client('autoscaling')
iam_client = boto3.client('iam')


def create_send_mock(result):
    return util.create_send_mock(result)


def find_default_vpc():
    return util.find_default_vpc(ec2_client)


def cleanup(vpc_id, group_name):
    util.cleanup_security_groups(ec2_client, vpc_id, group_name)


def mock_boto_client(client):
    if client == "cloudformation":

        class TestCFClass:

            def __init__(self):
                pass

            def describe_stacks(self, *args, **kwargs):
                return {"Stacks": [
                    {"StackStatus": "ROLLBACK_IN_PROGRESS"}
                ]}

        return TestCFClass()

    return orig_client(client)


class CreateSecurityGroupTests(unittest.TestCase):
    def test_create_new_security_group_linux_no_cidr(self):
        result = {"args": None}
        name = "{}SomeReallyRandomGroupName".format(PREFIX)
        default_vpc = None
        try:
            with mock.patch("create_security_group.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_security_group.boto3.client", side_effect=mock_boto_client):
                    default_vpc = find_default_vpc()
                    cleanup(default_vpc["VpcId"], name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "GroupName": name,
                            "VpcId": default_vpc["VpcId"],
                            "Platform": "linux",
                            "RemoteAccessCidr": "10.0.0.0/24"
                        }
                    }
                    context = {}
                    create_security_group.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")
                    self.assertTrue(physicalResourceId.startswith("created:"))

                    security_group = \
                        ec2_client.describe_security_groups(GroupIds=[responseData["SecurityGroupId"]])[
                            "SecurityGroups"][0]
                    self.assertEqual(security_group["GroupName"], name)
                    self.assertEqual(len(security_group["IpPermissions"]), 0)
        finally:
            if default_vpc is not None:
                cleanup(default_vpc["VpcId"], name)

    def test_create_new_security_group_linux_with_cidr(self):
        result = {"args": None}
        name = "{}SomeReallyRandomGroupName".format(PREFIX)
        default_vpc = None
        try:
            with mock.patch("create_security_group.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_security_group.boto3.client", side_effect=mock_boto_client):
                    default_vpc = find_default_vpc()
                    cleanup(default_vpc["VpcId"], name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "GroupName": name,
                            "VpcId": default_vpc["VpcId"],
                            "Platform": "linux",
                            'AccessCidr': "10.0.0.0/24"
                        }
                    }
                    context = {}
                    create_security_group.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")
                    self.assertTrue(physicalResourceId.startswith("created:"))

                    print [responseData["SecurityGroupId"]]
                    security_group = \
                        ec2_client.describe_security_groups(GroupIds=[responseData["SecurityGroupId"]])[
                            "SecurityGroups"][0]
                    self.assertEqual(security_group["GroupName"], name)
                    self.assertEqual(len(security_group["IpPermissions"]), 1)
                    self.assertDictContainsSubset({
                        "FromPort": 22,
                        "IpRanges": [{"CidrIp": "10.0.0.0/24"}]
                    }, security_group["IpPermissions"][0])
        finally:
            if default_vpc is not None:
                cleanup(default_vpc["VpcId"], name)

    def test_create_new_security_group_windows_with_cidr(self):
        result = {"args": None}
        name = "{}SomeReallyRandomGroupName".format(PREFIX)
        default_vpc = None
        try:
            with mock.patch("create_security_group.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_security_group.boto3.client", side_effect=mock_boto_client):
                    default_vpc = find_default_vpc()
                    cleanup(default_vpc["VpcId"], name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "GroupName": name,
                            "VpcId": default_vpc["VpcId"],
                            "Platform": "windows",
                            'AccessCidr': "10.0.0.0/24"
                        }
                    }
                    context = {}
                    create_security_group.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")
                    self.assertTrue(physicalResourceId.startswith("created:"))

                    print [responseData["SecurityGroupId"]]
                    security_group = \
                        ec2_client.describe_security_groups(GroupIds=[responseData["SecurityGroupId"]])[
                            "SecurityGroups"][0]
                    self.assertEqual(security_group["GroupName"], name)
                    self.assertEqual(len(security_group["IpPermissions"]), 1)
                    self.assertDictContainsSubset({
                        "FromPort": 3389,
                        "IpRanges": [{"CidrIp": "10.0.0.0/24"}]
                    }, security_group["IpPermissions"][0])
        finally:
            if default_vpc is not None:
                cleanup(default_vpc["VpcId"], name)

    def test_existing_new_security_group_windows_with_cidr(self):
        result = {"args": None}
        name = "{}SomeReallyRandomGroupName".format(PREFIX)
        default_vpc = None
        try:
            with mock.patch("create_security_group.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_security_group.boto3.client", side_effect=mock_boto_client):
                    default_vpc = find_default_vpc()
                    cleanup(default_vpc["VpcId"], name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "GroupName": name,
                            "VpcId": default_vpc["VpcId"],
                            "Platform": "windows",
                            'AccessCidr': "10.0.0.0/24"
                        }
                    }
                    context = {}
                    create_security_group.handler(event, context)

                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    _ = \
                        ec2_client.describe_security_groups(GroupIds=[responseData["SecurityGroupId"]])[
                            "SecurityGroups"][0]

                    create_security_group.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")
                    self.assertTrue(physicalResourceId.startswith("existing:"))
        finally:
            if default_vpc is not None:
                cleanup(default_vpc["VpcId"], name)

    def test_created_delete(self):
        result = {"args": None}
        name = "{}SomeReallyRandomGroupName".format(PREFIX)
        default_vpc = None
        try:
            with mock.patch("create_security_group.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_security_group.boto3.client", side_effect=mock_boto_client):
                    default_vpc = find_default_vpc()
                    cleanup(default_vpc["VpcId"], name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "GroupName": name,
                            "VpcId": default_vpc["VpcId"],
                            "Platform": "windows",
                            'AccessCidr': "10.0.0.0/24"
                        }
                    }
                    context = {}
                    create_security_group.handler(event, context)

                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    security_group_id = responseData["SecurityGroupId"]
                    _ = ec2_client.describe_security_groups(GroupIds=[security_group_id])["SecurityGroups"][0]

                    event = {
                        "StackId": "FakeID",
                        "RequestType": "Delete",
                        "PhysicalResourceId": physicalResourceId
                    }
                    create_security_group.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")

                    try:
                        ec2_client.describe_security_groups(GroupIds=[security_group_id])
                        self.assertTrue(False, "SecurityGroup still exists")
                    except Exception:
                        pass
        finally:
            if default_vpc is not None:
                cleanup(default_vpc["VpcId"], name)

    def test_existing_delete(self):
        result = {"args": None}

        name = "{}SomeReallyRandomGroupName".format(PREFIX)
        default_vpc = None
        try:
            with mock.patch("create_security_group.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_security_group.boto3.client", side_effect=mock_boto_client):
                    default_vpc = find_default_vpc()
                    cleanup(default_vpc["VpcId"], name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "GroupName": name,
                            "VpcId": default_vpc["VpcId"],
                            "Platform": "windows",
                            'AccessCidr': "10.0.0.0/24"
                        }
                    }
                    context = {}
                    create_security_group.handler(event, context)
                    create_security_group.handler(event, context)

                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    security_group_id = responseData["SecurityGroupId"]
                    _ = ec2_client.describe_security_groups(GroupIds=[security_group_id])["SecurityGroups"][0]

                    event = {
                        "StackId": "FakeID",
                        "RequestType": "Delete",
                        "PhysicalResourceId": physicalResourceId
                    }
                    create_security_group.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")

                    groups = ec2_client.describe_security_groups(GroupIds=[security_group_id])["SecurityGroups"]
                    self.assertEqual(len(groups), 1)
        finally:
            if default_vpc is not None:
                cleanup(default_vpc["VpcId"], name)
