import boto3


def handler(event, context):
    cf = boto3.client("cloudformation")

    cf.update_stack(
        StackName=event["StackName"],
        TemplateURL=event["TemplateUrl"],
        Capabilities=["CAPABILITY_IAM"]
    )
