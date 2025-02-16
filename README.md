# PowerDog Home Assistant Integration

This is a custom integration for Home Assistant that enables communication with PowerDog energy management systems. The integration provides access to PowerDog devices, including sensors, switches, and climate controls, allowing you to monitor and manage your energy system directly from Home Assistant.

## Features
- Fetch real-time energy consumption and production data.
- Control and monitor PowerDog-regulated devices.
- Full integration with Home Assistant's entity model.

## Installation via HACS
To install this integration via [HACS](https://hacs.xyz/), follow these steps:

1. Open Home Assistant and navigate to **HACS**.
2. Go to **Integrations** and click the three-dot menu in the top-right corner.
3. Select **Custom repositories**.
4. Add the following repository:
   ```
   https://github.com/patrickweh/ha-powerdog
   ```
    - Category: **Integration**
5. Click **Add** and then **Close**.
6. Search for "PowerDog" in HACS Integrations and install it.
7. Restart Home Assistant.

## Manual Installation
If you prefer manual installation:
1. Download the latest release from the [GitHub repository](https://github.com/patrickweh/ha-powerdog).
2. Copy the `powerdog` folder into your `custom_components` directory in Home Assistant.
3. Restart Home Assistant.

## Configuration
1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for "PowerDog".
3. Enter your PowerDog connection details (IP address, credentials, etc.).
4. Follow the setup wizard to configure your devices.

## Usage
Once configured, the PowerDog entities will appear in Home Assistant. You can:
- View real-time power usage.
- Automate energy management based on PowerDog data.
- Control PowerDog-compatible devices through Home Assistant.

## Icons & Logos
This integration includes icons and logos for PowerDog. These are used for visual representation in Home Assistant.

## Support
If you encounter any issues, feel free to open an issue in the [GitHub repository](https://github.com/patrickweh/ha-powerdog/issues).

## License
This integration is released under the MIT License.

---
💡 **Contributions are welcome!** If you have improvements, feel free to submit a PR. 🚀

