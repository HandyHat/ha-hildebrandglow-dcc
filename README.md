# This fork has been moved to https://github.com/HandyHat/ha-hildebrandglow-dcc

# Hildebrand Glow (DCC) Integration

Home Assistant integration for energy consumption data from UK SMETS (Smart) meters using the Hildebrand Glow API.

This integration works without requiring a consumer device provided by Hildebrand Glow and can work with your existing smart meter. You'll need to set up your smart meter for free in the Bright app on [Android](https://play.google.com/store/apps/details?id=uk.co.hildebrand.brightionic&hl=en_GB) or [iOS](https://apps.apple.com/gb/app/bright/id1369989022). This will only work when using the Data Communications Company (DCC) backend, which all SMETS 2 meters and some SMETS 1 meters do ([more information](https://www.smartme.co.uk/technical.html)). Once you can see your data in the app, you are good to go.

If you are using [Hildebrand Glow hardware](https://shop.glowmarkt.com/), you should use the MQTT version [here](https://github.com/unlobito/ha-hildebrandglow/tree/mqtt) to get current consumption data.

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

## Development

Run `pip install -r requirements-dev.txt` to install the development requirements.

### Code Style

This project makes use of isort, pylint and autopep8 to enforce a consistent code style across the codebase.
