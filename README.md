# Wave Plus Exporter

A simple exporter for `Prometheus` to periodically pull sensor data over an extended period of time. A problem I've noticed while trying to read _current values_ from the device every hour, is that it has a significant effect over battery life. The code in this script will make use of _historical_ data over an extended period of time.

## Environment

The following environment variables can configure and override the script's defaults.
- `SensorHourlyWindow` : How far back to pull historical data. Default: 12 (hours)
- `HourlyUpdateDelay` : How often to update the Guage values for Prometheus. Default: 6 (hours)
- `RadonThreshold` : The threshold to send notifications. Default: 99.9
- `ListeningPort` : The port to listen on. Default: 8000
- `PhoneEnabled` : Whether or not to enable phone notificaitons. Default: 0
- `PhoneNumber` : Number to receive the notification. Default: 0
- `DeviceAddress` : The address of the Wave device.
- `DeviceSerial` : The serial of the Wave device.
- `TwilioAccountSID` : The Twilio SID to use.
- `TwilioToken` : The Twilio Token to use.
- `TwilioSender` : The Twilio phone number to send from.

The configuration file, `wave.ini`, is loaded from either `/etc/wave/wave.ini` or `$HOME/.config/wave.ini`. See `sample.ini` for example.

## Example Usage

```
python scripts/wave-exporter.py
```