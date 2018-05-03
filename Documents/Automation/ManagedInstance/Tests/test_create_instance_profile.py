import os
import sys
import logging
import unittest

import ConfigParser
import boto3

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
import create_instance_profile
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


def cleanup(name):
    util.cleanup_instance_profile(iam_client, name)

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


class CreateInstanceTest(unittest.TestCase):
    def test_create_new_profile(self):
        result = {}
        name = "{}SomeReallyRandomRoleNameThatShouldNotExist".format(PREFIX)
        try:

            with mock.patch("create_instance_profile.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_instance_profile.boto3.client", side_effect=mock_boto_client):
                    cleanup(name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "InstanceProfileName": name
                        }
                    }
                    context = {}
                    create_instance_profile.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")
                    self.assertTrue(physicalResourceId.startswith("created:"))

                    iam_client.get_role(RoleName=name)
                    # verify instance profile was created
                    instance_profile = iam_client.get_instance_profile(InstanceProfileName=name)

                    # verify policy was added
                    attached = iam_client.list_attached_role_policies(RoleName=name)
                    arns = set([])
                    for policy in attached["AttachedPolicies"]:
                        arns.add(policy["PolicyArn"])

                    # verify role was added to profile
                    is_role_found = False
                    for role in instance_profile["InstanceProfile"]["Roles"]:
                        if role["RoleName"] == name:
                            is_role_found = True
                            continue

                    self.assertEquals(arns, set(create_instance_profile.POLICY_ARNS))
                    self.assertTrue(is_role_found, "Role was not added to the profile correctly")

        finally:
            cleanup(name)

    def test_create_existing_profile(self):
        result = {}
        name = "{}SomeReallyRandomRoleNameThatShouldNotExist".format(PREFIX)
        try:

            with mock.patch("create_instance_profile.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_instance_profile.boto3.client", side_effect=mock_boto_client):
                    cleanup(name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "InstanceProfileName": name
                        }
                    }
                    context = {}
                    create_instance_profile.handler(event, context)

                    # make sure role and instance profile exists
                    iam_client.get_role(RoleName=name)
                    iam_client.get_instance_profile(InstanceProfileName=name)

                    create_instance_profile.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")
                    self.assertTrue(physicalResourceId.startswith("existing:"))
        finally:
            cleanup(name)

    def test_delete_created_instance_profile(self):
        result = {}
        name = "{}SomeReallyRandomRoleNameThatShouldNotExist".format(PREFIX)
        try:

            with mock.patch("create_instance_profile.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_instance_profile.boto3.client", side_effect=mock_boto_client):
                    cleanup(name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "InstanceProfileName": name
                        }
                    }
                    context = {}
                    create_instance_profile.handler(event, context)

                    # make sure role and instance profile exists
                    iam_client.get_role(RoleName=name)
                    iam_client.get_instance_profile(InstanceProfileName=name)

                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    event = {
                        "RequestType": "Delete",
                        "StackId": "FakeID",
                        "PhysicalResourceId": physicalResourceId
                    }
                    create_instance_profile.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")

                    try:
                        iam_client.get_role(RoleName=name)
                        self.assertTrue(False, "Role still exists in account")
                    except Exception as e:
                        pass

                    try:
                        iam_client.get_instance_profile(RoleName=name)
                        self.assertTrue(False, "Instance still exists in account")
                    except Exception as e:
                        pass

        finally:
            cleanup(name)

    def test_delete_existing_instance_profile(self):
        result = {}
        name = "{}SomeReallyRandomRoleNameThatShouldNotExist".format(PREFIX)
        try:

            with mock.patch("create_instance_profile.cfnresponse.send", side_effect=create_send_mock(result)):
                with mock.patch("create_instance_profile.boto3.client", side_effect=mock_boto_client):
                    cleanup(name)

                    event = {
                        "RequestType": "Create",
                        "StackId": "FakeID",
                        "ResourceProperties": {
                            "InstanceProfileName": name
                        }
                    }
                    context = {}
                    create_instance_profile.handler(event, context)
                    create_instance_profile.handler(event, context)

                    # make sure role and instance profile exists
                    iam_client.get_role(RoleName=name)
                    iam_client.get_instance_profile(InstanceProfileName=name)

                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    event = {
                        "RequestType": "Delete",
                        "StackId": "FakeID",
                        "PhysicalResourceId": physicalResourceId
                    }
                    create_instance_profile.handler(event, context)

                    print result["args"]
                    (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
                    self.assertEqual(responseStatus, "SUCCESS")
                    self.assertTrue(physicalResourceId.startswith("existing:"))

                    # make sure role and instance profile exists
                    iam_client.get_role(RoleName=name)
                    iam_client.get_instance_profile(InstanceProfileName=name)
        finally:
            cleanup(name)
