# Raspberry Pi Balcony Irrigation Controller

Python code for my Raspberry Pi to control the watering of plants on my balcony.

## Prerequisites

Python 3:

    sudo apt-get install python3

Python [gpiozero library](http://gpiozero.readthedocs.io):

    sudo apt-get install python3-gpiozero

Python spidev library, which is needed for hardware accelerated SPI. It will also work without, but reading Soil Moisture sensors through an MCP3008 Analog-Digital Converter (ADC) will be a little slower (I measured 1.4ms instead of 0.04ms per reading):

    sudo apt-get install python3-spidev

Additionally the SPI kernel module will need to be enabled. Start the Raspberry Pi configuration tool with

    sudo raspi-config

and select `Advanced Options` and then `SPI`.

