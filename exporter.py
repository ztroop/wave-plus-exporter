import asyncio
import os
import struct
import sys
from dataclasses import dataclass
from time import sleep
from typing import List

import bleak
import prometheus_client as prom
from bleak import BleakClient
from wave_reader.wave import WaveDevice

SENSOR_RECORD_UUID = "b42e2fc2-ade7-11e4-89d3-123b93f75cba"
COMMAND_UUID = "b42e2d06-ade7-11e4-89d3-123b93f75cba"

RADON_AVG = prom.Gauge(
    "radon_avg", "Average radon level measured in becquerels per cubic metre"
)
TEMPERATURE_AVG = prom.Gauge("temperature_avg", "Average tempature in celcius")
HUMIDITY_AVG = prom.Gauge("humidity_avg", "Average humidity")
PRESSURE_AVG = prom.Gauge("pressure_avg", "Average pressure")
CO2_AVG = prom.Gauge("co2_avg", "Average CO2 level")
VOC_AVG = prom.Gauge("voc_avg", "Average VOC level")
AMBIANT_LIGHT_AVG = prom.Gauge("light_avg", "Average light level")
X3_AVG = prom.Gauge("x3_avg", "No description")
X4_AVG = prom.Gauge("x4_avg", "No description")


def avg(collection: List):
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
    async def get_sensor_values(self, hours: int = 48):
        async with BleakClient(self.address, timeout=10) as client:
            cmd = struct.pack("<BHHHH", 0x01, 2, 0, hours, 0)
            raw_data = []

            if not client.is_connected:
                return

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
    def update_guage(data: List[SensorValues]):
        RADON_AVG.set(avg([d.radon for d in data]))
        TEMPERATURE_AVG.set(avg([d.temperature for d in data]))
        HUMIDITY_AVG.set(avg([d.humidity for d in data]))
        PRESSURE_AVG.set(avg([d.pressure for d in data]))
        CO2_AVG.set(avg([d.co2 for d in data]))
        VOC_AVG.set(avg([d.voc for d in data]))
        AMBIANT_LIGHT_AVG.set(avg([d.light for d in data]))
        X3_AVG.set(avg([d.x3 for d in data]))
        X4_AVG.set(avg([d.x4 for d in data]))


async def main(address: str, serial: str):
    while True:
        try:
            device = WavePlus.create(address, serial)
            data = await device.get_sensor_values(
                hours=int(os.environ.get("READING_WINDOW", 12))
            )
            device.update_guage(data)
        except bleak.exc.BleakDBusError:
            continue
        sleep(int(os.environ.get("UPDATE_DELAY", 12)) * 60 * 60)


if __name__ == "__main__":
    prom.start_http_server(int(os.environ.get("EXPORTER_PORT", 8000)))
    asyncio.run(main(sys.argv[1], sys.argv[2]))
