#
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
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


