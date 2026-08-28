# HASS Daikin One Open API

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=CordMaster&repository=hass-daikin-one-open-api&category=Integration)

## What is this?

This is a simple cloud-polling integration that integrates Home Assistant with the [Daikin One Open API](https://www.daikinone.com/openapi/index.html) for (recent) Daikin, Amana, and Goodman thermostats.
It provides binary sensor, climate, select, sensor, and switch platforms for each thermostat.
Per their API specs, polling occurs every 3 minutes.

## Compatability

This integration is compatable with any thermostat listed [here](https://www.daikinone.com/openapi/overview/index.html).
In summary, it is compatable with select Daikin, Amana, and Goodman thermostats.

This has been confirmed to work with an Amana Smart Thermostat (ATST-CWE-BL-A) with a single unit.

Other units and multi-thermostat systems have not been tested yet.

## How do I use this?

1. Set up your thermostat in the `Skyport Home` app
2. Follow the steps [here](https://www.daikinone.com/openapi/documentation/index.html) to get an `Integrator Token` and an `API Token`.
3. Install this integration in your Home Assistant instance (either via HACS or by manually installing it in the `custom_components` directory).
4. Start the setup process in your Home Assistant instance. Provide:
    1. The email of your `Skyport Home` account (the one associated with your `API Token`).
    2. Your `Integrator Token`.
    3. Your `API Token`.
5. Select the devices you want to include in Home Assistant.
6. Enjoy!

## Special Thanks

* Special thanks to the Home Assistant team and Nabu Casa for their amazing products.
* Special thanks to the HACS team and maintainers.
* Special thanks to [ludeeus](https://github.com/ludeeus) for [integration_blueprint](https://github.com/ludeeus/integration_blueprint) from which this project was bootstrapped. See [TEMPLATE_LICENSE.md](TEMPLATE_LICENSE.md).

## Legal Notes

This project is not endorsed by Daikin. Any use of their brands is intended for identification only. All trademarks are property of their owners. Any issues with it should be reported here and not to them.

The brand icons are sourced from [https://github.com/home-assistant/brands](https://github.com/home-assistant/brands). The license is quoted below.

```
All product names, trademarks and registered trademarks in the images in this repository, are property of their respective owners. All images in this repository are used by the Home Assistant project for identification purposes only.

The use of these names, trademarks and brands appearing in these image files, do not imply endorsement.
```
