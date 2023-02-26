from datetime import datetime, timedelta
import logging
from typing import Optional

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
        self.last_sent: Optional[datetime] = None

    def publish_text_message(self, message: str) -> Optional[str]:
        if self.last_sent and datetime.now() < (self.last_sent + timedelta(minutes=5)):
            return
        try:
            response = self.sns_resource.meta.client.publish(
                PhoneNumber=self.phone_number, Message=message
            )
            message_id = response["MessageId"]
            self.last_sent = datetime.now()
            logger.info(f"Published message to {self.phone_number}.")
        except ClientError:
            logger.error(f"Couldn't publish message to {self.phone_number}!")
        else:
            return message_id
