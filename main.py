#!/usr/bin/env python3

from time import sleep, time
from pprint import pformat
from statistics import median
import json
import requests
import logging
import signal, os
from signal import pause

logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.WARNING)
logger = logging.getLogger('oh-balcony')
logger.setLevel(logging.INFO)

try:
    from config import *
except ImportError as err:
    print("The configuration file config.py does not exist. Have a look at config.sample.py for reference. (" +
          str(err) + ")")
    exit(1)



def main():
    print("Oh, Balcony!")

    all_off()

    global measure_interval
    global moisture_values
    global temperature_values
    global values_count
    global button_pressed

		# time between two measurements (seconds)
    measure_interval = send_measurements_interval / aggregated_measurements_count

    print("Measuring every", measure_interval, "seconds, aggregating", aggregated_measurements_count,
          "values and sending them to the server every", send_measurements_interval, "seconds.")

    moisture_values = {moistureSensorName: [] for moistureSensorName in moisture_sensors.keys()}
    temperature_values = {temperatureSensorName: [] for temperatureSensorName in temperature_sensors.keys()}
    values_count = 0

    button_pressed = False
    buttons["button1"].when_pressed = pressedButton1
    buttons["button2"].when_pressed = pressedButton2
    buttons["button3"].when_pressed = pressedButton3
    buttons["button4"].when_pressed = pressedButton4

    signal.signal(signal.SIGALRM, loop)
    signal.alarm(int(send_measurements_interval))

    while True:
      signal.pause()
    signal.alarm(0)

def loop(signum, frame):
  global measure_interval
  global moisture_values
  global temperature_values
  global values_count
  
  start_time = time()
  measure_moisture(moisture_values)
  measure_temperature(temperature_values)
  values_count += 1
  if values_count >= aggregated_measurements_count:
      values_count = 0
      aggregated_moisture_values = aggregate_values(moisture_values)
      aggregated_temperature_values = aggregate_values(temperature_values)
      clear_values_map(moisture_values)
      clear_values_map(temperature_values)
      store_and_change_state(aggregated_moisture_values, aggregated_temperature_values)
  processing_time = time() - start_time
  sleep_time = max(measure_interval - processing_time, 0)
  signal.alarm(int(sleep_time))

def pressedButton1():
  global button_pressed
  button_pressed=True

  logger.info("Open valve1 button")
  valves["valve1"].open();

def pressedButton2():
  global button_pressed
  button_pressed=True

  logger.info("Open valve2 button")
  valves["valve2"].open();
  sleep(2)
  pumps["pump1"].on()

def pressedButton3():
  global button_pressed
  button_pressed=True

  logger.info("Open valve3 button")
  valves["valve3"].open();
  sleep(2)
  pumps["pump1"].on()

def pressedButton4():
  global button_pressed
  button_pressed=True

  logger.info("TurnOff button")
  pumps["pump1"].off()
  sleep(2)
  valves["valve1"].close();
  valves["valve2"].close();
  valves["valve3"].close();


def all_off():
    for pump in pumps.values():
        pump.off()

    for valve in valves.values():
        valve.close()


def measure_moisture(moisture_values):
    for name, sensor in moisture_sensors.items():
        value = sensor.value
        moisture_values[name].append(value)


def measure_temperature(temperature_values):
    for name, sensor in temperature_sensors.items():
        value = 0
        try:
            value = sensor.get_temperature()
        except:
            logger.exception("Error reading temperature sensor")
        temperature_values[name].append(value)


def aggregate_values(values_map):
    return {name: median(values) for name, values in values_map.items()}


def clear_values_map(values_map):
    for values in values_map.values():
        del values[:]


def store_and_change_state(aggregated_moisture_values, aggregated_temperature_values):
    global button_pressed

    water_level_values = {name: water_level.value for name, water_level in water_levels.items()}
    pump_values = {name: pump.is_active for name, pump in pumps.items()}
    valve_values = {name: valve.is_open for name, valve in valves.items()}

    pump_val = [{"id":name, "isActive":pump.is_active} for name, pump in pumps.items()]
    valve_val = [{"id":name, "isOpen":valve.is_open} for name, valve in valves.items()]

    if button_pressed:
      pl = {"pumps": pump_val,
            "valves": valve_val}
      send_pump_valve_value(pl)

    payload = {"moisture": aggregated_moisture_values,
               "temperature": aggregated_temperature_values,
               "tanks": water_level_values,
               "pumps": pump_values,
               "valves": valve_values}

    # debugging output for float switches
    for name, water_level in water_levels.items():
        logger.info(name + ": " + pformat(water_level.float_switch_values))

    logger.info("Send: " + pformat(payload))

    instructions = send_and_get_instructions(payload)

    logger.info("Receive: " + pformat(instructions))

    pump_instructions = instructions["pumps"]
    valve_instructions = instructions["valves"]

    for name, pump in pumps.items():
        if name in pump_instructions and pump_instructions[name]:
            pump.on()
        else:
            pump.off()

    for name, valve in valves.items():
        if name in valve_instructions and valve_instructions[name]:
            valve.open()
        else:
            valve.close()

    for name, state in instructions["pumps"].items():
        if name not in pumps:
            logger.error("Ignoring instructions for unknown pump " + name)
    for name, state in instructions["valves"].items():
        if name not in valves:
            logger.error("Ignoring instructions for unknown valve " + name)


def send_and_get_instructions(payload):
    headers = {'content-type': 'application/json'}
    instructions = {"pumps": {}, "valves": {}}  # default: all off/closed
    try:
        response = requests.post(get_service_endpoint("updateControllerState/" + controller_name), data=json.dumps(payload), headers=headers, timeout=5.0)
        response.raise_for_status()

        instructions = response.json()
    except:
        logger.exception("Communication error with server")
    return instructions


def get_service_endpoint(endpoint):
    if service_base_url.endswith("/"):
        return service_base_url + endpoint
    else:
        return service_base_url + "/" + endpoint

def send_pump_valve_value(payload):
  headers = {'content-type': 'application/json'}

  try:
##    print(get_service_endpoint("updateActuators/"))
##  data=json.dumps(payload)
    logger.info("Pump e Valve: " + pformat(payload))
##    print(data)
#    print("************************************")
    #data=json.dumps(payload)
    response = requests.post(get_service_endpoint("updateActuators"), data=json.dumps(payload), headers=headers, timeout=5.0)
    #response.raise_for_status()

  except:
    logger.exception("Communication error with server")


main()
