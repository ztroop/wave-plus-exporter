from twilio.rest import Client

from datetime import datetime, timedelta
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class TwilioWrapper:
    def __init__(self, config):
        self.client = Client(config.get("TwilioAccountSID"), config.get("TwilioToken"))
        self.phone_number = int(config.get("PhoneNumber", 0))
        self.last_sent: Optional[datetime] = None

    def publish_text_message(self, message: str) -> Optional[str]:
        if self.last_sent and datetime.now() < (self.last_sent + timedelta(minutes=5)):
            return
        try:
            sent_message = self.client.messages.create(body=message, to=self.phone_number)
            self.last_sent = datetime.now()
            logger.info(f"Published message to {self.phone_number}.")
        except Exception:
            logger.error(f"Couldn't publish message to {self.phone_number}!")
        else:
            return sent_message.sid
