import boto3
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    ec2 = boto3.resource('ec2')

    volume_id = event["VolumeId"]
    volume = ec2.Volume(volume_id)
    volume.detach_from_instance()

    retry_count = 0
    attachment_state = 'detaching'

    while retry_count < 35:

        retry_count += 1
        volume.reload()

        if len(volume.attachments) == 0:
            attachment_state = 'detached'
            break
        attachment_state = volume.attachments[0]['State']
        if attachment_state == 'detached' or attachment_state == 'busy':
            break

        time.sleep(1)
        logger.info("Current Attachment State:" + attachment_state + ", tries:" + str(retry_count))

    logger.info("Last Attachment State:" + attachment_state + ", tries:" + str(retry_count))

    if attachment_state == 'busy':
        logger.warn('Volume still mounted. Will detach once volume is unmounted from instance.')
        raise Exception('Volume still mounted. Will detach once volume is unmounted from instance.')

    if attachment_state != 'detached':
        raise Exception('Failed to detach volume.  Current state is:' + attachment_state)

