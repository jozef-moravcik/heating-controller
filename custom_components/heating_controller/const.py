"""The Heating Controller integration"""
"""Author: Jozef Moravcik"""
"""email: jozef.moravcik@moravcik.eu"""

""" const.py """

"""Constants for the Heating Controller integration."""
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNKNOWN, STATE_UNAVAILABLE, STATE_OK, STATE_PROBLEM

DOMAIN = "heating_controller"

# Services
SERVICE_SYSTEM_STARTED = "system_started"

# States and commands
STATE_NONE = "none"
STATE_FALSE = "false"
STATE_TRUE = "true"

TURN_ON = "turn_on" 
TURN_OFF = "turn_off"

STATE_OPEN = "open"
SWITCH_to_OPEN = "open_cover"

STATE_CLOSED = "closed"
SWITCH_to_CLOSE = "close_cover"

STATE_OPENING = "opening"
STATE_CLOSING = "closing"

STATE_HP_DHW = "closed"
SWITCH_HP_to_DHW = "close_cover"
STATE_HP_ACC = "open"
SWITCH_HP_to_ACC = "open_cover"

STATE_ACC_DHW = "closed"
SWITCH_ACC_to_DHW = "close_cover"
STATE_ACC_HEATING = "open"
SWITCH_ACC_to_HEATING = "open_cover"

# Configuration keys

# Načítanie základných konfiguračných parametrov
CONF_TIMEOUT_HEAT_DHW = "timeout_for_heat_dhw_from_acc"
CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW = "temperature_delta_limit_acc_dhw"
CONF_DISABLED_ACC_TEMPERATURE_LIMIT = "disabled_acc_temperature_limit"
CONF_MIN_TEMPERATURE_FOR_HEATING = "min_temperature_for_heating"
CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC = "temperature_delta_limit_in_acc"
CONF_HEATING_SOURCE_TEMP_HYSTERESIS = "heating_source_temp_hysteresis"
CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY = "heating_source_command_debounce_delay"
CONF_AUXILIARY_WATER_PUMP_FOR_HEATING = "auxiliary_water_pump_for_heating"
CONF_AUXILIARY_PUMP_BOOSTER_TIME = "auxiliary_pump_booster_time"

# Načítanie parametrov pre ovládanie ventilov
CONF_VALVE_OUTPUT_ACC_STRICT_MODE = "valve_output_acc_strict_mode"
CONF_VALVE_INPUT_ACC_STRICT_MODE = "valve_input_acc_strict_mode"
CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP = "valve_input_acc_closing_delay_when_heating_source_stop"
CONF_VALVE_TIMEOUT = "valve_timeout"

# Načítanie entít ventilov z konfigurácie
CONF_VALVE_FROM_TC_TO_ACC_OR_DHW = "valve_from_hp_to_acc_or_dhw"
CONF_VALVE_OUTPUT_ACC1 = "valve_output_acc1"
CONF_VALVE_OUTPUT_ACC2 = "valve_output_acc2"
CONF_VALVE_INPUT_ACC1 = "valve_input_acc1"
CONF_VALVE_INPUT_ACC2 = "valve_input_acc2"
CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW = "valve_from_acc_to_heat_or_dhw"
CONF_VALVE_OUTPUT_HEATING = "valve_output_heating"

# Načítanie entít teplotných senzorov z konfigurácie
CONF_SENSOR_TEMP_ACC1 = "sensor_temp_acc1"
CONF_SENSOR_TEMP_ACC2 = "sensor_temp_acc2"
CONF_SENSOR_TEMP_DHW = "sensor_temp_dhw"

# Načítanie entít obehových čerpadiel z konfigurácie
CONF_WATER_PUMP_ACC_OUTPUT = "water_pump_acc_output"
CONF_WATER_PUMP_DHW = "water_pump_dhw"
CONF_WATER_PUMP_FLOOR_HEATING = "water_pump_floor_heating"
CONF_WATER_PUMP_HEATING = "water_pump_heating"

