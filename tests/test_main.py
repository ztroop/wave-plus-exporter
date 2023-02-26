from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from wave_reader.wave import WaveDevice
from wave_plus_exporter.main import SensorValues, exporter


class MockedWave(WaveDevice):
    async def get_hourly_sensor_data(*args):
        return [
            SensorValues(
                radon=80,
                temperature=21,
                humidity=40,
                pressure=980,
                co2=500,
                voc=90,
                light=0,
                x3=0,
                x4=0,
            )
        ]

    def update_guage(*args):
        pass


class TestExporter(IsolatedAsyncioTestCase):
    async def test_exporter(self):
        config = {
            "DeviceAddress": "AB:CD:EF:GH:JK",
            "DeviceSerial": "12345678",
            "PhoneEnabled": False,
            "PhoneNumber": 1234567890,
            "SensorHourlyWindow": 12,
            "RadonThreshold": 99.0,
            "ConnectionRetries": 3,
            "HourlyUpdateWindow": 6,
        }
        device = MockedWave.create(config["DeviceAddress"], config["DeviceSerial"])
        ret = await exporter(device, config)

        self.assertTrue(ret)

    @patch("wave_plus_exporter.main.SnsWrapper", autospec=True)
    @patch("wave_plus_exporter.main.logger")
    async def test_exporter_sns(self, logger, sns):
        config = {
            "DeviceAddress": "AB:CD:EF:GH:JK",
            "DeviceSerial": "12345678",
            "PhoneEnabled": True,
            "PhoneNumber": 1234567890,
            "SensorHourlyWindow": 12,
            "RadonThreshold": 70.0,
            "ConnectionRetries": 3,
            "HourlyUpdateWindow": 6,
        }
        device = MockedWave.create(config["DeviceAddress"], config["DeviceSerial"])
        ret = await exporter(device, config)

        expected_msg = "Radon levels are high (80.0). Open the windows!"

        logger.info.assert_called_with(expected_msg)
        sns(config).publish_text_message.assert_called_with(f"Wave: {expected_msg}")
        self.assertTrue(ret)
