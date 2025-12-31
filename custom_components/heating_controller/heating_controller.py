from __future__ import annotations
"""The Heating Controller integration"""
"""Author: Jozef Moravcik"""
"""email: jozef.moravcik@moravcik.eu"""

""" heating_controller.py """

"""Coordinator for Heating Controller integration."""

from datetime import timedelta
import logging
import struct
import dataclasses
import json
import asyncio
import time

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.dispatcher import async_dispatcher_send
#from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNKNOWN, STATE_UNAVAILABLE, STATE_OK, STATE_PROBLEM
from .const import *

LOGGER = logging.getLogger(__name__)

class Heating_Controller_Instance:

    def __init__(self) -> None:
#        self._Data = self.Data()
        self.settings = self.Settings()
        self._is_running = False

        self.hass = None
        self._entry_id = None # Budete potrebovat ulozit entry_id aj sem
        # Ukladaci priestor pre stavy senzorov
        self.sensor_states = {
            ENTITY_CONTROL_COMMAND_HP_TEMPERATURE: None,
            ENTITY_CONTROL_COMMAND_HP_ON_OFF: None,
        }

        self.SWITCH_ENTITY_AUTOMATIC_MODE = f"switch.{DOMAIN}_{ENTITY_AUTOMATIC_MODE}"
        self.SWITCH_ENTITY_ACC1_ENABLE = f"switch.{DOMAIN}_{ENTITY_ACC1_ENABLE}"
        self.SWITCH_ENTITY_ACC2_ENABLE = f"switch.{DOMAIN}_{ENTITY_ACC2_ENABLE}"
        self.SWITCH_ENTITY_HEAT_DHW_FROM_ACC = f"switch.{DOMAIN}_{ENTITY_HEAT_DHW_FROM_ACC}"
        self.SWITCH_ENTITY_HP_ACC = f"switch.{DOMAIN}_{ENTITY_HP_ACC}"
        self.SWITCH_ENTITY_HP_DHW = f"switch.{DOMAIN}_{ENTITY_HP_DHW}"
        self.SWITCH_ENTITY_HEATING_SOURCE_ON_OFF = f"switch.{DOMAIN}_{ENTITY_HEATING_SOURCE_ON_OFF}"
        self.SENSOR_ENTITY_CONTROL_COMMAND_HP_ON_OFF = f"sensor.{DOMAIN}_{ENTITY_CONTROL_COMMAND_HP_ON_OFF}"
        self.SENSOR_ENTITY_CONTROL_COMMAND_HP_TEMPERATURE = f"sensor.{DOMAIN}_{ENTITY_CONTROL_COMMAND_HP_TEMPERATURE}"
        self.NUMBER_ENTITY_DHW_TARGET_TEMPERATURE = f"number.{DOMAIN}_{ENTITY_DHW_TARGET_TEMPERATURE}"
        self.NUMBER_ENTITY_ACC_TARGET_TEMPERATURE = f"number.{DOMAIN}_{ENTITY_ACC_TARGET_TEMPERATURE}"
        self.SELECT_ENTITY_HEATING_OPERATING_MODE = f"select.{DOMAIN}_{ENTITY_HEATING_OPERATING_MODE}"
        
        self.SWITCH_ENTITY_WATER_PUMP_ACC_OUTPUT = ""
        self.SWITCH_ENTITY_WATER_PUMP_DHW = ""
        self.SWITCH_ENTITY_WATER_PUMP_FLOOR_HEATING = ""
        self.SWITCH_ENTITY_WATER_PUMP_HEATING = ""

        self.hp_acc = True
        self.hp_dhw = False
        self.heating_source_input_on_off = False

        self.preferred_output_ACC = 0
        self.preferred_input_ACC = 0
        self.controll_command_hp_on_off = 0

        self.valve_from_hp_to_acc_or_dhw_flag = 1
        self.valve_output_acc1_flag = 0
        self.valve_output_acc2_flag = 0
        self.valve_input_acc1_flag = 0
        self.valve_input_acc2_flag = 0
        self.valve_from_acc_to_heat_or_dhw_flag = 1
        self.valve_output_heating_flag = 1
        
        self.water_pump_acc_output_flag = 0
        self.water_pump_dhw_flag = 0
        self.water_pump_floor_heating_flag = 0
        self.water_pump_heating_flag = 0

        # Debounce timestamps pre ventily (čas posledného príkazu)
        self._valve_last_command_time = {
            CONF_VALVE_FROM_TC_TO_ACC_OR_DHW: 0,
            CONF_VALVE_OUTPUT_ACC1: 0,
            CONF_VALVE_OUTPUT_ACC2: 0,
            CONF_VALVE_INPUT_ACC1: 0,
            CONF_VALVE_INPUT_ACC2: 0,
            CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW: 0,
            CONF_VALVE_OUTPUT_HEATING: 0,
        }
        self._scheduled_rerun = None  # Naplánovaný rerun kontrolného cyklu
        self._auxiliary_pump_booster_timer = None  # Časovač pre booster režim auxiliary pump
        self._auxiliary_pump_booster_active = False  # Príznak či je booster aktívny (timer beží)
        self._auxiliary_pump_booster_finished = False  # Príznak či booster už prebehol (timer vypršal)
        self._hp_on_off_debounce_timer = None  # Časovač pre debounce HP ON/OFF príkazu
        self._hp_on_off_pending_value = None  # Očakávaná hodnota po uplynutí debounce
        self._valve_input_acc_closing_delay_timer = None  # Časovač pre oneskorené zatvorenie ventilov na vstupoch do ACC
        self._valve_input_acc_closing_allowed = True  # Príznak či je povolené zatvorenie ventilov (po vypršaní časovača)
        self._previous_controll_command_hp_on_off = 0  # Predchádzajúci stav príkazu pre TČ
        self._hp_dhw_to_acc_delay_timer = None  # Časovač pre oneskorené pretočenie ventilu hp_dhw z TUV na ACC
        self._hp_dhw_to_acc_switch_allowed = True  # Príznak či je povolené pretočenie ventilu (po vypršaní časovača)
        
        self.preferred_output_ACC = 0
        self.preferred_input_ACC = 0
        self.higher_temperature_acc_value = 0
        self.lower_temperature_acc_value = 0

        self.heating_source_auto_on_off = False
        self.heating_operating_mode = HEATING_OPERATING_MODE_MANUAL
        self.heating_operating_mode_previous = HEATING_OPERATING_MODE_MANUAL
        self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

        self.temperature_setpoint = 0
        
    @dataclasses.dataclass
    class Settings:
        # Nastavenie statických parametrov
        fallback_check_interval = DEFAULT_FALLBACK_CHECK_INTERVAL

        # === Nastavenia dynamických parametrov ===

        # Základné konfiguračné parametre
        timeout_for_heat_dhw_from_acc: int = DEFAULT_TIMEOUT_HEAT_DHW
        temperature_delta_limit_acc_dhw: float = DEFAULT_TEMPERATURE_DELTA_LIMIT_ACC_DHW
        disabled_acc_temperature_limit: int = DEFAULT_DISABLED_ACC_TEMPERATURE_LIMIT
        min_temperature_for_heating: int = DEFAULT_MIN_TEMPERATURE_FOR_HEATING
        temperature_delta_limit_in_acc: float = DEFAULT_TEMPERATURE_DELTA_LIMIT_IN_ACC
        heating_source_temp_hysteresis: float = DEFAULT_HEATING_SOURCE_TEMP_HYSTERESIS
        heating_source_command_debounce_delay: int = DEFAULT_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY
        auxiliary_water_pump_for_heating: int = DEFAULT_AUXILIARY_WATER_PUMP_FOR_HEATING
        auxiliary_pump_booster_time: int = DEFAULT_AUXILIARY_PUMP_BOOSTER_TIME
        # Konfiguračné parametre pre ovládanie ventilov
        valve_output_acc_strict_mode: int = DEFAULT_VALVE_OUTPUT_ACC_STRICT_MODE
        valve_input_acc_strict_mode: int = DEFAULT_VALVE_INPUT_ACC_STRICT_MODE
        valve_input_acc_closing_delay_when_heating_source_stop: int = DEFAULT_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP
        valve_timeout: int = DEFAULT_VALVE_TIMEOUT
        # Entity ventilov
        entity_valve_from_hp_to_acc_or_dhw = DEFAULT_ENTITY_VALVE_FROM_TC_TO_ACC_OR_DHW
        entity_valve_output_acc1 = DEFAULT_ENTITY_VALVE_OUTPUT_ACC1
        entity_valve_output_acc2 = DEFAULT_ENTITY_VALVE_OUTPUT_ACC2
        entity_valve_input_acc1 = DEFAULT_ENTITY_VALVE_INPUT_ACC1
        entity_valve_input_acc2 = DEFAULT_ENTITY_VALVE_INPUT_ACC2
        entity_valve_from_acc_to_heat_or_dhw = DEFAULT_ENTITY_VALVE_FROM_ACC_TO_HEAT_OR_DHW
        entity_valve_output_heating = DEFAULT_ENTITY_VALVE_OUTPUT_HEATING
        # Entity teplotných senzorov
        entity_temp_acc1 = DEFAULT_ENTITY_TEMP_ACC1
        entity_temp_acc2 = DEFAULT_ENTITY_TEMP_ACC2
        entity_temp_dhw = DEFAULT_ENTITY_TEMP_DHW
        # Entity obehových čerpadiel
        entity_water_pump_acc_output = DEFAULT_ENTITY_WATER_PUMP_ACC_OUTPUT
        entity_water_pump_dhw = DEFAULT_ENTITY_WATER_PUMP_DHW
        entity_water_pump_floor_heating = DEFAULT_ENTITY_WATER_PUMP_FLOOR_HEATING
        entity_water_pump_heating = DEFAULT_ENTITY_WATER_PUMP_HEATING
        # Entity stavov termostatov a tepelného čerpadla
        entity_thermostat_state = DEFAULT_ENTITY_THERMOSTAT_STATE
        entity_heating_state = DEFAULT_ENTITY_HEATING_STATE
        entity_floor_heating_state = DEFAULT_ENTITY_FLOOR_HEATING_STATE

