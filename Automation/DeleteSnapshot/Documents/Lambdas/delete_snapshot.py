import boto3


def handler(event, context):
    ec2_client = boto3.client('ec2')

    snapshot_id = event["SnapshotId"]
    ec2_client.delete_snapshot(
        SnapshotId=snapshot_id
    )
