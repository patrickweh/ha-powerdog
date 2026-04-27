# PowerAPI Integration for Home Assistant

This integration allows you to control and monitor PowerDog devices using the PowerAPI XML-RPC protocol.

## Features

- Automatic discovery of all sensors, counters, and regulations from your PowerDog device
- Display sensor readings with appropriate units
- Control regulations as switches or sliders
- Energy monitoring with daily, monthly, and yearly statistics
- Services to control counter values and meter readings

## Installation

### Manual Installation

1. Copy this directory into your Home Assistant's `custom_components` directory.
2. Restart Home Assistant.
3. Navigate to Configuration > Integrations.
4. Click on "Add Integration" and search for "PowerAPI".
5. Enter your PowerDog device's IP address and password (default is the Unlock Key).

## Configuration

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| host | The IP address of your PowerDog device | Required |
| password | The PowerAPI password (usually the Unlock Key) | Required |
| port | The port of the PowerAPI service | 20000 |
| scan_interval | How often to poll the device for updates (seconds) | 30 |

## Entity Types

The integration creates different entity types based on the PowerDog device:

### Sensors

- Regular sensors for all sensor devices (temperature, pressure, speed, etc.)
- Counter sensors with appropriate units and device classes
- Energy usage sensors for energy counters (daily, monthly, yearly)

### Switches

- On/Off controls for percent-based regulations

### Numbers

- Slider controls for variable percent-based regulations

## Services

### `powerapi.set_counter_value`

Sets a value and meter reading for a counter device.

| Parameter | Description | Required |
|-----------|-------------|----------|
| entity_id | The entity ID of the counter sensor | Yes |
| value | The value to set | Yes |
| meter_reading | The meter reading value (should be increasing) | Yes |

Example:
```yaml
service: powerapi.set_counter_value
data:
  entity_id: sensor.powerapi_test_counter
  value: "150.5"
  meter_reading: "10002"
```

## Troubleshooting

If you encounter issues with the integration:

1. Check that your PowerDog device is accessible on the network
2. Verify that the PowerAPI service is enabled on your PowerDog (available since version 1.60)
3. Confirm that you're using the correct password (default is the Unlock Key)
4. Check the Home Assistant logs for error messages

## API Documentation

This integration is based on the PowerAPI Local Device API. For more information, refer to the official documentation.

## Credits

This integration is based on the PowerAPI specifications from ecodata GmbH.