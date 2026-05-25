import argparse
import asyncio
import struct
import sys
from dataclasses import dataclass
from typing import List

import bleak
import prometheus_client as prom
from bleak import BleakClient
from bleak.exc import BleakError
from loguru import logger
from wave_reader.wave import WaveDevice

SENSOR_RECORD_UUID = "b42e2fc2-ade7-11e4-89d3-123b93f75cba"
COMMAND_UUID = "b42e2d06-ade7-11e4-89d3-123b93f75cba"

APP_REGISTRY = prom.CollectorRegistry()

LABEL_NAMES = ["address", "serial"]

RADON_AVG = prom.Gauge(
    "radon_avg",
    "Average radon level measured in becquerels per cubic metre",
    labelnames=LABEL_NAMES,
    registry=APP_REGISTRY,
)
TEMPERATURE_AVG = prom.Gauge(
    "temperature_avg",
    "Average temperature in celcius",
    labelnames=LABEL_NAMES,
    registry=APP_REGISTRY,
)
HUMIDITY_AVG = prom.Gauge(
    "humidity_avg", "Average humidity", labelnames=LABEL_NAMES, registry=APP_REGISTRY
)
PRESSURE_AVG = prom.Gauge(
    "pressure_avg", "Average pressure", labelnames=LABEL_NAMES, registry=APP_REGISTRY
)
CO2_AVG = prom.Gauge(
    "co2_avg", "Average CO2 level", labelnames=LABEL_NAMES, registry=APP_REGISTRY
)
VOC_AVG = prom.Gauge(
    "voc_avg", "Average VOC level", labelnames=LABEL_NAMES, registry=APP_REGISTRY
)
AMBIANT_LIGHT_AVG = prom.Gauge(
    "light_avg", "Average light level", labelnames=LABEL_NAMES, registry=APP_REGISTRY
)
X3_AVG = prom.Gauge(
    "x3_avg", "No description", labelnames=LABEL_NAMES, registry=APP_REGISTRY
)
X4_AVG = prom.Gauge(
    "x4_avg", "No description", labelnames=LABEL_NAMES, registry=APP_REGISTRY
)

BATTERY_VOLTAGE = prom.Gauge(
    "battery_voltage",
    "Battery voltage in volts",
    labelnames=LABEL_NAMES,
    registry=APP_REGISTRY,
)
BATTERY_PERCENTAGE = prom.Gauge(
    "battery_percentage",
    "Battery percentage remaining",
    labelnames=LABEL_NAMES,
    registry=APP_REGISTRY,
)


def avg(collection: List[float]) -> float:
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


@dataclass
class Settings:
    sensor_hourly_window: int = 12
    update_interval: int = 6


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

        temperature = [(t - 27315) / 100 for t in temp]
        humidity = [h / 2 for h in hum]
        pressure = [p / 50 for p in pres]
        x3 = [x / 256 for x in x3]

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

    def update_gauge(self, data: List[SensorValues]):
        labels = {"address": self.address, "serial": self.serial}

        RADON_AVG.labels(**labels).set(avg([d.radon for d in data]))
        TEMPERATURE_AVG.labels(**labels).set(avg([d.temperature for d in data]))
        HUMIDITY_AVG.labels(**labels).set(avg([d.humidity for d in data]))
        PRESSURE_AVG.labels(**labels).set(avg([d.pressure for d in data]))
        CO2_AVG.labels(**labels).set(avg([d.co2 for d in data]))
        VOC_AVG.labels(**labels).set(avg([d.voc for d in data]))
        AMBIANT_LIGHT_AVG.labels(**labels).set(avg([d.light for d in data]))
        X3_AVG.labels(**labels).set(avg([d.x3 for d in data]))
        X4_AVG.labels(**labels).set(avg([d.x4 for d in data]))


async def exporter(device: WavePlus, settings: Settings):
    try:
        hours = settings.sensor_hourly_window
        data = await device.get_hourly_sensor_data(hours)

        logger.info(f"Updating Prometheus gauges for {device.address}.")
        device.update_gauge(data)

        battery = await device.get_battery()
        if battery:
            labels = {"address": device.address, "serial": device.serial}
            BATTERY_VOLTAGE.labels(**labels).set(battery.voltage)
            BATTERY_PERCENTAGE.labels(**labels).set(battery.percentage)
            logger.info(f"Battery: {battery.voltage}V ({battery.percentage}%)")

    except (bleak.exc.BleakDBusError, bleak.exc.BleakError):
        logger.error(f"Failed to connect to device {device.address}!")
        return False

    except Exception as error:
        logger.error(f"Unhandled exception for {device.address}. {error}")
        return False

    return True


async def run_loop(args: argparse.Namespace):
    devices: List[WavePlus] = []
    for device_str in args.device:
        if "," not in device_str:
            logger.error(f"Invalid device format: {device_str}. Expected ADDRESS,SERIAL")
            sys.exit(1)
        address, serial = device_str.split(",", 1)
        devices.append(WavePlus.create(address.strip(), serial.strip()))

    settings = Settings(
        sensor_hourly_window=args.sensor_hourly_window,
        update_interval=args.update_interval,
    )

    logger.info(f"Starting Prometheus HTTP server on port {args.port}.")
    prom.start_http_server(args.port, registry=APP_REGISTRY)

    while True:
        for device in devices:
            attempt = False
            retries = 0
            while not attempt and retries < 5:
                logger.info(
                    f"Updating and exporting sensor values for {device.address}. "
                    f"Attempt ({retries}/5)"
                )
                attempt = await exporter(device, settings)
                retries += 1

        logger.info(f"Sleeping for {settings.update_interval} hours.")
        await asyncio.sleep(settings.update_interval * 60 * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prometheus exporter for Airthings Wave Plus."
    )
    parser.add_argument(
        "--device",
        action="append",
        required=True,
        metavar="ADDRESS,SERIAL",
        help="Bluetooth address and serial of a Wave Plus device. Can be given multiple times.",
    )
    parser.add_argument(
        "--sensor-hourly-window",
        type=int,
        default=12,
        help="How many hours of historical sensor data to pull. Default: 12",
    )
    parser.add_argument(
        "--update-interval",
        type=int,
        default=6,
        help="How often to poll devices, in hours. Default: 6",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the Prometheus HTTP server. Default: 8000",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(run_loop(args))


if __name__ == "__main__":
    main()