# Načítanie entít stavov termostatov a tepelného čerpadla z konfigurácie
CONF_THERMOSTAT_STATE = "thermostat_state"
CONF_HEATING_STATE = "heating_state"
CONF_FLOOR_HEATING_STATE = "floor_heating_state"

# Internal entity names (will be prefixed with DOMAIN in code)
# These entities are created by this integration
ENTITY_ACC1_ENABLE = "acc1_enable"
ENTITY_ACC2_ENABLE = "acc2_enable"
ENTITY_HP_ACC = "hp_acc"
ENTITY_HP_DHW = "hp_dhw"
ENTITY_AUTOMATIC_MODE = "automatic_mode"
ENTITY_HEAT_DHW_FROM_ACC = "heat_dhw_from_acc"
ENTITY_DHW_TARGET_TEMPERATURE = "dhw_target_temperature"
ENTITY_ACC_TARGET_TEMPERATURE = "acc_target_temperature"
ENTITY_HEATING_OPERATING_MODE = "heating_operating_mode"
ENTITY_HEATING_SOURCE_ON_OFF = "heating_source_on_off"
ENTITY_CONTROL_COMMAND_HP_ON_OFF = "controll_command_hp_on_off"
ENTITY_CONTROL_COMMAND_HP_TEMPERATURE = "controll_command_hp_temperature"

# Default Values of External entities (Binary Sensors)
DEFAULT_ENTITY_THERMOSTAT_STATE = "binary_sensor.termostaty_stav"
DEFAULT_ENTITY_HEATING_STATE = "binary_sensor.kurenie_stav"
DEFAULT_ENTITY_FLOOR_HEATING_STATE = "binary_sensor.podlahove_kurenie_stav"

# Default Values of External entities (Temperature Sensors)
DEFAULT_ENTITY_TEMP_ACC1 = "sensor.cwt_temperature_sensor_01"
DEFAULT_ENTITY_TEMP_ACC2 = "sensor.cwt_temperature_sensor_04"
DEFAULT_ENTITY_TEMP_DHW = "sensor.cwt_temperature_sensor_07"

# Default Values of External entities (Valves)
DEFAULT_ENTITY_VALVE_FROM_TC_TO_ACC_OR_DHW = "cover.valve_1"
DEFAULT_ENTITY_VALVE_OUTPUT_ACC1 = "cover.valve_2"
DEFAULT_ENTITY_VALVE_OUTPUT_ACC2 = "cover.valve_3"
DEFAULT_ENTITY_VALVE_INPUT_ACC1 = "cover.valve_4"
DEFAULT_ENTITY_VALVE_INPUT_ACC2 = "cover.valve_5"
DEFAULT_ENTITY_VALVE_FROM_ACC_TO_HEAT_OR_DHW = "cover.valve_6"
DEFAULT_ENTITY_VALVE_OUTPUT_HEATING = "cover.valve_8"

# Default Values of External entities (Water Pumps)
DEFAULT_ENTITY_WATER_PUMP_ACC_OUTPUT = "switch.water_pump_1"
DEFAULT_ENTITY_WATER_PUMP_DHW = "switch.water_pump_2"
DEFAULT_ENTITY_WATER_PUMP_FLOOR_HEATING = "switch.water_pump_3"
DEFAULT_ENTITY_WATER_PUMP_HEATING = "switch.water_pump_4"

# Auxiliary water pump mode option constants
AUXILIARY_PUMP_DISABLE = 0
AUXILIARY_PUMP_ENABLE = 1
AUXILIARY_PUMP_BOOSTER = 2

# Options for auxiliary_pump
AUXILIARY_WATER_PUMP_OPTIONS = [
                                    AUXILIARY_PUMP_DISABLE,
                                    AUXILIARY_PUMP_ENABLE,
                                    AUXILIARY_PUMP_BOOSTER
                                ]

# Valve mode options constants
VALVE_MODE_GENERIC = 0
VALVE_MODE_MODERATE = 1
VALVE_MODE_STRICT = 2

