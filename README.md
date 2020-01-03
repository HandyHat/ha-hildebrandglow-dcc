# ha-hildebrandglow
HomeAssistant integration for the [Hildebrand Glow](https://www.hildebrand.co.uk/our-products/) smart meter HAN for UK SMETS meters.

Before using this integration, you'll need to have an active Glow account (usable through the Bright app) and API access enabled. If you haven't been given an API Application ID by Hildebrand, you'll need to contact them and request API access be enabled for your account.

This integration will currently emit one sensor for the current usage of each detected smart meter.

## Installation
### Automated installation through HACS
You can install this component through [HACS](https://hacs.xyz/) and receive automatic updates.

After installing HACS, visit the HACS _Settings_ pane and add `https://github.com/unlobito/ha-hildebrandglow` as an `Integration`. You'll then be able to install it through the _Integrations_ pane.

### Manual installation
Copy the `custom_components/hildebrandglow/` directory and all of its files to your ` config/custom_components` directory. You'll then need to restart Home Assistant for it to detect the new integration.

## Configuration
Visit the _Integrations_ section within Home Assistant's _Configuration_ panel and click the _Add_ button in the bottom right corner. After searching for "Hildebrand Glow", you'll be asked for your application ID and Glow credentials.

Once you've authenticated, the integration will automatically set up a sensor for each of the smart meters on your account.