# ******************************************************************************************
# ************************ System Started (initial functions) ******************************
# ******************************************************************************************

    def system_started(self) -> None:
        try:
            LOGGER.debug(f"System Started")
        except Exception as e:
            LOGGER.error(f"Error during System Started")

# ******************************************************************************************
# ********************** Heating Controller ************************************************
# ******************************************************************************************

    async def heating_control_system(self):
        """Main heating control system logic."""
        LOGGER.debug("=== HEATING CONTROL SYSTEM START ===")
        
        # Mode: single - prevent concurrent runs
        if self._is_running:
            LOGGER.debug("Already running, skipping this cycle")
            return
        
        self._is_running = True

# ******************************************************************************************
# ********************** LOAD CONFIGURATION ************************************************
# ******************************************************************************************

        try:
            LOGGER.debug("Cycle started")

        # Get INTERNAL ENTITIES states (Internal Entities created by this integration, Entity IDs are generated from entity names, not unique_ids)
            try:
                automatic_mode = self.hass.states.is_state(self.SWITCH_ENTITY_AUTOMATIC_MODE, STATE_ON)
                acc1_enable = self.hass.states.is_state(self.SWITCH_ENTITY_ACC1_ENABLE, STATE_ON)
                acc2_enable = self.hass.states.is_state(self.SWITCH_ENTITY_ACC2_ENABLE, STATE_ON)
                self.heat_dhw_from_acc = self.hass.states.is_state(self.SWITCH_ENTITY_HEAT_DHW_FROM_ACC, STATE_ON)
                self.hp_acc = self.hass.states.is_state(self.SWITCH_ENTITY_HP_ACC, STATE_ON)
                self.hp_dhw = self.hass.states.is_state(self.SWITCH_ENTITY_HP_DHW, STATE_ON)
                self.heating_source_input_on_off = self.hass.states.is_state(self.SWITCH_ENTITY_HEATING_SOURCE_ON_OFF, STATE_ON)
                dhw_target_temperature = float(self.hass.states.get(self.NUMBER_ENTITY_DHW_TARGET_TEMPERATURE).state)
                acc_target_temperature = float(self.hass.states.get(self.NUMBER_ENTITY_ACC_TARGET_TEMPERATURE).state)
                self.heating_operating_mode = int(self.hass.states.get(self.SELECT_ENTITY_HEATING_OPERATING_MODE).state)
                
                LOGGER.debug("ENTITY %s, %s, %s, %s, %s, %s, %s", self.SWITCH_ENTITY_AUTOMATIC_MODE, self.SWITCH_ENTITY_ACC1_ENABLE, self.SWITCH_ENTITY_ACC2_ENABLE, self.SWITCH_ENTITY_HEAT_DHW_FROM_ACC, self.SWITCH_ENTITY_HP_ACC, self.SWITCH_ENTITY_HP_DHW, self.SWITCH_ENTITY_HEATING_SOURCE_ON_OFF)

                LOGGER.debug("Internal Entity States: automatic_mode=%s, acc1_enable=%s, acc2_enable=%s, self.hp_acc=%s, self.hp_dhw=%s, self.heat_dhw_from_acc=%s, self.heating_source_input_on_off=%s, dhw_target_temperature=%s, acc_target_temperature=%s, self.heating_operating_mode=%s",
                            automatic_mode, acc1_enable, acc2_enable, self.hp_acc, self.hp_dhw, self.heat_dhw_from_acc, self.heating_source_input_on_off, dhw_target_temperature, acc_target_temperature, self.heating_operating_mode)


                LOGGER.debug("XXXXXXXXX AAA - valve_input_acc_closing_delay_when_heating_source_stop=%s", self.settings.valve_input_acc_closing_delay_when_heating_source_stop)

            except Exception as e:
                LOGGER.error(f"Failed to load entities created by this integration. Error details: {e}")
                return

        # Get EXTERNAL ENTITIES states (External Entities defined by user in the configuration of this integration)

        # **** Get temperature sensor entities **************************************************************
            try:
                temperature_acc1 = self.hass.states.get(self.settings.entity_temp_acc1)
                temperature_acc2 = self.hass.states.get(self.settings.entity_temp_acc2)
                temperature_dhw = self.hass.states.get(self.settings.entity_temp_dhw)
                
                # Check if Temperature sensor entities exist
                if temperature_acc1 is None:
                    LOGGER.error(f"Temperature sensor {self.settings.entity_temp_acc1} does not exist!")
                    return

                if temperature_acc2 is None:
                    LOGGER.error(f"Temperature sensor {self.settings.entity_temp_acc2} does not exist!")
                    return

                if temperature_dhw is None:
                    LOGGER.error(f"Temperature sensor {self.settings.entity_temp_dhw} does not exist!")
                    return
                
                # Check if Temperature sensor entities are available
                if temperature_acc1.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Temperature sensor {self.settings.entity_temp_acc1} is not available (state: {temperature_acc1.state})")
                    return

                if temperature_acc2.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Temperature sensor {self.settings.entity_temp_acc2} is not available (state: {temperature_acc2.state})")
                    return

                if temperature_dhw.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Temperature sensor {self.settings.entity_temp_dhw} is not available (state: {temperature_dhw.state})")
                    return
                
                # Convert to float
                temperature_acc1_value = float(temperature_acc1.state)
                temperature_acc2_value = float(temperature_acc2.state)
                temperature_dhw_value = float(temperature_dhw.state)
                self.higher_temperature_acc_value = float((temperature_acc1_value + temperature_acc2_value) / 2.00)
                self.lower_temperature_acc_value = float(min(temperature_acc1_value, temperature_acc2_value))
                
                LOGGER.debug("Temperature sensor values: temperature_acc1_value=%f, temperature_acc2_value=%f, temperature_dhw_value=%f",
                            temperature_acc1_value, temperature_acc2_value, temperature_dhw_value)

            except (ValueError, TypeError) as e:
                LOGGER.error(f"Could not convert temperature sensors to float: {e}")
                LOGGER.error(f"ACC1: {temperature_acc1.state if temperature_acc1 else 'None'}")
                LOGGER.error(f"ACC2: {temperature_acc2.state if temperature_acc2 else 'None'}")
                LOGGER.error(f"DHW: {temperature_dhw.state if temperature_dhw else 'None'}")
                return

        # **** Get Valve Objects ****************************************************************************
            try:
                valve_from_hp_to_acc_or_dhw = self.hass.states.get(self.settings.entity_valve_from_hp_to_acc_or_dhw)
                valve_output_acc1 = self.hass.states.get(self.settings.entity_valve_output_acc1)
                valve_output_acc2 = self.hass.states.get(self.settings.entity_valve_output_acc2)
                valve_input_acc1 = self.hass.states.get(self.settings.entity_valve_input_acc1)
                valve_input_acc2 = self.hass.states.get(self.settings.entity_valve_input_acc2)
                valve_from_acc_to_heat_or_dhw = self.hass.states.get(self.settings.entity_valve_from_acc_to_heat_or_dhw)
                valve_output_heating = self.hass.states.get(self.settings.entity_valve_output_heating)
                
                # Check if valve entities exist
                if valve_from_hp_to_acc_or_dhw is None:
                    LOGGER.error(f"Valve {self.settings.entity_valve_from_hp_to_acc_or_dhw} does not exist!")
                    return

                if valve_output_acc1 is None:
                    LOGGER.error(f"Valve {self.settings.entity_valve_output_acc1} does not exist!")
                    return

                if valve_output_acc2 is None:
                    LOGGER.error(f"Valve {self.settings.entity_valve_output_acc2} does not exist!")
                    return

                if valve_input_acc1 is None:
                    LOGGER.error(f"Valve {self.settings.entity_valve_input_acc1} does not exist!")
                    return

                if valve_input_acc2 is None:
                    LOGGER.error(f"Valve {self.settings.entity_valve_input_acc2} does not exist!")
                    return

                if valve_from_acc_to_heat_or_dhw is None:
                    LOGGER.error(f"Valve {self.settings.entity_valve_from_acc_to_heat_or_dhw} does not exist!")
                    return

                if valve_output_heating is None:
                    LOGGER.error(f"Valve {self.settings.entity_valve_output_heating} does not exist!")
                    return

                # Check if valve entities are available
                if valve_from_hp_to_acc_or_dhw.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_valve_from_hp_to_acc_or_dhw} is not available (state: {valve_from_hp_to_acc_or_dhw.state})")
                    return

                if valve_output_acc1.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_valve_output_acc1} is not available (state: {valve_output_acc1.state})")
                    return

                if valve_output_acc2.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_valve_output_acc2} is not available (state: {valve_output_acc2.state})")
                    return

                if valve_input_acc1.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_valve_input_acc1} is not available (state: {valve_input_acc1.state})")
                    return

                if valve_input_acc2.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_valve_input_acc2} is not available (state: {valve_input_acc2.state})")
                    return

                if valve_from_acc_to_heat_or_dhw.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_valve_from_acc_to_heat_or_dhw} is not available (state: {valve_from_acc_to_heat_or_dhw.state})")
                    return

                if valve_output_heating.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_valve_output_heating} is not available (state: {valve_output_heating.state})")
                    return

            except Exception as e:
                LOGGER.error(f"Failed to load valve entities: {e}")
                return

        # **** Get Water Pump Objects ***********************************************************************
            try:
                water_pump_acc_output = self.hass.states.get(self.settings.entity_water_pump_acc_output)
                water_pump_dhw = self.hass.states.get(self.settings.entity_water_pump_dhw)
                water_pump_floor_heating = self.hass.states.get(self.settings.entity_water_pump_floor_heating)
                water_pump_heating = self.hass.states.get(self.settings.entity_water_pump_heating)

                # Check if water pump entities exist
                if water_pump_acc_output is None:
                    LOGGER.error(f"Water pump entity {self.settings.entity_water_pump_acc_output} does not exist!")
                    return

                if water_pump_dhw is None:
                    LOGGER.error(f"Water pump entity {self.settings.entity_water_pump_dhw} does not exist!")
                    return

                if water_pump_floor_heating is None:
                    LOGGER.error(f"Water pump entity {self.settings.water_pump_floor_heating} does not exist!")
                    return

                if water_pump_heating is None:
                    LOGGER.error(f"Water pump entity {self.settings.water_pump_heating} does not exist!")
                    return

                # Check if water pump entities are available
                if water_pump_acc_output.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_water_pump_acc_output} is not available (state: {water_pump_acc_output.state})")
                    return

                if water_pump_dhw.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_water_pump_dhw} is not available (state: {water_pump_dhw.state})")
                    return

                if water_pump_floor_heating.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_water_pump_floor_heating} is not available (state: {water_pump_floor_heating.state})")
                    return

                if water_pump_heating.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Valve {self.settings.entity_water_pump_heating} is not available (state: {water_pump_heating.state})")
                    return

            except Exception as e:
                LOGGER.error(f"Failed to load water pump entities: {e}")
                return

        # **** Get states of Heating System entities (thermostat and heating pump entities) *****************
            try:
                thermostat_state = self.hass.states.get(self.settings.entity_thermostat_state)
                heating_state = self.hass.states.get(self.settings.entity_heating_state)
                podlahove_stav = self.hass.states.get(self.settings.entity_floor_heating_state)
                
                # Check if Heating System entities exist
                if thermostat_state is None:
                    LOGGER.error(f"Temperature sensor {self.settings.entity_thermostat_state} does not exist!")
                    return

                if heating_state is None:
                    LOGGER.error(f"Temperature sensor {self.settings.entity_heating_state} does not exist!")
                    return

                if podlahove_stav is None:
                    LOGGER.error(f"Temperature sensor {self.settings.entity_floor_heating_state} does not exist!")
                    return

                # Check if Heating System entities are available
                if thermostat_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Heating system entity {self.settings.entity_thermostat_state} is not available (state: {thermostat_state.state})")
                    return

                if heating_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Heating system entity {self.settings.entity_heating_state} is not available (state: {heating_state.state})")
                    return

                if podlahove_stav.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, None]:
                    LOGGER.warning(f"Heating system entity {self.settings.entity_floor_heating_state} is not available (state: {podlahove_stav.state})")
                    return

                LOGGER.debug("External Entity States: thermostat_state=%s, heating_state=%s, podlahove_stav=%s",
                            thermostat_state.state, heating_state.state, podlahove_stav.state)

            except Exception as e:
                LOGGER.error(f"Failed to load External Entity States. Error details: {e}")
                return

