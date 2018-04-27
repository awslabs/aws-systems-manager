import boto3
import traceback

import cfnresponse


def handler_ami_info(event, context):
    try:
        ec2 = boto3.client('ec2')
        ami_id = event["ResourceProperties"].get("AmiId", None)
        vpc_id = event["ResourceProperties"].get("VpcId", "")
        if ami_id is None:
            raise Exception("AMI id must be provided")

        data = {}

        # find platform based on ami
        images = ec2.describe_images(ImageIds=[ami_id])["Images"]
        if len(images) == 0:
            raise Exception("No image found with " + ami_id)
        data["Platform"] = images[0].get("Platform", "linux")
        data["UserData"] = "" if data["Platform"] == "windows" else "IyEvYmluL2Jhc2gNCg0KZnVuY3Rpb24gZ2V0X2NvbnRlbnRzKCkgew0KICAgIGlmIFsgLXggIiQod2hpY2ggY3VybCkiIF07IHRoZW4NCiAgICAgICAgY3VybCAtcyAtZiAiJDEiDQogICAgZWxpZiBbIC14ICIkKHdoaWNoIHdnZXQpIiBdOyB0aGVuDQogICAgICAgIHdnZXQgIiQxIiAtTyAtDQogICAgZWxzZQ0KICAgICAgICBkaWUgIk5vIGRvd25sb2FkIHV0aWxpdHkgKGN1cmwsIHdnZXQpIg0KICAgIGZpDQp9DQoNCnJlYWRvbmx5IElERU5USVRZX1VSTD0iaHR0cDovLzE2OS4yNTQuMTY5LjI1NC8yMDE2LTA2LTMwL2R5bmFtaWMvaW5zdGFuY2UtaWRlbnRpdHkvZG9jdW1lbnQvIg0KcmVhZG9ubHkgVFJVRV9SRUdJT049JChnZXRfY29udGVudHMgIiRJREVOVElUWV9VUkwiIHwgYXdrIC1GXCIgJy9yZWdpb24vIHsgcHJpbnQgJDQgfScpDQpyZWFkb25seSBERUZBVUxUX1JFR0lPTj0idXMtZWFzdC0xIg0KcmVhZG9ubHkgUkVHSU9OPSIke1RSVUVfUkVHSU9OOi0kREVGQVVMVF9SRUdJT059Ig0KDQpyZWFkb25seSBTQ1JJUFRfTkFNRT0iYXdzLWluc3RhbGwtc3NtLWFnZW50Ig0KIFNDUklQVF9VUkw9Imh0dHBzOi8vYXdzLXNzbS1kb3dubG9hZHMtJFJFR0lPTi5zMy5hbWF6b25hd3MuY29tL3NjcmlwdHMvJFNDUklQVF9OQU1FIg0KDQppZiBbICIkUkVHSU9OIiA9ICJjbi1ub3J0aC0xIiBdOyB0aGVuDQogIFNDUklQVF9VUkw9Imh0dHBzOi8vYXdzLXNzbS1kb3dubG9hZHMtJFJFR0lPTi5zMy5jbi1ub3J0aC0xLmFtYXpvbmF3cy5jb20uY24vc2NyaXB0cy8kU0NSSVBUX05BTUUiDQpmaQ0KDQppZiBbICIkUkVHSU9OIiA9ICJ1cy1nb3Ytd2VzdC0xIiBdOyB0aGVuDQogIFNDUklQVF9VUkw9Imh0dHBzOi8vYXdzLXNzbS1kb3dubG9hZHMtJFJFR0lPTi5zMy11cy1nb3Ytd2VzdC0xLmFtYXpvbmF3cy5jb20vc2NyaXB0cy8kU0NSSVBUX05BTUUiDQpmaQ0KDQpjZCAvdG1wDQpGSUxFX1NJWkU9MA0KTUFYX1JFVFJZX0NPVU5UPTMNClJFVFJZX0NPVU5UPTANCg0Kd2hpbGUgWyAkUkVUUllfQ09VTlQgLWx0ICRNQVhfUkVUUllfQ09VTlQgXSA7IGRvDQogIGVjaG8gQVdTLVVwZGF0ZUxpbnV4QW1pOiBEb3dubG9hZGluZyBzY3JpcHQgZnJvbSAkU0NSSVBUX1VSTA0KICBnZXRfY29udGVudHMgIiRTQ1JJUFRfVVJMIiA+ICIkU0NSSVBUX05BTUUiDQogIEZJTEVfU0laRT0kKGR1IC1rIC90bXAvJFNDUklQVF9OQU1FIHwgY3V0IC1mMSkNCiAgZWNobyBBV1MtVXBkYXRlTGludXhBbWk6IEZpbmlzaGVkIGRvd25sb2FkaW5nIHNjcmlwdCwgc2l6ZTogJEZJTEVfU0laRQ0KICBpZiBbICRGSUxFX1NJWkUgLWd0IDAgXTsgdGhlbg0KICAgIGJyZWFrDQogIGVsc2UNCiAgICBpZiBbWyAkUkVUUllfQ09VTlQgLWx0IE1BWF9SRVRSWV9DT1VOVCBdXTsgdGhlbg0KICAgICAgUkVUUllfQ09VTlQ9JCgoUkVUUllfQ09VTlQrMSkpOw0KICAgICAgZWNobyBBV1MtVXBkYXRlTGludXhBbWk6IEZpbGVTaXplIGlzIDAsIHJldHJ5Q291bnQ6ICRSRVRSWV9DT1VOVA0KICAgIGZpDQogIGZpIA0KZG9uZQ0KDQppZiBbICRGSUxFX1NJWkUgLWd0IDAgXTsgdGhlbg0KICBjaG1vZCAreCAiJFNDUklQVF9OQU1FIg0KICBlY2hvIEFXUy1VcGRhdGVMaW51eEFtaTogUnVubmluZyBVcGRhdGVTU01BZ2VudCBzY3JpcHQgbm93IC4uLi4NCiAgLi8iJFNDUklQVF9OQU1FIiAtLXJlZ2lvbiAiJFJFR0lPTiINCmVsc2UNCiAgZWNobyBBV1MtVXBkYXRlTGludXhBbWk6IFVuYWJsZSB0byBkb3dubG9hZCBzY3JpcHQsIHF1aXR0aW5nIC4uLi4NCmZp"

        # find default vpc id if non is specified
        if len(vpc_id) == 0 or vpc_id == "Default":
            vpc_id = ""
            for vpc in ec2.describe_vpcs().get('Vpcs', []):
                if vpc.get('IsDefault', False):
                    vpc_id = vpc['VpcId']
                    break
            if len(vpc_id) == 0:
                raise Exception("Unable to find default vpc")
        data["VpcId"] = vpc_id

        cfnresponse.send(event, context, cfnresponse.SUCCESS, data, event.get("PhysicalResourceId", None))
    except Exception as e:
        print str(e)
        traceback.print_exc()
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, event.get("PhysicalResourceId", None))


def handler_delete(event, context):
    # Nothing to do... this is a informational lambda and no resource is created.
    cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, event["PhysicalResourceId"])


def handler(event, context):
    if event["RequestType"] in ["Create", "Update"]:
        handler_ami_info(event, context)
    elif event["RequestType"] in ["Delete"]:
        handler_delete(event, context)
