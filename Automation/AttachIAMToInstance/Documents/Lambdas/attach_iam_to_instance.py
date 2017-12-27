import boto3
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

iam_client = boto3.client('iam')
ec2_client = boto3.client('ec2')


def find_or_create_instance_profile(role_name):
    response = iam_client.list_instance_profiles_for_role(RoleName=role_name)
    if len(response['InstanceProfiles']) != 0:
        logger.info("Instance profile with role " + role_name + " already exists")
        instance_profile = response['InstanceProfiles'][0]
    else:
        logger.info("Creating instance profile for role " + role_name)
        response = iam_client.create_instance_profile(
            InstanceProfileName=role_name,
            Path='/'
        )
        instance_profile = response['InstanceProfile']

        # Now assign the role to the profile
        iam_client.add_role_to_instance_profile(
            InstanceProfileName=instance_profile['InstanceProfileName'],
            RoleName=role_name
        )

    return {
        'InstanceProfileName': instance_profile['InstanceProfileName'],
        'Arn': instance_profile['Arn']
    }


def associate_instance_profile(profile_name, profile_arn, instance_id):
    logger.info("Associating instance profile: " + profile_name + " to " + instance_id)
    # For whatever reason, new instance profiles are not available immediately. So we try again
    retry_count = 6
    while True:
        try:
            return ec2_client.associate_iam_instance_profile(
                IamInstanceProfile={
                    'Arn': profile_arn,
                    'Name': profile_name
                },
                InstanceId=instance_id
            )
        except Exception as e:
            retry_count -= 1
            if retry_count == 0:
                raise e

            logger.info("Unable to associate instance profile... trying again in 10 sec")
            time.sleep(10)


def handler(event, context):
    instance_id = event['InstanceId']
    role_name = event['RoleName']

    response = ec2_client.describe_iam_instance_profile_associations(Filters=[{
        'Name': 'instance-id',
        'Values': [instance_id]
    }])

    if len(response['IamInstanceProfileAssociations']) != 0:
        logger.info("Instance Profile already exists. Will attach role to existing instance profile")

        iam_instance_profile_association = response['IamInstanceProfileAssociations'][0]
        association_id = iam_instance_profile_association['AssociationId']
        ec2_client.disassociate_iam_instance_profile(AssociationId=association_id)

    instance_profile = find_or_create_instance_profile(role_name)
    association_response = associate_instance_profile(instance_profile['InstanceProfileName'], instance_profile['Arn'],
                                                      instance_id)
    association_id = association_response['IamInstanceProfileAssociation']['AssociationId']

    return {
        "InstanceProfileName": instance_profile['InstanceProfileName'],
        "Arn": instance_profile['Arn'],
        "RoleName": event['RoleName'],
        "AssociationId": association_id
    }
