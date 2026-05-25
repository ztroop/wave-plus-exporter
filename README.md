# Wave Plus Exporter

A Prometheus exporter for Airthings Wave Plus devices. It pulls historical sensor data over a configurable window to minimize battery drain from frequent BLE connections.

## Usage

```bash
python scripts/wave-exporter.py \
  --device AA:BB:CC:DD:EE:FF,1234567890 \
  --port 8000 \
  --update-interval 6
```

### Arguments

| Flag | Default | Description |
|---|---|---|
| `--device` | **required** | `ADDRESS,SERIAL` pair. Repeatable for multiple devices. |
| `--sensor-hourly-window` | `12` | Hours of historical data to fetch. |
| `--update-interval` | `6` | How often to poll, in hours. |
| `--port` | `8000` | Prometheus HTTP server port. |