# Options for valve strict modes (separate for output and input)
VALVE_OUTPUT_ACC_STRICT_MODE_OPTIONS = [
                                            VALVE_MODE_GENERIC,
                                            VALVE_MODE_MODERATE,
                                            VALVE_MODE_STRICT
                                        ]

VALVE_INPUT_ACC_STRICT_MODE_OPTIONS = [
                                            VALVE_MODE_GENERIC,
                                            VALVE_MODE_MODERATE,
                                            VALVE_MODE_STRICT
                                        ]

# Control Checks for valve open
VALVE_CONTROL_CHECKS_FOR_OPEN = [
                                    STATE_OPEN,
                                    STATE_OPENING,
                                    STATE_TRUE,
                                    STATE_FALSE,
                                    STATE_NONE,
                                    STATE_UNAVAILABLE,
                                    STATE_UNKNOWN
                                ]

# Control Checks for valve close
VALVE_CONTROL_CHECKS_FOR_CLOSE = [
                                    STATE_CLOSED,
                                    STATE_CLOSING,
                                    STATE_TRUE,
                                    STATE_FALSE,
                                    STATE_NONE,
                                    STATE_UNAVAILABLE,
                                    STATE_UNKNOWN
                                ]

# Heating operating mode option constants
HEATING_OPERATING_MODE_MANUAL = 0
HEATING_OPERATING_MODE_DHW = 1
HEATING_OPERATING_MODE_PDHW_DHW = 2
HEATING_OPERATING_MODE_ACC = 3
HEATING_OPERATING_MODE_PDHW_ACC = 4
HEATING_OPERATING_MODE_DHW_ACC = 5
HEATING_OPERATING_MODE_PDHW_DHW_ACC = 6

# Default values for select entities
DEFAULT_HEATING_OPERATING_MODE = HEATING_OPERATING_MODE_DHW_ACC

# Options for heating operating mode (key: value)
HEATING_OPERATING_MODE_OPTIONS = [
                                    HEATING_OPERATING_MODE_MANUAL,
                                    HEATING_OPERATING_MODE_DHW,
                                    HEATING_OPERATING_MODE_PDHW_DHW,
                                    HEATING_OPERATING_MODE_ACC,
                                    HEATING_OPERATING_MODE_PDHW_ACC,
                                    HEATING_OPERATING_MODE_DHW_ACC,
                                    HEATING_OPERATING_MODE_PDHW_DHW_ACC
                                ]


# Default values for number entities
DEFAULT_DHW_TARGET_TEMPERATURE = 50
DEFAULT_ACC_TARGET_TEMPERATURE = 50

# Default values of static parameters
DEFAULT_FALLBACK_CHECK_INTERVAL = 60
DEBOUNCE_DELAY = 0.2  # seconds - it groups all changes within this time period (due to better performance)

# Načítanie predvolených hodnôt základných konfiguračných parametrov
DEFAULT_TIMEOUT_HEAT_DHW = 60
DEFAULT_TEMPERATURE_DELTA_LIMIT_ACC_DHW = 2.0
DEFAULT_DISABLED_ACC_TEMPERATURE_LIMIT = 40
DEFAULT_MIN_TEMPERATURE_FOR_HEATING = 35
DEFAULT_TEMPERATURE_DELTA_LIMIT_IN_ACC = 2.0
DEFAULT_HEATING_SOURCE_TEMP_HYSTERESIS = 5
DEFAULT_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY = 20  # in seconds - it groups all changes within this time period
DEFAULT_AUXILIARY_WATER_PUMP_FOR_HEATING = AUXILIARY_PUMP_DISABLE
DEFAULT_AUXILIARY_PUMP_BOOSTER_TIME = 5  # in minutes

DEFAULT_VALVE_OUTPUT_ACC_STRICT_MODE = VALVE_MODE_STRICT
DEFAULT_VALVE_INPUT_ACC_STRICT_MODE = VALVE_MODE_STRICT
DEFAULT_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP = 3  # in minutes
DEFAULT_VALVE_TIMEOUT = 15

MAX_TEMPERATURE_LIMIT = 90

# Update interval
UPDATE_INTERVAL = 60  # in seconds
