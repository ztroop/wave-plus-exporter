# Wave Plus Exporter

A simple exporter for `Prometheus` to periodically pull sensor data over an extended period of time. A problem I've noticed while trying to read _current values_ from the device every  hour, is that it has a significant effect over battery life. The code in this script will make use of _historical_ data over an extended period of time.

## Environment

The following environment variables can configure and override the script's defaults.
- `READING_WINDOW` : How far back to pull historical data. Default: 12 (hours)
- `UPDATE_DELAY` : How often to update the Guage values for Prometheus. Default: 12 (hours)
- `EXPORTER_PORT` : The port to listen on.

## Example Usage

```
# Takes two arguments, address and serial:
python exporter.py 80:6F:B0:XX:YY:ZZ 2930123456
```