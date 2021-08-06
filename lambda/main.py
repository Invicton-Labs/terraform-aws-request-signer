import os
import boto3

session = boto3.Session()


def lambda_handler(event, context):
    return {
        "event": event,
        # "credentials": session.get_credentials(),
        "services": session.get_available_services()
    }
