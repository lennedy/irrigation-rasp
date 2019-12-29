from gpiozero import DigitalOutputDevice, Button, AnalogInputDevice, MCP3008

class MyButton(Button):
    def __init__(self, pin: int):
        super(MyButton, self).__init__(pin=pin, pull_up=True)

class Pump(DigitalOutputDevice):
    """
    A water pump controlled by a relay. It can be turned on() and off(). Initially it will be off.

    :param int pin:
        The GPIO pin (in BCM numbering) that the relay is connected to.

    :param boolean active_high:
        Whether the relay is active on high or low. Relays are usually active on low, therefore the default is False.
    """
    def __init__(self, pin: int, active_high: bool = False):
        super(Pump, self).__init__(pin=pin, active_high=active_high, initial_value=False)


class Valve:
    """
    A valve controlling the flow of water switched by a relay. It can be set to open() (water flowing) or close()
    (water blocked). Initially it will be closed.

    :param int pin:
        The GPIO pin (in BCM numbering) that the relay is connected to.

    :param bool active_high:
        Whether the relay is active on high or low. Relays are usually active on low, therefore the default is False.

    :param bool active_open:
        Set to True, when the Valve opens if power is turned on (relay active) (default). Set to False if the Valve
        opens if power is turned off (relay inactive).
    """
    def __init__(self, pin: int, active_high: bool = False, active_open: bool = True):
        self.active_open = active_open
        initial_value = not active_open  # initially closed
        self._relay = DigitalOutputDevice(pin=pin, active_high=active_high, initial_value=initial_value)

    def open(self):
        self._relay.value = self.active_open

    def close(self):
        self._relay.value = not self.active_open

    @property
    def is_open(self) -> bool:
        if self.active_open:
            return self._relay.value
        else:
            return not self._relay.value

    @property
    def is_closed(self):
        return not self.is_open


class MoistureSensor:
    """
    A moisture sensor connected to an Analog-Digital-Converter (ADC) chip.

    :param AnalogInputDevice input_device:
        The input channel of your ADC-chip, e.g. MCP3008(channel=0)
        Have a look at the documentation of gpiozero for a list of all available ADC chips and their parameters:
        http://gpiozero.readthedocs.io/en/latest/api_spi.html

    :param bool inverse:
        If the moisture sensor is 0 when dry then set to False (default), if it is 1 when dry then set to True.
    """
    def __init__(self, input_device: AnalogInputDevice, inverse: bool = False):
        self.input_device = input_device
        self.inverse = inverse

    @property
    def value(self) -> float:
        if self.inverse:
            return 1 - self.input_device.value
        else:
            return self.input_device.value


class FloatSwitch:
    """
    A binary float switch to measure the water level in a water tank.

    It can be either wet (under water) or dry (above water).

    Connect one side of the switch to a ground pin, and the other to any GPIO
    pin. Alternatively, connect one side of the switch to a 3V3 pin, and the
    other to any GPIO pin, then set *pull_up* to ``False`` in the constructor.

    :param int pin:
        The GPIO pin (in BCM numbering) the switch is connected to.

    :param int height:
        The installation height of the float switch within the water tank specified as a value between 0 and 100.
        0 is the very bottom of the tank and 100 the top of the tank. (Consequently 50 is the middle of the tank.)

    :param bool active_wet:
        Set to True if the active state (switch closed) means that the switch is under water (wet).
        Set to False (default) if the active state (switch closed) means that the switch is above water (dry).

    :param bool pull_up:
        If ``True`` (the default), the GPIO pin will be pulled high by default.
        In this case, connect the other side of the switch to ground. If
        ``False``, the GPIO pin will be pulled low by default. In this case,
        connect the other side of the button to 3V3.
    """
    def __init__(self, pin: int, height: int, active_wet: bool = False, pull_up: bool = True):
        self._switch = Button(pin=pin, pull_up=pull_up)
        self.active_wet = active_wet
        self.height = height

    def is_wet(self) -> bool:
        return self._switch.is_active if self.active_wet else not self._switch.is_active

    def is_dry(self) -> bool:
        return not self.is_wet()


class WaterLevel:
    """
    Determines the water level in a tank by combining the values of multiple float switches, that are installed at
    different heights in the tank.

    :param Sequence[FloatSwitch] float_switches:
        List of float switches.
    """
    def __init__(self, float_switches: list):
        self.float_switches = sorted(float_switches, key=lambda s: s.height)

    @property
    def value(self) -> float:
        """
        :return:
            value from 0 to 100 specifying the approximated amount of water left in the tank. 0 means that the tank is
            empty. 100 means it is full.
            Examples:
                - If all switches are dry, then 0 will be returned.
                - If a switch installed at height 100 is wet, then 100 will be returned.
                - If a switch installed at height 0 is wet and the next switch installed at height 20 is dry, then 10
                will be returned (the mean).
                - If a switch installed at height 25 is wet and the next switch installed at height 75 is dry, then 50
                will be returned (the mean).
                - If a switch installed at height 50 is wet and the next switch installed at height 100 is dry, then 75
                will be returned (the mean).
                - If a switch installed at height 60 is wet and there is no higher switch, then 80 will be returned (the
                mean of 60 and 100).
        """
        if self.float_switches[0].is_dry():
            return 0

        highest_wet = 0
        lowest_dry = 100
        for float_switch in self.float_switches:
            if float_switch.is_wet():
                highest_wet = float_switch.height
            else:
                lowest_dry = float_switch.height
                break
        return (lowest_dry + highest_wet) / 2

    @property
    def float_switch_values(self):
        return [{"height": float_switch.height, "wet": float_switch.is_wet()} for float_switch in self.float_switches]


class CPUTemperature:
    """
    Reads the CPU temperature of the Raspberry Pi
    """

    def get_temperature(self) -> float:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as temperature_file:
            return float(temperature_file.read()) / 1000
