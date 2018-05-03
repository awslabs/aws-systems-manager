import os
import sys
import logging
import unittest
import json
from functools import partial

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
import collect_info
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

vpcUtil = ssm_testing.VPCTester(boto3.resource('ec2', region_name=REGION))
boto3.setup_default_session(region_name=REGION)

ec2_client = boto3.client('ec2')
as_client = boto3.client('autoscaling')
iam_client = boto3.client('iam')


class InfoTest(unittest.TestCase):
    def test_handler_on_create_windows(self):
        result = {}

        def send_mock(*args):
            result["args"] = args

        default_vpc = util.find_default_vpc(ec2_client)

        with mock.patch("collect_info.cfnresponse.send", side_effect=send_mock):
            event = {
                "RequestType": "Create",
                "ResourceProperties": {
                    "AmiId": WINDOWS_AMI_ID,
                    "VpcId": "Default"
                }
            }
            context = {}
            collect_info.handler(event, context)

            (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
            self.assertEqual(responseStatus, "SUCCESS")
            self.assertDictContainsSubset({
                "Platform": "windows",
                "VpcId": default_vpc["VpcId"]
            }, responseData)
            self.assertIsNone(physicalResourceId)

    def test_handler_on_create_linux(self):
        result = {}

        def send_mock(*args):
            result["args"] = args

        with mock.patch("collect_info.cfnresponse.send", side_effect=send_mock):
            event = {
                "RequestType": "Create",
                "ResourceProperties": {
                    "AmiId": LINUX_AMI_ID,
                    "VpcId": "vpc-id-12345"
                }
            }
            context = {}
            collect_info.handler(event, context)

            print result["args"]
            (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
            self.assertEqual(responseStatus, "SUCCESS")
            self.assertDictContainsSubset({
                "Platform": "linux",
                "VpcId": "vpc-id-12345"
            }, responseData)
            self.assertIsNone(physicalResourceId)

    def test_handler_on_create_bad_ami(self):
        result = {}

        def send_mock(*args):
            result["args"] = args

        with mock.patch("collect_info.cfnresponse.send", side_effect=send_mock):
            event = {
                "RequestType": "Create",
                "ResourceProperties": {
                    "AmiId": "ami-invalid123"
                }
            }
            context = {}
            collect_info.handler(event, context)

            (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
            self.assertEqual(responseStatus, "FAILED")
            self.assertIsNone(physicalResourceId)

    def test_handler_on_update_windows(self):
        result = {}

        def send_mock(*args):
            result["args"] = args

        with mock.patch("collect_info.cfnresponse.send", side_effect=send_mock):
            event = {
                "RequestType": "Update",
                "PhysicalResourceId": "testing_resource_id",
                "ResourceProperties": {
                    "AmiId": WINDOWS_AMI_ID
                }
            }
            context = {}
            collect_info.handler(event, context)

            (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
            self.assertEqual(responseStatus, "SUCCESS")
            self.assertDictContainsSubset({"Platform": "windows"}, responseData)
            self.assertEqual(physicalResourceId, "testing_resource_id")

    def test_handler_on_update_linux(self):
        result = {}

        def send_mock(*args):
            result["args"] = args

        with mock.patch("collect_info.cfnresponse.send", side_effect=send_mock):
            event = {
                "RequestType": "Update",
                "PhysicalResourceId": "testing_resource_id",
                "ResourceProperties": {
                    "AmiId": LINUX_AMI_ID
                }
            }
            context = {}
            collect_info.handler(event, context)

            (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
            self.assertEqual(responseStatus, "SUCCESS")
            self.assertDictContainsSubset({"Platform": "linux"}, responseData)
            self.assertEqual("testing_resource_id", physicalResourceId)

    def test_handler_on_update_bad_ami(self):
        result = {}

        def send_mock(*args):
            result["args"] = args

        with mock.patch("collect_info.cfnresponse.send", side_effect=send_mock):
            event = {
                "RequestType": "Create",
                "PhysicalResourceId": "testing_resource_id",
                "ResourceProperties": {
                    "AmiId": "ami-invalid123"
                }
            }
            context = {}

            collect_info.handler(event, context)

            (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
            self.assertEqual(responseStatus, "FAILED")
            self.assertEqual(physicalResourceId, "testing_resource_id")

    def test_handler_on_delete(self):
        result = {}

        def send_mock(*args):
            result["args"] = args

        with mock.patch("collect_info.cfnresponse.send", side_effect=send_mock):
            event = {
                "RequestType": "Delete",
                "PhysicalResourceId": "testing_resource_id",
                "ResourceProperties": {
                    "AmiId": LINUX_AMI_ID
                }
            }
            context = {}
            collect_info.handler(event, context)

            (event, context, responseStatus, responseData, physicalResourceId) = result["args"]
            self.assertEqual(responseStatus, "SUCCESS")
            self.assertEqual(physicalResourceId, "testing_resource_id")