# ******************************************************************************************
# ********************** LOGIKA CONTROLLERA ************************************************
# ******************************************************************************************

            if not automatic_mode:
                return

    # ******************************************************************************************************
    # *** VYPOCET PREFEROVANEHO ZASOBNIKA ACC PRE ODCERPAVANIE TEPLEJ VODY *********************************
    # ******************************************************************************************************

            # zistenie ci teplota v DHW dosiahla teplotu v ((ACC1 alebo ACC2) - offset)
            # Podla toho bude odcerpacat (primarne z toho v ktorom ACC je teplota vyssia),
            # ale ak sa zasobnik vypne, ale jeho teplota bude este stale vyssia, nez teplotny limit
            # u vypnuteho zasobnika, tak sa docasne povoli odcerpanie teplej vody,
            # dokial sa teplota neznizi, ale vstup do zasobnika bude uz uzatvoreny
            # Toto plati aj pre kurenie a aj pre DHW
            self.preferred_output_ACC = 0
            self.preferred_input_ACC = 0
            self.higher_temperature_acc_value = float((temperature_acc1_value + temperature_acc2_value) / 2.00)
            self.lower_temperature_acc_value = float(min(temperature_acc1_value, temperature_acc2_value))

            if (abs(temperature_acc1_value - temperature_acc2_value) > self.settings.temperature_delta_limit_in_acc):
                if (acc1_enable and acc2_enable):
                    if (temperature_acc1_value > temperature_acc2_value):
                        self.higher_temperature_acc_value = temperature_acc1_value
                        self.lower_temperature_acc_value = temperature_acc2_value
                        self.preferred_input_ACC = 2
                        self.preferred_output_ACC = 1
                    else:
                        self.higher_temperature_acc_value = temperature_acc2_value
                        self.lower_temperature_acc_value = temperature_acc1_value
                        self.preferred_input_ACC = 1
                        self.preferred_output_ACC = 2
                elif (acc1_enable and (not acc2_enable)):
                    self.preferred_input_ACC = 1
                    if (temperature_acc2_value > self.settings.disabled_acc_temperature_limit):
                        if (temperature_acc2_value > temperature_acc1_value):
                            self.preferred_output_ACC = 2
                            self.higher_temperature_acc_value = temperature_acc2_value
                            self.lower_temperature_acc_value = temperature_acc1_value
                        else:
                            self.preferred_output_ACC = 1
                            self.higher_temperature_acc_value = temperature_acc1_value
                            self.lower_temperature_acc_value = temperature_acc2_value
                    else:
                        self.preferred_output_ACC = 1
                        self.higher_temperature_acc_value = temperature_acc1_value
                        self.lower_temperature_acc_value = temperature_acc1_value
                elif ((not acc1_enable) and acc2_enable):
                    self.preferred_input_ACC = 2
                    if (temperature_acc1_value > self.settings.disabled_acc_temperature_limit):
                        if (temperature_acc1_value > temperature_acc2_value):
                            self.preferred_output_ACC = 1
                            self.higher_temperature_acc_value = temperature_acc1_value
                            self.lower_temperature_acc_value = temperature_acc2_value
                        else:
                            self.preferred_output_ACC = 2
                            self.higher_temperature_acc_value = temperature_acc2_value
                            self.lower_temperature_acc_value = temperature_acc1_value
                    else:
                        self.preferred_output_ACC = 2
                        self.higher_temperature_acc_value = temperature_acc2_value
                        self.lower_temperature_acc_value = temperature_acc2_value

            temperature_acc_with_offset = self.higher_temperature_acc_value - self.settings.temperature_delta_limit_acc_dhw

            # ak je v ACC nizsia teplota nez pouzitelna na korenie (zadefinovana v nastaveniach), tak anuluje hodnoty v premenych z termostatov kurenia
            if(self.higher_temperature_acc_value < self.settings.min_temperature_for_heating):
                thermostat_state.state = STATE_OFF
                heating_state.state = STATE_OFF
                podlahove_stav.state = STATE_OFF

            LOGGER.debug("Temperature in ACC 1 and 2: temperature_acc1_value=%f, temperature_acc2_value=%f, temperature_acc_with_offset=%f, self.preferred_output_ACC=%d, self.preferred_input_ACC=%d",
                        temperature_acc1_value, temperature_acc2_value, temperature_acc_with_offset, self.preferred_output_ACC, self.preferred_input_ACC)

    # ******************************************************************************************************
    # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA (sekvenčné módy, priority, atď. *************************************
    # ******************************************************************************************************
                
        # ******************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - MANUÁLNY MÓD ******************************************************
        # ******************************************************************************************************
            if(self.heating_operating_mode==HEATING_OPERATING_MODE_MANUAL):
                self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

                # INICIALIZÁCIA MÓDU
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu

                # HLAVNÁ LOGIKA

                self.heating_source_auto_on_off = True
