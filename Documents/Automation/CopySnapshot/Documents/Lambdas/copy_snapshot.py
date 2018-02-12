import boto3


def handler(event, context):
    ec2_client = boto3.client("ec2")

    snapshot_id = event["SnapshotId"]
    source_region = event["SourceRegion"]
    description = event["Description"]
    response = ec2_client.copy_snapshot(
        Description=description,
        SourceRegion=source_region,
        SourceSnapshotId=snapshot_id
    )

    return {
        "SnapshotId": response["SnapshotId"]
    }
