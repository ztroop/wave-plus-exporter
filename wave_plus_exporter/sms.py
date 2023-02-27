from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from twilio.rest import Client


class TwilioWrapper:
    def __init__(self, config):
        self.client = Client(config.get("TwilioAccountSID"), config.get("TwilioToken"))
        self.receiving_num = config.get("PhoneNumber", "")
        self.last_sent: Optional[datetime] = None
        self.sending_num = config.get("TwilioSender", "")

    def publish_text_message(self, message: str) -> Optional[str]:
        if self.last_sent and datetime.now() < (self.last_sent + timedelta(minutes=5)):
            logger.warning(f"Rate limit hit. Last sent: {self.last_sent}")
            return
        try:
            sent_message = self.client.messages.create(
                body=message, to=self.receiving_num, from_=self.sending_num
            )
            self.last_sent = datetime.now()
            logger.info(
                f"Published message to {self.receiving_num} at {self.last_sent}!"
            )
        except Exception as error:
            logger.error(f"Couldn't publish message to {self.receiving_num}!")
            logger.error(f"Unhandled exception. {error}")
        else:
            return sent_message.sid