#                self.temperature_setpoint = MAX_TEMPERATURE_LIMIT - (self.settings.heating_source_temp_hysteresis / 2)
#                self.temperature_setpoint = MAX_TEMPERATURE_LIMIT
                self.temperature_setpoint = acc_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

        # ******************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - AUTOMATICKÝ MÓD - Len Ohrev DHW ***********************************
        # ******************************************************************************************************
            elif(self.heating_operating_mode==HEATING_OPERATING_MODE_DHW):
                self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

                # INICIALIZÁCIA MÓDU
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu
                    # pri vstupe do tohot rezimu sa stopne precerpavanie z ACC do TUV
                    await self.stop_heat_dhw_from_acc()

                # HLAVNÁ LOGIKA

                # a ak nie je striktny mod, pretoci ventil do TUV natrvalo pocas celeho rezimu
                if (self.settings.valve_input_acc_strict_mode != VALVE_MODE_STRICT):
                    await self.switch_to_dhw()

                # Ak je v TUV teplota vyssia nez 2. uroven ziadanej teploty (52.5)
                if ((dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))) or (not self.heating_source_input_on_off)):
                    # vypne ohrev
                    self.heating_source_auto_on_off = False
                    # a ak je striktny mod, pretoci ventil do ACC
                    if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                        await self.switch_to_acc()

                # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                elif(dhw_target_temperature > (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                    # zapne ohrev TUV
                    self.heating_source_auto_on_off = True
                    # a v striktnom mode pretoci ventil do TUV
                    if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                        await self.switch_to_dhw()

                self.temperature_setpoint = dhw_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

        # **************************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - AUTOMATICKÝ MÓD - Cyklus s prioritou: 1.Prečerpanie z ACC, 2. Ohrev DHW ***
        # **************************************************************************************************************
            elif(self.heating_operating_mode==HEATING_OPERATING_MODE_PDHW_DHW):
                self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

                # INICIALIZÁCIA MÓDU
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu
                    # pri vstupe do tohot rezimu sa stopne precerpavanie z ACC do TUV
                    await self.stop_heat_dhw_from_acc()

                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                    if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):

                        # prepne sa na ventil z TC na ACC a vypne sa zdroj kurenia
                        await self.switch_to_acc()
                        self.heating_source_auto_on_off = False

                # HLAVNÁ LOGIKA

                # a ak nie je striktny mod, pretoci ventil do TUV natrvalo pocas celeho rezimu
                if (self.settings.valve_input_acc_strict_mode != VALVE_MODE_STRICT):
                    await self.switch_to_dhw()

                # Ak je v ACC vyssia teplota nez v TUV
                if (temperature_acc_with_offset > temperature_dhw_value):
                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                    if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                        # zapne sa precerpavanie z ACC do TUV a vypne sa zdroj kurenia
                        await self.start_heat_dhw_from_acc()
                        self.heating_source_auto_on_off = False
                
                # Ak je v ACC teplota rovna, alebo dokonca nizsia nez v TUV, alebo teplota dosiahne cielovu hodnotu
                # vypne sa precerpavanie automaticky (nie tu, ale v inej casti programu)
                # zapne sa zdroj kurenia
                else:
                    # Ak je v TUV teplota vyssia nez 2. uroven ziadanej teploty (52.5)
                    if ((dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))) or (not self.heating_source_input_on_off)):
                        # vypne ohrev
                        self.heating_source_auto_on_off = False
                        # a ak je striktny mod, pretoci ventil do ACC
                        if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                            await self.switch_to_acc()

                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                    elif(dhw_target_temperature > (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                        # zapne ohrev TUV
                        self.heating_source_auto_on_off = True
                        # a v striktnom mode pretoci ventil do TUV
                        if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                            await self.switch_to_dhw()

                self.temperature_setpoint = dhw_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

        # ******************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - AUTOMATICKÝ MÓD - Len Ohrev ACC ***********************************
        # ******************************************************************************************************
            elif(self.heating_operating_mode==HEATING_OPERATING_MODE_ACC):
                self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

                # INICIALIZÁCIA MÓDU
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu
                    # pri vstupe do tohot rezimu sa stopne precerpavanie z ACC do TUV
                    await self.stop_heat_dhw_from_acc()

                # HLAVNÁ LOGIKA

                await self.switch_to_acc()

                if(acc_target_temperature < (self.lower_temperature_acc_value - (self.settings.heating_source_temp_hysteresis / 2))):
                    self.heating_source_auto_on_off = False
                elif(acc_target_temperature > (self.lower_temperature_acc_value + (self.settings.heating_source_temp_hysteresis / 2))):
                    self.heating_source_auto_on_off = True

                self.temperature_setpoint = acc_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

        # **************************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - AUTOMATICKÝ MÓD - 1.Prečerpanie z ACC + 2. Ohrev ACC ***
        # **************************************************************************************************************
            elif(self.heating_operating_mode==HEATING_OPERATING_MODE_PDHW_ACC):
                self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

                # INICIALIZÁCIA MÓDU
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu
                    # pri vstupe do tohot rezimu sa stopne precerpavanie z ACC do TUV
                    await self.stop_heat_dhw_from_acc()

                # HLAVNÁ LOGIKA

                await self.switch_to_acc()

                if(acc_target_temperature < (self.lower_temperature_acc_value - (self.settings.heating_source_temp_hysteresis / 2))):
                    self.heating_source_auto_on_off = False
                elif(acc_target_temperature > (self.lower_temperature_acc_value + (self.settings.heating_source_temp_hysteresis / 2))):
                    self.heating_source_auto_on_off = True

                self.temperature_setpoint = acc_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

                # Ak je v ACC vyssia teplota nez v TUV
                # ***** (Ak je v ACC teplota rovna, alebo nizsia nez v TUV, alebo teplota dosiahne cielovu hodnotu, precerpavanie sa vypne automaticky (nie tu, ale v inej casti programu)
                if (temperature_acc_with_offset > temperature_dhw_value):
                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                    if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                        # zapne sa precerpavanie z ACC do TUV
                        await self.start_heat_dhw_from_acc()

        # ******************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - AUTOMATICKÝ MÓD - Cyklus s prioritou: 1.Ohrev DHW, 2.Ohrev ACC ****
        # ******************************************************************************************************
            elif(self.heating_operating_mode==HEATING_OPERATING_MODE_DHW_ACC):
                self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

                # INICIALIZÁCIA MÓDU
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu
                    # pri vstupe do tohot rezimu sa stopne precerpavanie z ACC do TUV
                    await self.stop_heat_dhw_from_acc()

                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                    if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):

                        # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                        await self.switch_to_dhw()
                        self.heating_source_auto_on_off = True

                # HLAVNÁ LOGIKA

                # ak je prepnute na ohrev TUV
                if(self.hp_dhw):

                    # Pre zdroj kurenia sa nastavi 2. uroven teploty pre TUV (52.5)
                    self.temperature_setpoint = dhw_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)
                    
                    # Ak je striktny mod pre vstupne ventily
                    flag_0 = True
                    if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                        # Ak je zdroj kurenia vypnuty
                        if (self.heating_source_input_on_off == False):
                            # Tak sa prepne ventil z TC do ACC
                            await self.switch_to_acc()
                            flag_0 = False

                    if(flag_0):

                        # Ak teplota v TUV prekroci 2. uroven ziadanej teploty (52.5)
                        if(dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))):

                            # Tak sa prepne na ohrev ACC
                            await self.switch_to_acc()

                            # Ak je v ACC teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                            if(acc_target_temperature < (self.lower_temperature_acc_value - (self.settings.heating_source_temp_hysteresis / 2))):

                                # vypne sa zdroj kurenia
                                self.heating_source_auto_on_off = False

                # ak je uz prepnuty ohrev na ACC
                else:

                    # Pre zdroj kurenia sa nastavi 2. uroven ziadanej teploty (52.5) pre ACC
                    self.temperature_setpoint = acc_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)
                    
                    # Ak je zdroj kurenia zapnuty
                    if (self.heating_source_input_on_off == True):
                        
                        # Ak je v ACC teplota vyssia nez 1. uroven ziadanej teploty (47.5)
                        if(acc_target_temperature < (self.lower_temperature_acc_value + (self.settings.heating_source_temp_hysteresis / 2))):
                            
                            # Ak je v ACC teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                            if(acc_target_temperature < (self.lower_temperature_acc_value - (self.settings.heating_source_temp_hysteresis / 2))):
                                
                                # ak bol zdroj teploty uz zapnuty (z predchadzajucej sekvencie) tak bude pokracovat v kureni az do dosiahnutia 2. urovne ziadanej teploty (52.5)
                                if(self.heating_source_auto_on_off):

                                    # Ak je v TUV teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                                    if(dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))):
                                        
                                        # vypne sa zdroj kurenia
                                        self.heating_source_auto_on_off = False
                                        
                                    # Ak je v TUV teplota nizsia nez 2. uroven ziadanej teploty (52.5)
                                    else:
                                        
                                        # prepne sa na ohrev TUV
                                        await self.switch_to_dhw()

                                # ak bol zdroj teploty uz vypnuty (z predchadzajucej sekvencie) tak sa zapne az po znizeni teploty TUV pod 1. uroven ziadanej teploty
                                else:

                                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                                    if not (dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):

                                        # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                        await self.switch_to_dhw()
                                        self.heating_source_auto_on_off = True

                            # Ak je v ACC teplota nizsia, nez 2. uroven ziadanej teploty (52.5)
                            else:

                                # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                                if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                                    
                                    # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                    await self.switch_to_dhw()
                                    self.heating_source_auto_on_off = True

                        # Ak je v ACC teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                        else:

                            # zapne sa zdroj kurenia
                            self.heating_source_auto_on_off = True

                            # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                            if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                                # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                await self.switch_to_dhw()

                            # Ak je v TUV teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                            if(dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))):
                                # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                await self.switch_to_acc()

        # ***********************************************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - AUTOMATICKÝ MÓD - Cyklus s prioritou: 1.Prečerpanie z ACC do DHW, 2.Ohrev DHW, 3.ohrev ACC *****
        # ***********************************************************************************************************************************
            elif(self.heating_operating_mode==HEATING_OPERATING_MODE_PDHW_DHW_ACC):

                # INICIALIZÁCIA MÓDU
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu
                    # pri vstupe do tohot rezimu sa stopne precerpavanie z ACC do TUV
                    await self.stop_heat_dhw_from_acc()

                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                    if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):

                        # prepne sa na ohrev ACC a vypne sa zdroj kurenia
                        await self.switch_to_acc()
                        self.heating_source_auto_on_off = False

                # HLAVNÁ LOGIKA

                # Ak je v ACC vyssia teplota nez v TUV
                if (temperature_acc_with_offset > temperature_dhw_value):

                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                    if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):

                        # zapne sa precerpavanie z ACC do TUV
                        # ventil sa presmeruje zo zdroja kurenia do ACC
                        # Pre zdroj kurenia sa teplota nastavi na 2. uroven teploty pre ACC
                        self.temperature_setpoint = acc_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

                        if (self.heating_operating_mode_pdhw_dhw_acc_init_flag2 == 0):
                            self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 1

                            # zapne sa precerpavanie z ACC do TUV, prepne sa ventil na ACC a vypne sa zdroj kurenia
                            await self.start_heat_dhw_from_acc()
                            await self.switch_to_acc()

                        # Ak je v ACC vyssia teplota nez 1. uroven ziadanej teploty (47.5)
                        if(acc_target_temperature < (self.lower_temperature_acc_value + (self.settings.heating_source_temp_hysteresis / 2))):
                            # vypne sa zdroj kurenia
                            self.heating_source_auto_on_off = False

                        # Ak je v ACC teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                        else:
                            # zapne sa zdroj kurenia
                            self.heating_source_auto_on_off = True

                # Ak je v ACC teplota rovna, alebo dokonca nizsia nez v TUV, alebo teplota dosiahne cielovu hodnotu
                # vypne sa precerpavanie automaticky (nie tu, ale v inej casti programu)
                # zapne sa zdroj kurenia a ventil sa prepne zo zdoja kurenia na TUV
                else:
                    # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                    if (self.heating_operating_mode_pdhw_dhw_acc_init_flag2 == 1):
                        self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0

                        # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                        await self.switch_to_dhw()
                        self.heating_source_auto_on_off = True

                # ak bezi precerpavanie, cela dalsia cast programu sa nevykona, az ked precerpavanie skonci
                if (not self.heat_dhw_from_acc):

                    # ak je prepnute na ohrev TUV
                    if(self.hp_dhw):

                        # Pre zdroj kurenia sa nastavi 2. uroven teploty pre TUV (52.5)
                        self.temperature_setpoint = dhw_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

                        # Ak je striktny mod pre vstupne ventily
                        flag_0 = True
                        if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                            # Ak je zdroj kurenia vypnuty
                            if (self.heating_source_input_on_off == False):
                                # Tak sa prepne ventil z TC do ACC
                                await self.switch_to_acc()
                                flag_0 = False
                        
                        if(flag_0):
                    
                            # Ak teplota v TUV prekroci 2. uroven ziadanej teploty (52.5)
                            if(dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))):

                                # Tak sa prepne na ohrev ACC
                                await self.switch_to_acc()

                                # Ak je v ACC teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                                if(acc_target_temperature < (self.lower_temperature_acc_value - (self.settings.heating_source_temp_hysteresis / 2))):

                                    # vypne sa zdroj kurenia
                                    self.heating_source_auto_on_off = False

                    # ak je uz prepnuty ohrev na ACC
                    else:

                        # Pre zdroj kurenia sa nastavi 2. uroven ziadanej teploty (52.5) pre ACC
                        self.temperature_setpoint = acc_target_temperature + (self.settings.heating_source_temp_hysteresis / 2)

                        # Ak je zdroj kurenia zapnuty
                        if (self.heating_source_input_on_off == True):
                            
                            # Ak je v ACC teplota vyssia nez 1. uroven ziadanej teploty (47.5)
                            if(acc_target_temperature < (self.lower_temperature_acc_value + (self.settings.heating_source_temp_hysteresis / 2))):
                                
                                # Ak je v ACC teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                                if(acc_target_temperature < (self.lower_temperature_acc_value - (self.settings.heating_source_temp_hysteresis / 2))):
                                    
                                    # ak bol zdroj teploty uz zapnuty (z predchadzajucej sekvencie) tak bude pokracovat v kureni az do dosiahnutia 2. urovne ziadanej teploty (52.5)                                
                                    if(self.heating_source_auto_on_off):

                                        # Ak je v TUV teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                                        if(dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))):
                                            
                                            # vypne sa zdroj kurenia
                                            self.heating_source_auto_on_off = False
                                            
                                        # Ak je v TUV teplota nizsia nez 2. uroven ziadanej teploty (52.5)
                                        else:
                                            
                                            # prepne sa na ohrev TUV
                                            await self.switch_to_dhw()

                                    # ak bol zdroj teploty uz vypnuty (z predchadzajucej sekvencie) tak sa zapne az po znizeni teploty TUV pod 1. uroven ziadanej teploty
                                    else:

                                        # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                                        if not (dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):

                                            # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                            await self.switch_to_dhw()
                                            self.heating_source_auto_on_off = True
                                            
                                # Ak je v ACC teplota nizsia, nez 2. uroven ziadanej teploty (52.5)
                                else:
                                    
                                    # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                                    if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                                        
                                        # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                        await self.switch_to_dhw()
                                        self.heating_source_auto_on_off = True

                            # Ak je v ACC teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                            else:
                                
                                # zapne sa zdroj kurenia
                                self.heating_source_auto_on_off = True

                                # Ak je v TUV teplota nizsia nez 1. uroven ziadanej teploty (47.5)
                                if not(dhw_target_temperature < (temperature_dhw_value + (self.settings.heating_source_temp_hysteresis / 2))):
                                    # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                    await self.switch_to_dhw()

                                # Ak je v TUV teplota vyssia, nez 2. uroven ziadanej teploty (52.5)
                                if(dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2))):
                                    # prepne sa na ohrev TUV a zapne sa zdroj kurenia
                                    await self.switch_to_acc()

        # ***********************************************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - NEPLATNÝ REŽIM *********************************************************************************
        # ***********************************************************************************************************************************
        
            else:
                if(self.heating_operating_mode_previous != self.heating_operating_mode):
                    self.heating_operating_mode_previous = self.heating_operating_mode
                    # Jednorazove vykonanie akcie pri zmene heating modu
                    # pri vstupe do tohot rezimu sa stopne precerpavanie z ACC do TUV
                    await self.stop_heat_dhw_from_acc()

                self.heating_operating_mode_pdhw_dhw_acc_init_flag2 = 0
                LOGGER.error(f"Heating operating mode {self.heating_operating_mode} is not valid.")

        # ***********************************************************************************************************************************
        # *** 1. ÚROVEŇ AUTOMATIKY KÚRENIA - RIADIACE SIGNÁLY PRE TC ************************************************************************
        # ***********************************************************************************************************************************

            if(self.temperature_setpoint > 65):
                self.sensor_states[ENTITY_CONTROL_COMMAND_HP_TEMPERATURE] = 65
            elif(self.temperature_setpoint < 25):
                self.sensor_states[ENTITY_CONTROL_COMMAND_HP_TEMPERATURE] = 25
            else:
                self.sensor_states[ENTITY_CONTROL_COMMAND_HP_TEMPERATURE] = self.temperature_setpoint

            self.controll_command_hp_on_off = 0
            if(self.heating_source_input_on_off):
                if(self.heating_source_auto_on_off):
                    if(
                        (temperature_acc1_value <= MAX_TEMPERATURE_LIMIT) and
                        (temperature_acc2_value <= MAX_TEMPERATURE_LIMIT) and
                        (temperature_dhw_value <= MAX_TEMPERATURE_LIMIT)
                        ):
                        if(self.heating_operating_mode==HEATING_OPERATING_MODE_MANUAL):
                            if (valve_from_hp_to_acc_or_dhw.state == STATE_HP_ACC):
                                if ((valve_input_acc1.state == STATE_OPEN) or (valve_input_acc2.state == STATE_OPEN)):
                                    self.controll_command_hp_on_off = 1
                            elif (valve_from_hp_to_acc_or_dhw.state == STATE_HP_DHW):
                                self.controll_command_hp_on_off = 1
                        else:
                            self.controll_command_hp_on_off = 1

            # Detekcia zmeny stavu TČ pre časovač zatvorenia ventilov na vstupoch do ACC
            if (self._previous_controll_command_hp_on_off == 1 and self.controll_command_hp_on_off == 0):
                # TČ sa práve vyplo - spustiť časovač ak ešte nebeží
                if self._valve_input_acc_closing_delay_timer is None:
                    delay_minutes = self.settings.valve_input_acc_closing_delay_when_heating_source_stop
                    if delay_minutes > 0:
                        self._valve_input_acc_closing_allowed = False
                        self._valve_input_acc_closing_delay_timer = async_call_later(
                            self.hass,
                            delay_minutes * 60,  # konverzia minút na sekundy
                            self._valve_input_acc_closing_delay_finished
                        )
                        LOGGER.info(f"Valve input ACC closing delay timer started for {delay_minutes} minutes")
                    else:
                        # Ak je delay 0, povoliť zatvorenie okamžite
                        self._valve_input_acc_closing_allowed = True
                
                # Časovač pre oneskorenie pretočenia ventilu hp_dhw z TUV na ACC
                # Spúšťa sa len ak: ventil je v TUV a vstupné ventily do ACC sú zatvorené
                if (valve_from_hp_to_acc_or_dhw.state == STATE_HP_DHW and 
                    valve_input_acc1.state == STATE_CLOSED and 
                    valve_input_acc2.state == STATE_CLOSED):
                    if self._hp_dhw_to_acc_delay_timer is None:
                        delay_minutes = self.settings.valve_input_acc_closing_delay_when_heating_source_stop
                        if delay_minutes > 0:
                            self._hp_dhw_to_acc_switch_allowed = False
                            self._hp_dhw_to_acc_delay_timer = async_call_later(
                                self.hass,
                                delay_minutes * 60,  # konverzia minút na sekundy
                                self._hp_dhw_to_acc_delay_finished
                            )
                            LOGGER.info(f"HP DHW to ACC switch delay timer started for {delay_minutes} minutes (HP off, DHW active, ACC inputs closed)")
                        else:
                            # Ak je delay 0, povoliť pretočenie okamžite
                            self._hp_dhw_to_acc_switch_allowed = True
                else:
                    # Ak podmienky nie sú splnené, resetovať príznak (môže sa pretočiť ihneď)
                    self._hp_dhw_to_acc_switch_allowed = True
            elif (self._previous_controll_command_hp_on_off == 0 and self.controll_command_hp_on_off == 1):
                # TČ sa práve zaplo - zrušiť časovač a resetovať stav
                if self._valve_input_acc_closing_delay_timer is not None:
                    self._valve_input_acc_closing_delay_timer()
                    self._valve_input_acc_closing_delay_timer = None
                    LOGGER.debug("Valve input ACC closing delay timer cancelled - HP turned on")
                self._valve_input_acc_closing_allowed = True
                
                # Zrušiť aj časovač pre pretočenie hp_dhw ventilu
                if self._hp_dhw_to_acc_delay_timer is not None:
                    self._hp_dhw_to_acc_delay_timer()
                    self._hp_dhw_to_acc_delay_timer = None
                    LOGGER.debug("HP DHW to ACC switch delay timer cancelled - HP turned on")
                self._hp_dhw_to_acc_switch_allowed = True
            
            # Uložiť aktuálny stav pre porovnanie v ďalšom cykle
            self._previous_controll_command_hp_on_off = self.controll_command_hp_on_off

            if (self.controll_command_hp_on_off):
                await self._set_hp_on_off_with_debounce(STATE_ON)
            else:
                await self._set_hp_on_off_with_debounce(STATE_OFF)

    # ******************************************************************************************************
    # *** AUTOMATICKE VYPNUTIE PRECERPAVANIA Z ACC DO DHW, KED SA DOSIAHNE V DHW TEPLOTA, KTORA JE V ACC ***
    # ******************************************************************************************************

            # Ak teplota v DHW dosiahne teplotu v ((ACC1 alebo ACC2) - offset), alebo
            # ak teplota v TUV prekroci 2. uroven teploty voči žiadanej teplote
            # tak sa vypne switch.heat_dhw_from_acc
            if (
                (temperature_acc_with_offset <= temperature_dhw_value) or
                (dhw_target_temperature < (temperature_dhw_value - (self.settings.heating_source_temp_hysteresis / 2)))
                ):
                    await self.stop_heat_dhw_from_acc()

    # ******************************************************************************************************
    # *** OVLÁDANIE VENTILU Z TEPELNÉHO ČERPADLA KTORÝ PREPÍNA BUĎ DO ACC, ALEBO DO DHW ********************
    # ******************************************************************************************************

            if (self.hp_dhw):
                self.valve_from_hp_to_acc_or_dhw_flag = 0
            else:
                self.valve_from_hp_to_acc_or_dhw_flag = 1

            # **** Ovládanie ventilu *******************************************************************
            if (self.valve_from_hp_to_acc_or_dhw_flag):
                if (valve_from_hp_to_acc_or_dhw.state == STATE_HP_DHW):
                    # Kontrola oneskorenia - len ak prepíname z DHW na ACC
                    if not self._hp_dhw_to_acc_switch_allowed:
                        LOGGER.debug("Valve HP to ACC switch delayed - waiting for timer")
                    else:
                        if await self._call_valve_service(CONF_VALVE_FROM_TC_TO_ACC_OR_DHW, SWITCH_HP_to_ACC, self.settings.entity_valve_from_hp_to_acc_or_dhw):
                            LOGGER.debug("Valve from Heating pump is switched to ACC")
            else:
                if (valve_from_hp_to_acc_or_dhw.state == STATE_HP_ACC):
                    if await self._call_valve_service(CONF_VALVE_FROM_TC_TO_ACC_OR_DHW, SWITCH_HP_to_DHW, self.settings.entity_valve_from_hp_to_acc_or_dhw):
                        LOGGER.debug("Valve from Heating pump is switched to DHW")

    # ******************************************************************************************************
    # *** OVLÁDANIE VENTILU NA VÝSTUPE Z ACC 1 *************************************************************
    # ******************************************************************************************************

            self.valve_output_acc1_flag = 0
            if ((acc1_enable) or (temperature_acc1_value > self.settings.disabled_acc_temperature_limit)):
                if (self.preferred_output_ACC==0) or (self.preferred_output_ACC==1):
                    if (self.heat_dhw_from_acc):
                        self.valve_output_acc1_flag = 1
                    else:
                        if (self.settings.valve_output_acc_strict_mode == VALVE_MODE_GENERIC):
                            self.valve_output_acc1_flag = 1
                        elif (self.settings.valve_output_acc_strict_mode == VALVE_MODE_MODERATE):
                            if (thermostat_state.state == STATE_ON):
                                self.valve_output_acc1_flag = 1
                        elif (self.settings.valve_output_acc_strict_mode == VALVE_MODE_STRICT):
                            if (not self.hp_dhw):
                                if (thermostat_state.state == STATE_ON):
                                    self.valve_output_acc1_flag = 1
                            else:
                                if (heating_state.state == STATE_ON):
                                    self.valve_output_acc1_flag = 1
                        else:
                            LOGGER.error("Value in 'self.settings.valve_output_acc_strict_mode' = '%s' is invalid.", 
                                    self.settings.valve_output_acc_strict_mode)

            # **** Ovládanie ventilu *******************************************************************
            if (self.valve_output_acc1_flag):
                if (valve_output_acc1.state == STATE_CLOSED):
                    if await self._call_valve_service(CONF_VALVE_OUTPUT_ACC1, SWITCH_to_OPEN, self.settings.entity_valve_output_acc1):
                        LOGGER.debug("Valve output from ACC 1 was opened")
            else:
                if (valve_output_acc1.state == STATE_OPEN):
                    if await self._call_valve_service(CONF_VALVE_OUTPUT_ACC1, SWITCH_to_CLOSE, self.settings.entity_valve_output_acc1):
                        LOGGER.debug("Valve output from ACC 1 was closed")

    # ******************************************************************************************************
    # *** OVLÁDANIE VENTILU NA VÝSTUPE Z ACC 2 *************************************************************
    # ******************************************************************************************************

            self.valve_output_acc2_flag = 0
            if ((acc2_enable) or (temperature_acc2_value > self.settings.disabled_acc_temperature_limit)):
                if (self.preferred_output_ACC==0) or (self.preferred_output_ACC==2):
                    if (self.heat_dhw_from_acc):
                        self.valve_output_acc2_flag = 1
                    else:
                        if (self.settings.valve_output_acc_strict_mode == VALVE_MODE_GENERIC):
                            self.valve_output_acc2_flag = 1
                        elif (self.settings.valve_output_acc_strict_mode == VALVE_MODE_MODERATE):
                            if (thermostat_state.state == STATE_ON):
                                self.valve_output_acc2_flag = 1
                        elif (self.settings.valve_output_acc_strict_mode == VALVE_MODE_STRICT):
                            if (not self.hp_dhw):
                                if (thermostat_state.state == STATE_ON):
                                    self.valve_output_acc2_flag = 1
                            elif (self.hp_dhw):
                                if (heating_state.state == STATE_ON):
                                    self.valve_output_acc2_flag = 1
                        else:
                            LOGGER.error("Value in 'self.settings.valve_output_acc_strict_mode' = '%s' is invalid.",
                                    self.settings.valve_output_acc_strict_mode)

            # **** Ovládanie ventilu *******************************************************************
            if (self.valve_output_acc2_flag):
                if (valve_output_acc2.state == STATE_CLOSED):
                    if await self._call_valve_service(CONF_VALVE_OUTPUT_ACC2, SWITCH_to_OPEN, self.settings.entity_valve_output_acc2):
                        LOGGER.debug("Valve output from ACC 2 was opened")
            else:
                if (valve_output_acc2.state == STATE_OPEN):
                    if await self._call_valve_service(CONF_VALVE_OUTPUT_ACC2, SWITCH_to_CLOSE, self.settings.entity_valve_output_acc2):
                        LOGGER.debug("Valve output from ACC 2 was closed")

    # ******************************************************************************************************
    # *** OVLÁDANIE VENTILU NA VSTUPE DO ACC 1 *************************************************************
    # ******************************************************************************************************
            self.valve_input_acc1_flag = 0
            if (acc1_enable):
                # Otvara len ten ventil ktoreho ACC je chladnejsi, ak su teploty v oboch ACC rovnake, otvori obidva ventily
                # Tento ventil sa otvori aj vtedy ak by ACC druheho ventilu bol vypnuty
                if ((self.preferred_input_ACC==0) or (self.preferred_input_ACC==1) or (not acc2_enable)):
                    if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_GENERIC):
                        self.valve_input_acc1_flag = 1
                    elif (self.settings.valve_input_acc_strict_mode == VALVE_MODE_MODERATE):
                        if(not self.hp_dhw):
                            self.valve_input_acc1_flag = 1
                    elif (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                        if(not self.hp_dhw):
                            if(self.heating_operating_mode==HEATING_OPERATING_MODE_MANUAL):
                                if (self.heating_source_input_on_off):
                                    self.valve_input_acc1_flag = 1
                            elif (self.heating_operating_mode==HEATING_OPERATING_MODE_DHW):
                                self.valve_input_acc1_flag = 0
                            elif (self.heating_operating_mode==HEATING_OPERATING_MODE_PDHW_DHW):
                                self.valve_input_acc1_flag = 0
                            else:
                                if (self.controll_command_hp_on_off):
                                    self.valve_input_acc1_flag = 1
                        else:
                            if(self.heating_operating_mode==HEATING_OPERATING_MODE_DHW_ACC):
                                self.valve_input_acc1_flag = 0
                    else:
                        LOGGER.error("Value in 'self.settings.valve_input_acc_strict_mode' = '%s' is invalid.",
                                self.settings.valve_input_acc_strict_mode)

            # **** Ovládanie ventilu *******************************************************************
            if (self.valve_input_acc1_flag):
                if (valve_input_acc1.state == STATE_CLOSED):
                    if await self._call_valve_service(CONF_VALVE_INPUT_ACC1, SWITCH_to_OPEN, self.settings.entity_valve_input_acc1):
                        LOGGER.debug("Valve input to ACC 1 was opened")
            else:
                if (valve_input_acc1.state == STATE_OPEN):
                    # Zatvorenie ventilu len ak je povolené (časovač vypršal alebo TČ je zapnuté)
                    if self._valve_input_acc_closing_allowed:
                        if await self._call_valve_service(CONF_VALVE_INPUT_ACC1, SWITCH_to_CLOSE, self.settings.entity_valve_input_acc1):
                            LOGGER.debug("Valve input to ACC 1 was closed")
                    else:
                        LOGGER.debug("Valve input to ACC 1 closing delayed - waiting for timer")

    # ******************************************************************************************************
    # *** OVLÁDANIE VENTILU NA VSTUPE DO ACC 2 *************************************************************
    # ******************************************************************************************************
            self.valve_input_acc2_flag = 0
            if (acc2_enable):
                # Otvara len ten ventil ktoreho ACC je chladnejsi, ak su teploty v oboch ACC rovnake, otvori obidva ventily
                # Tento ventil sa otvori aj vtedy ak by ACC druheho ventilu bol vypnuty
                if ((self.preferred_input_ACC==0) or (self.preferred_input_ACC==2) or (not acc1_enable)):
                    if (self.settings.valve_input_acc_strict_mode == VALVE_MODE_GENERIC):
                        self.valve_input_acc2_flag = 1
                    elif (self.settings.valve_input_acc_strict_mode == VALVE_MODE_MODERATE):
                        if(not self.hp_dhw):
                            self.valve_input_acc2_flag = 1
                    elif (self.settings.valve_input_acc_strict_mode == VALVE_MODE_STRICT):
                        if(not self.hp_dhw):
                            if(self.heating_operating_mode==HEATING_OPERATING_MODE_MANUAL):
                                if (self.heating_source_input_on_off):
                                    self.valve_input_acc2_flag = 1
                            elif (self.heating_operating_mode==HEATING_OPERATING_MODE_DHW):
                                self.valve_input_acc2_flag = 0
                            elif (self.heating_operating_mode==HEATING_OPERATING_MODE_PDHW_DHW):
                                self.valve_input_acc2_flag = 0
                            else:
                                if (self.controll_command_hp_on_off):
                                    self.valve_input_acc2_flag = 1
                        else:
                            if(self.heating_operating_mode==HEATING_OPERATING_MODE_DHW_ACC):
                                self.valve_input_acc2_flag = 0
                    else:
                        LOGGER.error("Value in 'self.settings.valve_input_acc_strict_mode' = '%s' is invalid.",
                                self.settings.valve_input_acc_strict_mode)

            # **** Ovládanie ventilu *******************************************************************
            if (self.valve_input_acc2_flag):
                if (valve_input_acc2.state == STATE_CLOSED):
                    if await self._call_valve_service(CONF_VALVE_INPUT_ACC2, SWITCH_to_OPEN, self.settings.entity_valve_input_acc2):
                        LOGGER.debug("Valve input to ACC 2 was opened")
            else:
                if (valve_input_acc2.state == STATE_OPEN):
                    # Zatvorenie ventilu len ak je povolené (časovač vypršal alebo TČ je zapnuté)
                    if self._valve_input_acc_closing_allowed:
                        if await self._call_valve_service(CONF_VALVE_INPUT_ACC2, SWITCH_to_CLOSE, self.settings.entity_valve_input_acc2):
                            LOGGER.debug("Valve input to ACC 2 was closed")
                    else:
                        LOGGER.debug("Valve input to ACC 2 closing delayed - waiting for timer")

    # ******************************************************************************************************
    # *** OVLÁDANIE VENTILU Z ACC KTORÝ PREPÍNA BUĎ DO KÚRENIA, ALEBO DO DHW *****
    # ******************************************************************************************************

            self.valve_from_acc_to_heat_or_dhw_flag = 0
            if (not self.heat_dhw_from_acc):
                self.valve_from_acc_to_heat_or_dhw_flag = 1

            # **** Ovládanie ventilu *******************************************************************
            if (self.valve_from_acc_to_heat_or_dhw_flag):
                if (valve_from_acc_to_heat_or_dhw.state == STATE_ACC_DHW):
                    if await self._call_valve_service(CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW, SWITCH_ACC_to_HEATING, self.settings.entity_valve_from_acc_to_heat_or_dhw):
                        LOGGER.debug("Valve from ACC was switched to Heating")
            else:
                if (valve_from_acc_to_heat_or_dhw.state == STATE_ACC_HEATING):
                    if await self._call_valve_service(CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW, SWITCH_ACC_to_DHW, self.settings.entity_valve_from_acc_to_heat_or_dhw):
                        LOGGER.debug("Valve from ACC was switched to DHW")

    # ******************************************************************************************************
    # *** OVLÁDANIE VENTILU NA VÝSTUPE DO KÚRENIA DO DOMU **************************************************
    # ******************************************************************************************************
            
            # ak nebezi precerpavanie
            if (not self.heat_dhw_from_acc):

                self.valve_output_heating_flag = 0
                if (self.settings.valve_output_acc_strict_mode == VALVE_MODE_STRICT):

                    if (not self.hp_dhw):
                        if (thermostat_state.state == STATE_ON):
                            self.valve_output_heating_flag = 1
                        else:
                            self.valve_output_heating_flag = 0
                    elif (self.hp_dhw):
                        if (heating_state.state == STATE_ON):
                            self.valve_output_heating_flag = 1

                else:
                    if (thermostat_state.state == STATE_ON):
                        self.valve_output_heating_flag = 1
                    else:
                        self.valve_output_heating_flag = 0
                            
                # **** Ovládanie ventilu *******************************************************************

                if (self.valve_output_heating_flag):
                    if (valve_output_heating.state == STATE_CLOSED):
                        if await self._call_valve_service(CONF_VALVE_OUTPUT_HEATING, SWITCH_to_OPEN, self.settings.entity_valve_output_heating):
                            LOGGER.debug("Valve for heating output was open")
                else:
                    if (valve_output_heating.state == STATE_OPEN):
                        if await self._call_valve_service(CONF_VALVE_OUTPUT_HEATING, SWITCH_to_CLOSE, self.settings.entity_valve_output_heating):
                            LOGGER.debug("Valve for heating output was closed") 

    # ******************************************************************************************************
    # *** OVLÁDANIE OBEHOVÉHO ČERPADLA NA VÝSTUPE ACC ******************************************************
    # ******************************************************************************************************

            self.water_pump_acc_output_flag = 0
            if (self.heat_dhw_from_acc):
                if (
                    ((valve_output_acc1.state == STATE_OPEN) or (valve_output_acc2.state == STATE_OPEN)) and
                    (valve_from_acc_to_heat_or_dhw.state == STATE_ACC_DHW)
                    ):
                        self.water_pump_acc_output_flag = 1
            else:
                if (self.settings.auxiliary_water_pump_for_heating == AUXILIARY_PUMP_ENABLE):
                    if (heating_state.state == STATE_ON):
                        if (
                            ((valve_output_acc1.state == STATE_OPEN) or (valve_output_acc2.state == STATE_OPEN)) and
                            (valve_from_acc_to_heat_or_dhw.state == STATE_ACC_HEATING) and
                            (valve_output_heating.state == STATE_OPEN)
                            ):
                                self.water_pump_acc_output_flag = 1
                # V BOOSTER režime sa pumpa ovláda v sekcii "OVLÁDANIE OBEHOVÉHO ČERPADLA NA VÝSTUPE DO KÚRENIA"

                # **** Ovládanie obehového čerpadla *******************************************************************

            # V BOOSTER režime sa pumpa neovláda tu, ale v sekcii heating
            if (self.settings.auxiliary_water_pump_for_heating != AUXILIARY_PUMP_BOOSTER):
                if (self.water_pump_acc_output_flag):
                    if (water_pump_acc_output.state != STATE_ON):
                        await self.hass.services.async_call(
                            "switch", TURN_ON, {"entity_id": self.settings.entity_water_pump_acc_output}
                        )
                        LOGGER.debug("The water pump at the ACC output was turned on")
                else:
                    if (water_pump_acc_output.state != STATE_OFF):
                        await self.hass.services.async_call(
                            "switch", TURN_OFF, {"entity_id": self.settings.entity_water_pump_acc_output}
                        )
                        LOGGER.debug("The water pump at the ACC output was turned off")

    # ******************************************************************************************************
    # *** OVLÁDANIE OBEHOVÉHO ČERPADLA PRE PODLAHOVÉ KÚRENIE ***********************************************
    # ******************************************************************************************************

            self.water_pump_floor_heating_flag = 0
            if (podlahove_stav.state == STATE_ON):
                if (not self.heat_dhw_from_acc):
                    if (
                        ((valve_output_acc1.state == STATE_OPEN) or (valve_output_acc2.state == STATE_OPEN)) and
                        (valve_from_acc_to_heat_or_dhw.state == STATE_OPEN) and
                        (valve_output_heating.state == STATE_OPEN)
                        ):
                            self.water_pump_floor_heating_flag = 1

            if (self.water_pump_floor_heating_flag):
                if (water_pump_floor_heating.state != STATE_ON):
                    await self.hass.services.async_call(
                        "switch", TURN_ON, {"entity_id": self.settings.entity_water_pump_floor_heating}
                    )
                    LOGGER.debug("The water pump for floor heating was turned on")
            else:
                if (water_pump_floor_heating.state != STATE_OFF):
                    await self.hass.services.async_call(
                        "switch", TURN_OFF, {"entity_id": self.settings.entity_water_pump_floor_heating}
                    )
                    LOGGER.debug("The water pump for floor heating was turned off")

    # ******************************************************************************************************
    # *** OVLÁDANIE OBEHOVÉHO ČERPADLA NA VÝSTUPE DO KÚRENIA ***********************************************
    # ******************************************************************************************************

            self.water_pump_heating_flag = 0
            if (heating_state.state == STATE_ON):
                if (not self.heat_dhw_from_acc):
                    if (
                        ((valve_output_acc1.state == STATE_OPEN) or (valve_output_acc2.state == STATE_OPEN)) and
                        (valve_from_acc_to_heat_or_dhw.state == STATE_OPEN) and
                        (valve_output_heating.state == STATE_OPEN)
                        ):
                            self.water_pump_heating_flag = 1

            if (self.water_pump_heating_flag):
                if (water_pump_heating.state != STATE_ON):
                    await self.hass.services.async_call(
                        "switch", TURN_ON, {"entity_id": self.settings.entity_water_pump_heating}
                    )
                    LOGGER.debug("Water Pump for heating was turned on")
                    
                if (self.settings.auxiliary_water_pump_for_heating == AUXILIARY_PUMP_ENABLE):
                    if (water_pump_acc_output.state != STATE_ON):
                        await self.hass.services.async_call(
                            "switch", TURN_ON, {"entity_id": self.settings.entity_water_pump_acc_output}
                        )
                        LOGGER.debug("Auxiliary water pump for heating was turned on (ENABLE mode)")
                elif (self.settings.auxiliary_water_pump_for_heating == AUXILIARY_PUMP_BOOSTER):
                    # V BOOSTER režime: zapnúť pumpu len ak booster ešte neprebehol
                    # Stavy: 
                    #   - _booster_finished == False, _booster_active == False: môže sa spustiť
                    #   - _booster_active == True: timer beží, pumpa zostáva zapnutá
                    #   - _booster_finished == True: booster už prebehol, pumpa sa nezapne
                    if not self._auxiliary_pump_booster_finished and not self._auxiliary_pump_booster_active:
                        # Prvé spustenie boostera - zapnúť pumpu a spustiť časovač
                        if (water_pump_acc_output.state != STATE_ON):
                            await self.hass.services.async_call(
                                "switch", TURN_ON, {"entity_id": self.settings.entity_water_pump_acc_output}
                            )
                        self._auxiliary_pump_booster_active = True
                        # Spustiť nový časovač
                        self._auxiliary_pump_booster_timer = async_call_later(
                            self.hass,
                            self.settings.auxiliary_pump_booster_time * 60,  # konverzia minút na sekundy
                            self._booster_timer_finished
                        )
                        LOGGER.debug("Auxiliary water pump for heating was turned on (BOOSTER mode) - timer started for %d minutes", self.settings.auxiliary_pump_booster_time)
                    # Ak je booster aktívny (timer beží) alebo už prebehol, nič nerobíme
            else:
                if (water_pump_heating.state != STATE_OFF):
                    await self.hass.services.async_call(
                        "switch", TURN_OFF, {"entity_id": self.settings.entity_water_pump_heating}
                    )
                    LOGGER.debug("Water pump for heating was turned off")
                    
                if (self.settings.auxiliary_water_pump_for_heating == AUXILIARY_PUMP_ENABLE):
                    if (not self.heat_dhw_from_acc):
                        if (water_pump_acc_output.state != STATE_OFF):
                            await self.hass.services.async_call(
                                "switch", TURN_OFF, {"entity_id": self.settings.entity_water_pump_acc_output}
                            )
                            LOGGER.debug("Auxiliary water pump for heating was turned off (ENABLE mode)")
                elif (self.settings.auxiliary_water_pump_for_heating == AUXILIARY_PUMP_BOOSTER):
                    if (not self.heat_dhw_from_acc):
                        if (water_pump_acc_output.state != STATE_OFF):
                            await self.hass.services.async_call(
                                "switch", TURN_OFF, {"entity_id": self.settings.entity_water_pump_acc_output}
                            )
                            LOGGER.debug("Auxiliary water pump for heating was turned off (BOOSTER mode)")
                    # Zrušiť booster časovač a resetovať všetky stavy (aby sa mohol znovu spustiť pri ďalšom zapnutí)
                    if self._auxiliary_pump_booster_timer:
                        self._auxiliary_pump_booster_timer()
                        self._auxiliary_pump_booster_timer = None
                        LOGGER.debug("Booster timer cancelled - heating turned off")
                    self._auxiliary_pump_booster_active = False
                    self._auxiliary_pump_booster_finished = False  # Reset - pri ďalšom zapnutí heating sa booster spustí znova

# ******************************************************************************************
# ********************** KONIEC LOGIKY CONTROLLERA *****************************************
# ******************************************************************************************

            async_dispatcher_send(self.hass, f"{DOMAIN}_feedback_update_{self._entry_id}")
            LOGGER.debug("Control cycle completed with sucess")
            
        except Exception as e:
            LOGGER.error(f"Error !!! {e}")
            return

        finally:
            self._is_running = False

# ******************************************************************************************
# ************************ Pomocné metódy **************************************************
# ******************************************************************************************

    # prepne sa na ohrev TUV
    async def switch_to_dhw(self):
        self.hp_dhw = True
        self.hp_acc = False
        if(self.hass.states.is_state(self.SWITCH_ENTITY_HP_ACC, STATE_ON)):
            await self.hass.services.async_call("switch", TURN_ON, {"entity_id": self.SWITCH_ENTITY_HP_DHW})

    # prepne sa na ohrev ACC
    async def switch_to_acc(self):
        self.hp_dhw = False
        self.hp_acc = True
        if(self.hass.states.is_state(self.SWITCH_ENTITY_HP_DHW, STATE_ON)):
            await self.hass.services.async_call("switch", TURN_ON, {"entity_id": self.SWITCH_ENTITY_HP_ACC})

    # Zapne precerpavanie z ACC do TUV
    async def start_heat_dhw_from_acc(self):
        self.heat_dhw_from_acc = True
        if(self.hass.states.get(self.SWITCH_ENTITY_HEAT_DHW_FROM_ACC).state != STATE_ON):
            await self.hass.services.async_call("switch", TURN_ON, {"entity_id": self.SWITCH_ENTITY_HEAT_DHW_FROM_ACC})

    # Stopne precerpavanie z ACC do TUV
    async def stop_heat_dhw_from_acc(self):
        self.heat_dhw_from_acc = False
        if(self.hass.states.get(self.SWITCH_ENTITY_HEAT_DHW_FROM_ACC).state != STATE_OFF):
            await self.hass.services.async_call("switch", TURN_OFF, {"entity_id": self.SWITCH_ENTITY_HEAT_DHW_FROM_ACC})

    async def _call_valve_service(self, valve_key: str, service: str, entity_id: str) -> bool:
        """
        Zavolá službu pre ventil s debounce kontrolou.
        Ak je príkaz zablokovaný, naplánuje rerun kontrolného cyklu.
        
        Args:
            valve_key: Kľúč ventilu v _valve_last_command_time
            service: SWITCH_to_OPEN alebo SWITCH_to_CLOSE
            entity_id: Entity ID ventilu
            
        Returns:
            True ak bol príkaz odoslaný, False ak bol zablokovaný debounce
        """
        current_time = time.time()
        last_time = self._valve_last_command_time.get(valve_key, 0)
        time_since_last = current_time - last_time
        
        if time_since_last < self.settings.valve_timeout:
            # Príkaz zablokovaný - naplánovať rerun
            remaining_time = self.settings.valve_timeout - time_since_last
            LOGGER.debug(f"Valve {valve_key} debounce active, skipping {service}, scheduling rerun in {remaining_time:.2f}s")
            self._schedule_rerun(remaining_time)
            return False
        
        await self.hass.services.async_call("cover", service, {"entity_id": entity_id})
        self._valve_last_command_time[valve_key] = current_time
        return True

    def _schedule_rerun(self, delay: float) -> None:
        """
        Naplánuje rerun kontrolného cyklu po uplynutí delay.
        Ak už je naplánovaný skorší rerun, ponechá ho.
        """
        # Zrušiť existujúci scheduled rerun ak je neskôr ako nový
        if self._scheduled_rerun is not None:
            # Už máme naplánovaný rerun, netreba plánovať ďalší
            return
        
        @callback
        def _rerun_callback(_now=None):
            """Callback pre naplánovaný rerun."""
            self._scheduled_rerun = None
            LOGGER.debug("Scheduled rerun triggered")
            self.hass.async_create_task(self.heating_control_system())
        
        self._scheduled_rerun = async_call_later(self.hass, delay, _rerun_callback)
        LOGGER.debug(f"Scheduled rerun in {delay:.2f}s")

    @callback
    def _booster_timer_finished(self, _now=None):
        """Callback volaný keď uplynie booster časovač."""
        LOGGER.info("Auxiliary pump booster timer finished - turning off pump")
        self._auxiliary_pump_booster_timer = None
        self._auxiliary_pump_booster_active = False
        self._auxiliary_pump_booster_finished = True  # Označiť že booster prebehol - pumpa sa už nezapne
        # Vypnúť auxiliary pump
        self.hass.async_create_task(self._turn_off_auxiliary_pump())

    async def _turn_off_auxiliary_pump(self):
        """Vypne auxiliary pump po uplynutí booster časovača."""
        try:
            water_pump_acc_output = self.hass.states.get(self.settings.entity_water_pump_acc_output)
            if water_pump_acc_output and water_pump_acc_output.state != STATE_OFF:
                await self.hass.services.async_call(
                    "switch", TURN_OFF, {"entity_id": self.settings.entity_water_pump_acc_output}
                )
                LOGGER.debug("Auxiliary water pump turned off by booster timer")
        except Exception as e:
            LOGGER.error(f"Error turning off auxiliary pump: {e}")

    async def _set_hp_on_off_with_debounce(self, new_value: str) -> None:
        """
        Nastaví hodnotu HP ON/OFF s debounce oneskorením.
        Pri každej zmene sa časovač resetuje.
        
        Args:
            new_value: Nová hodnota (STATE_ON alebo STATE_OFF)
        """
        # Ak sa hodnota zmenila, uložíme si ju a resetujeme časovač
        if self._hp_on_off_pending_value != new_value:
            self._hp_on_off_pending_value = new_value
            
            # Zrušiť existujúci časovač ak beží
            if self._hp_on_off_debounce_timer is not None:
                self._hp_on_off_debounce_timer()
                self._hp_on_off_debounce_timer = None
                LOGGER.debug(f"HP ON/OFF debounce timer reset due to value change to {new_value}")
            
            # Spustiť nový časovač
            @callback
            def _debounce_timer_finished(_now=None):
                """Callback volaný keď uplynie debounce časovač."""
                self._hp_on_off_debounce_timer = None
                # Nastaviť hodnotu
                self.sensor_states[ENTITY_CONTROL_COMMAND_HP_ON_OFF] = self._hp_on_off_pending_value
                LOGGER.debug(f"HP ON/OFF debounce timer finished - value set to {self._hp_on_off_pending_value}")
                # Odoslať update
                async_dispatcher_send(self.hass, f"{DOMAIN}_feedback_update_{self._entry_id}")
            
            self._hp_on_off_debounce_timer = async_call_later(
                self.hass,
                self.settings.heating_source_command_debounce_delay,
                _debounce_timer_finished
            )
            LOGGER.debug(f"HP ON/OFF debounce timer started for {self.settings.heating_source_command_debounce_delay}s, pending value: {new_value}")
        else:
            LOGGER.debug(f"HP ON/OFF value unchanged ({new_value}), timer continues")

    @callback
    def _valve_input_acc_closing_delay_finished(self, _now=None):
        """Callback volaný keď uplynie časovač oneskorenia zatvorenia ventilov na vstupoch do ACC."""
        LOGGER.info("Valve input ACC closing delay timer finished - closing now allowed")
        self._valve_input_acc_closing_delay_timer = None
        self._valve_input_acc_closing_allowed = True
        # Spustiť kontrolný cyklus aby sa ventily zatvorili
        self.hass.async_create_task(self.heating_control_system())

    @callback
    def _hp_dhw_to_acc_delay_finished(self, _now=None):
        """Callback volaný keď uplynie časovač oneskorenia pretočenia ventilu hp_dhw z TUV na ACC."""
        LOGGER.info("HP DHW to ACC switch delay timer finished - switch now allowed")
        self._hp_dhw_to_acc_delay_timer = None
        self._hp_dhw_to_acc_switch_allowed = True
        # Spustiť kontrolný cyklus aby sa ventil pretočil
        self.hass.async_create_task(self.heating_control_system())