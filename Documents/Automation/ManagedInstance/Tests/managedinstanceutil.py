import logging
import time
import json

LOGGER = logging.getLogger(__name__)

def find_default_vpc(ec2):
    for vpc in ec2.describe_vpcs().get('Vpcs', []):
        if vpc.get('IsDefault', False):
            return vpc

    return {"VpcId": None}


def create_send_mock(result):
    def send_mock(*args):
        result["args"] = args

    return send_mock


def cleanup_instance_profile(iam, name):
    try:
        attached = iam.list_attached_role_policies(RoleName=name)
        for policy in attached["AttachedPolicies"]:
            iam.detach_role_policy(RoleName=name, PolicyArn=policy["PolicyArn"])
    except Exception as e:
        print str(e)

    try:
        instance_profile = iam.get_instance_profile(InstanceProfileName=name)
        for role in instance_profile["InstanceProfile"].get("Roles", []):
            iam.remove_role_from_instance_profile(
                InstanceProfileName=name,
                RoleName=role["RoleName"]
            )
    except Exception as e:
        print str(e)

    try:
        iam.delete_instance_profile(InstanceProfileName=name)
    except Exception as e:
        print str(e)

    try:
        iam.delete_role(RoleName=name)
    except Exception as e:
        print str(e)


def cleanup_security_groups(ec2, vpc_id, group_name):
    try:
        groups = ec2.describe_security_groups(Filters=[
            {"Name": "group-name", "Values": [group_name]},
            {"Name": "vpc-id", "Values": [vpc_id]}
        ])["SecurityGroups"]

        if len(groups) > 0:
            group_id = groups[0]["GroupId"]
            try:
                ec2.delete_security_group(GroupId=group_id)
            except Exception as e:
                str(e)
    except Exception as e:
        print str(e)


def cleanup_key_pair(ec2, name):
    try:
        ec2.delete_key_pair(KeyName=name)
    except Exception as e:
        print str(e)


def cleanup_instance(ec2, instance_id):
    waiter = ec2.get_waiter('instance_terminated')

    ec2.terminate_instances(InstanceIds=[instance_id])
    waiter.wait(InstanceIds=[instance_id])


class sns_topic:
    def __init__(self, name, sns_client):
        self.name = name
        self.sns_client = sns_client

    def __enter__(self):
        self.cleanup()
        return self.sns_client.create_topic(Name=self.name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        try:
            self.sns_client.delete_topic(TopicArn=self.name)
        except Exception:
            pass


class admin_role:
    def __init__(self, iam_client, sts_client, role_name, user_arn):
        self.user_arn = user_arn
        self.role_name = role_name
        self.iam_client = iam_client
        self.sts_client = sts_client

    def __enter__(self):
        self.cleanup()
        assume_role = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": [
                            "lambda.amazonaws.com",
                            "ssm.amazonaws.com",
                            "cloudformation.amazonaws.com",
                            "ec2.amazonaws.com"
                        ]
                    },
                    "Action": "sts:AssumeRole"
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": self.user_arn},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        result = self.iam_client.create_role(RoleName=self.role_name, AssumeRolePolicyDocument=json.dumps(assume_role))
        self.iam_client.attach_role_policy(RoleName=self.role_name, PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")

        # For what ever reason assuming a role that got created too fast fails, so we just wait until we can.
        retry_count = 6
        while True:
            try:
                self.sts_client.assume_role(RoleArn=result["Role"]["Arn"], RoleSessionName="checking_assume")
                break
            except Exception as e:
                retry_count -= 1
                if retry_count == 0:
                    raise e

                LOGGER.info("Unable to assume role... trying again in 10 sec")
                time.sleep(10)

        return result

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        try:
            self.iam_client.detach_role_policy(
                RoleName=self.role_name,
                PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
            )
        except Exception as e:
            pass

        try:
            self.iam_client.delete_role(RoleName=self.role_name)
        except Exception as e:
            pass
