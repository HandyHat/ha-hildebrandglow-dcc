# Hildebrand Glow (DCC) Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![CodeFactor Grade](https://img.shields.io/codefactor/grade/github/HandyHat/ha-hildebrandglow-dcc?style=for-the-badge)](https://www.codefactor.io/repository/github/handyhat/ha-hildebrandglow-dcc)
[![DeepSource](https://deepsource.io/gh/HandyHat/ha-hildebrandglow-dcc.svg/?label=active+issues&show_trend=true&token=gYN6CNb5ApHN5Pry_U-FFSYK)](https://deepsource.io/gh/HandyHat/ha-hildebrandglow-dcc/?ref=repository-badge)
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/HandyHat)

Home Assistant integration for energy consumption data from UK SMETS (Smart) meters using the Hildebrand Glow API.

This integration works without requiring a consumer device provided by Hildebrand Glow and can work with your existing smart meter. You'll need to set up your smart meter for free in the Bright app on [Android](https://play.google.com/store/apps/details?id=uk.co.hildebrand.brightionic&hl=en_GB) or [iOS](https://apps.apple.com/gb/app/bright/id1369989022). This will only work when using the Data Communications Company (DCC) backend, which all SMETS 2 meters and some SMETS 1 meters do ([more information](https://www.smartme.co.uk/technical.html)). Once you can see your data in the app, you are good to go.

The data provided will be delayed by around 30 minutes. To get real-time consumption data, you can buy [Hildebrand Glow hardware](https://shop.glowmarkt.com/). Although this integration will work with their hardware, you should use the MQTT version [here](https://github.com/unlobito/ha-hildebrandglow/tree/mqtt) to get real-time consumption data.

## Installation

### Automated installation through HACS

You can install this component through [HACS](https://hacs.xyz/) and receive automatic updates.

After installing HACS, visit the HACS _Integrations_ pane and add `https://github.com/HandyHat/ha-hildebrandglow-dcc` as an `Integration` by following [these instructions](https://hacs.xyz/docs/faq/custom_repositories/). You'll then be able to install it through the _Integrations_ pane.

### Manual installation

Copy the `custom_components/hildebrandglow_dcc/` directory and all of its files to your `config/custom_components` directory. You'll then need to restart Home Assistant for it to detect the new integration.

## Configuration

Visit the _Integrations_ section within Home Assistant's _Configuration_ panel and click the _Add_ button in the bottom right corner. After searching for "Hildebrand Glow", you'll be asked for your  Glow credentials.

Once you've authenticated to Glow, the integration will automatically set up the following sensors for each of the smart meters on your account.

### Electricity Sensors
- Electric Consumption (Today)

  Consumption today in kWh
- Electric Consumption (Year)

  Consumption for the year to date in kWh
- Electric Cost (Today)

  Cost in pence of electricity used today
- Electric Tariff Standing

  Todays standing charge for electricity (GBP)
- Electric Tariff Rate

  Current tariff in GBP/kWh
### GAS Sensors
- Gas Consumption (Today)

  Consumption today in kWh
- Gas Consumption (Year)

  Consumption for the year to date in kWh
- Gas Cost (Today)

  Cost in pence of GAS used today
- Gas Tariff Standing

  Todays standing charge for GAS (GBP)
- Gas Tariff Rate

  Current tariff in GBP/kWh

## HASS Energy Integration
The sensors created provide everything needed to integrate Electicity and GAS meter readings as well as costs into the HASS [Home Energy Management](https://www.home-assistant.io/docs/energy/).
It is recommended you use the yearly sensors in the Energy integration.

## Debugging

To debug the integration, add the following to your `configuration.yaml`

```yaml
logger:
  default: warning
  logs:
    custom_components.hildebrandglow_dcc: debug
```

## Development

To begin, it is recommended to create a virtual environment to install dependencies:

```bash
python -m venv dev-venv
. dev-venv\Scripts\activate
```

You can then install the dependencies that will allow you to develop:
`pip3 install -r requirements-dev.txt`

This will install `homeassistant`, `autopep8`, `isort` and `pylint`.

### Code Style

This project makes use of isort, pylint and autopep8 to enforce a consistent code style across the codebase.

## Credits

Thanks to the [original project](https://github.com/unlobito/ha-hildebrandglow) from which this project is forked, which now provides the MQTT interface, for realtime data via a Hildebrand device.

The Hildebrand API [documentation](https://docs.glowmarkt.com/GlowmarktAPIDataRetrievalDocumentationIndividualUserForBright.pdf) and [Swagger UI](https://api.beething.com/api-docs/v0-1/resourcesys/).

The [Hildebrand-Glow-Python-Library](https://github.com/ghostseven/Hildebrand-Glow-Python-Library) was great for understanding the API.
