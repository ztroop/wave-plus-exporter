from unittest import IsolatedAsyncioTestCase

from wave_reader.measure import Battery
from wave_reader.wave import WaveDevice

from wave_plus_exporter.main import SensorValues, Settings, exporter


class MockedWave(WaveDevice):
    async def get_hourly_sensor_data(self, *args):
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

    def update_gauge(self, *args):
        pass

    async def get_battery(self, *args):
        return Battery(voltage=3.0, percentage=100)


class TestExporter(IsolatedAsyncioTestCase):
    async def test_exporter(self):
        settings = Settings(
            sensor_hourly_window=12,
        )
        device = MockedWave.create("AB:CD:EF:GH:JK", "12345678")
        ret = await exporter(device, settings)

        self.assertTrue(ret)
