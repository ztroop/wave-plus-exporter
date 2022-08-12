import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SnsWrapper:
    def __init__(self, config):
        self.sns_resource = boto3.client(
            "sns",
            region_name=config.get("AWSRegion", "ca-central-1"),
            aws_access_key_id=config.get("AWSKey"),
            aws_secret_access_key=config.get("AWSSecret"),
        )
        self.phone_number = int(config.get("PhoneNumber", 0))

    def publish_text_message(self, message: str) -> str:
        try:
            response = self.sns_resource.meta.client.publish(
                PhoneNumber=self.phone_number, Message=message
            )
            message_id = response["MessageId"]
            logger.info(f"Published message to {self.phone_number}.")
        except ClientError:
            logger.error(f"Couldn't publish message to {self.phone_number}!")
        else:
            return message_id
