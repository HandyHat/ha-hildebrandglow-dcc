# Hildebrand Glow (DCC) Integration

## Fork
Fork of orignal repo.
Added support for tarif data and metric sensors


[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![CodeFactor Grade](https://img.shields.io/codefactor/grade/github/HandyHat/ha-hildebrandglow-dcc?style=for-the-badge)](https://www.codefactor.io/repository/github/handyhat/ha-hildebrandglow-dcc)
[![DeepSource](https://deepsource.io/gh/HandyHat/ha-hildebrandglow-dcc.svg/?label=active+issues&show_trend=true&token=gYN6CNb5ApHN5Pry_U-FFSYK)](https://deepsource.io/gh/HandyHat/ha-hildebrandglow-dcc/?ref=repository-badge)
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/HandyHat)

Home Assistant integration for energy consumption data from UK SMETS (Smart) meters using the Hildebrand Glow API.

This integration works without requiring a consumer device provided by Hildebrand Glow and can work with your existing smart meter. You'll need to set up your smart meter for free in the Bright app on [Android](https://play.google.com/store/apps/details?id=uk.co.hildebrand.brightionic&hl=en_GB) or [iOS](https://apps.apple.com/gb/app/bright/id1369989022). This will only work when using the Data Communications Company (DCC) backend, which all SMETS 2 meters and some SMETS 1 meters do ([more information](https://www.smartme.co.uk/technical.html)). Once you can see your data in the app, you are good to go.

The data provided will be delayed by around 30 minutes. To get real-time consumption data, you can buy [Hildebrand Glow hardware](https://shop.glowmarkt.com/). Although this integration will work with their hardware, you should use the MQTT version [here](https://github.com/unlobito/ha-hildebrandglow/tree/mqtt) to get real-time consumption data.

This integration will currently emit one sensor for the daily usage of each detected smart meter.

## Installation

### Automated installation through HACS

You can install this component through [HACS](https://hacs.xyz/) and receive automatic updates.

After installing HACS, visit the HACS _Integrations_ pane and add `https://github.com/HandyHat/ha-hildebrandglow-dcc` as an `Integration` by following [these instructions](https://hacs.xyz/docs/faq/custom_repositories/). You'll then be able to install it through the _Integrations_ pane.

### Manual installation

Copy the `custom_components/hildebrandglow_dcc/` directory and all of its files to your `config/custom_components` directory. You'll then need to restart Home Assistant for it to detect the new integration.

## Configuration

Visit the _Integrations_ section within Home Assistant's _Configuration_ panel and click the _Add_ button in the bottom right corner. After searching for "Hildebrand Glow", you'll be asked for your  Glow credentials.

Once you've authenticated, the integration will automatically set up a sensor for each of the smart meters on your account.

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

Thanks to the [original project](https://github.com/unlobito/ha-hildebrandglow) from which this project is forked, and to [this python library](https://github.com/ghostseven/Hildebrand-Glow-Python-Library) for helping me troubleshoot.
