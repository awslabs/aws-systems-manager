import boto3


def handler(event, context):
    ec2 = boto3.resource('ec2')

    volume_id = event["VolumeId"]
    description = event["Description"]
    volume = ec2.Volume(volume_id)
    volume.create_snapshot(Description=description)
