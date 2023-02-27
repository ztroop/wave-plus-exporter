import asyncio
import struct
import sys
from dataclasses import dataclass
from time import sleep
from typing import List, Tuple, Union

import bleak
import prometheus_client as prom
from bleak import BleakClient
from bleak.exc import BleakError
from loguru import logger
from wave_reader.wave import WaveDevice

from wave_plus_exporter.sms import TwilioWrapper

SENSOR_RECORD_UUID = "b42e2fc2-ade7-11e4-89d3-123b93f75cba"
COMMAND_UUID = "b42e2d06-ade7-11e4-89d3-123b93f75cba"

RADON_AVG = prom.Gauge(
    "radon_avg", "Average radon level measured in becquerels per cubic metre"
)
TEMPERATURE_AVG = prom.Gauge("temperature_avg", "Average temperature in celcius")
HUMIDITY_AVG = prom.Gauge("humidity_avg", "Average humidity")
PRESSURE_AVG = prom.Gauge("pressure_avg", "Average pressure")
CO2_AVG = prom.Gauge("co2_avg", "Average CO2 level")
VOC_AVG = prom.Gauge("voc_avg", "Average VOC level")
AMBIANT_LIGHT_AVG = prom.Gauge("light_avg", "Average light level")
X3_AVG = prom.Gauge("x3_avg", "No description")
X4_AVG = prom.Gauge("x4_avg", "No description")


def avg(collection: Union[Tuple, List]):
    return sum(collection) / len(collection)


@dataclass
class SensorValues:
    radon: float
    temperature: float
    humidity: float
    pressure: float
    co2: float
    voc: float
    light: float
    x3: float
    x4: float


class WavePlus(WaveDevice):
    async def get_hourly_sensor_data(self, hours: int) -> List[SensorValues]:
        async with BleakClient(self.address, timeout=10) as client:
            cmd = struct.pack("<BHHHH", 0x01, 2, 0, hours, 0)
            raw_data = []

            if not client.is_connected:
                raise BleakError("Client is not connected.")

            await client.start_notify(
                SENSOR_RECORD_UUID, lambda x, y: raw_data.append((x, y))
            )
            await client.write_gatt_char(COMMAND_UUID, cmd)
            await asyncio.sleep(10.0)
            await client.stop_notify(SENSOR_RECORD_UUID)

            return [WavePlus.parse_hour_block(i[1]) for i in raw_data]

    async def flash_light(self):
        async with BleakClient(self.address) as client:
            if not client.is_connected:
                return False

            cmd = struct.pack("<BB", 0x67, 0x08)
            await client.write_gatt_char(COMMAND_UUID, cmd)

            return True

    @staticmethod
    def parse_hour_block(raw: bytearray):
        parts = struct.unpack("<8H HH 12H 12B 12H 12H", raw[:104])
        unused = [parts[0:8]]
        radon = parts[8:10]
        temp = parts[10:22]
        hum = parts[22:34]
        pres = parts[34:46]
        co2 = parts[46:58]

        parts = [
            struct.unpack("<2HL", raw[104 + i * 8 : 112 + i * 8]) for i in range(12)
        ]

        x4 = [p[0] for p in parts]
        voc = [p[1] for p in parts]
        x3 = [p[2] for p in parts]

        parts = struct.unpack("< 12B 6B L 4H", raw[200:230])

        light = parts[0:12]
        unused.append(parts[12:18])
        unused.append(parts[19:22])
        # tim = parts[18]
        # recno = parts[22]

        temperature = [(t - 27315) / 100 for t in temp]
        humidity = [h / 2 for h in hum]
        pressure = [p / 50 for p in pres]
        x3 = [
            x / 256 for x in x3
        ]  # Not really sure if that low order byte belongs or not.

        return SensorValues(
            radon=avg(radon),
            temperature=avg(temperature),
            humidity=avg(humidity),
            pressure=avg(pressure),
            co2=avg(co2),
            voc=avg(voc),
            light=avg(light),
            x3=avg(x3),
            x4=avg(x4),
        )

    @staticmethod
    def update_gauge(data: List[SensorValues]):
        RADON_AVG.set(avg([d.radon for d in data]))
        TEMPERATURE_AVG.set(avg([d.temperature for d in data]))
        HUMIDITY_AVG.set(avg([d.humidity for d in data]))
        PRESSURE_AVG.set(avg([d.pressure for d in data]))
        CO2_AVG.set(avg([d.co2 for d in data]))
        VOC_AVG.set(avg([d.voc for d in data]))
        AMBIANT_LIGHT_AVG.set(avg([d.light for d in data]))
        X3_AVG.set(avg([d.x3 for d in data]))
        X4_AVG.set(avg([d.x4 for d in data]))


async def exporter(device, config):
    phone_enabled = bool(config.get("PhoneEnabled", False))
    phone_number = int(config.get("PhoneNumber", 0))

    try:
        hours = int(config.get("SensorHourlyWindow", 12))
        data = await device.get_hourly_sensor_data(hours)

        logger.debug("Updating Prometheus gauges.")
        device.update_gauge(data)

        if not phone_enabled or not phone_number:
            logger.debug("Phone is disabled or number not set.")
            return True

        sms = TwilioWrapper(config)
        radon_average = avg([d.radon for d in data])
        if radon_average > float(config.get("RadonThreshold", 99.9)):
            message = f"Radon levels are high ({radon_average}). Open the windows!"
            logger.info(message)
            sms.publish_text_message(f"Wave: {message}")

    except (bleak.exc.BleakDBusError, bleak.exc.BleakError):
        logger.error(f"Failed to connect to device!")
        return False

    except Exception as error:
        logger.error(f"Unhandled exception. {error}")
        sys.exit(1)

    return True


async def run_loop(config):
    address = config.get("DeviceAddress")
    serial = config.get("DeviceSerial")

    if not address or not serial:
        logger.error("Invalid device address or serial. Check configuration.")
        sys.exit(1)

    device = WavePlus.create(address, serial)

    while True:
        attempt = False
        retries = 0
        while not attempt and retries < 5:
            logger.info(f"Updating and exporting sensor values. Attempt ({retries}/5)")
            attempt = await exporter(device, config)
            retries += 1

        sleep_interval = int(config.get("HourlyUpdateDelay", 6))
        logger.info(f"Sleeping for {sleep_interval} hours.")
        sleep(sleep_interval * 60 * 60)
