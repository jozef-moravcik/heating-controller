from __future__ import annotations
"""The Heating Controller integration"""
"""Author: Jozef Moravcik"""
"""email: jozef.moravcik@moravcik.eu"""

""" __init__.py """

import asyncio
import logging
import sys
import importlib
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.template import Template
from homeassistant.helpers.event import async_call_later, async_track_time_interval, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from datetime import timedelta

# Tieto importy sa načítajú dynamicky v async_setup_entry
# from .heating_controller import Heating_Controller_Instance
# from .const import *

# Dočasný import DOMAIN pre použitie pred dynamickým loadom
DOMAIN = "heating_controller"

LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.NUMBER, Platform.SELECT]


def _reload_integration_modules():
    """Vymaže a znovu načíta všetky moduly integrácie."""
    modules_to_reload = [key for key in sys.modules if key.startswith(f"custom_components.{DOMAIN}")]
    for module_name in modules_to_reload:
        del sys.modules[module_name]
        LOGGER.debug(f"Removed module from cache: {module_name}")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Heating Controller from configuration.yaml."""
    if DOMAIN not in config:
        return True

    # Import from configuration.yaml
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=config[DOMAIN]
        )
    )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heating Controller from a config entry."""
    
    # Reload modulov pre načítanie nového kódu bez reštartu HA
    _reload_integration_modules()
    
    # Dynamický import po vymazaní cache
#    const_module = importlib.import_module(f"custom_components.{DOMAIN}.const")
#    hc_module = importlib.import_module(f"custom_components.{DOMAIN}.heating_controller")
    
    const_module = await hass.async_add_executor_job(
        importlib.import_module, f"custom_components.{DOMAIN}.const"
    )
    hc_module = await hass.async_add_executor_job(
        importlib.import_module, f"custom_components.{DOMAIN}.heating_controller"
    )

    # Import všetkých konstánt z const modulu do lokálneho namespace
    globals().update({k: v for k, v in const_module.__dict__.items() if not k.startswith('_')})
    
    Heating_Controller_Instance = hc_module.Heating_Controller_Instance

    # Načítanie základných konfiguračných parametrov
    timeout_for_heat_dhw_from_acc = entry.options.get(
        CONF_TIMEOUT_HEAT_DHW,
        entry.data.get(CONF_TIMEOUT_HEAT_DHW, DEFAULT_TIMEOUT_HEAT_DHW)
    )
    temperature_delta_limit_acc_dhw = entry.options.get(
        CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW,
        entry.data.get(CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW, DEFAULT_TEMPERATURE_DELTA_LIMIT_ACC_DHW)
    )
    disabled_acc_temperature_limit = entry.options.get(
        CONF_DISABLED_ACC_TEMPERATURE_LIMIT,
        entry.data.get(CONF_DISABLED_ACC_TEMPERATURE_LIMIT, DEFAULT_DISABLED_ACC_TEMPERATURE_LIMIT)
    )
    min_temperature_for_heating = entry.options.get(
        CONF_MIN_TEMPERATURE_FOR_HEATING,
        entry.data.get(CONF_MIN_TEMPERATURE_FOR_HEATING, DEFAULT_MIN_TEMPERATURE_FOR_HEATING)
    )
    temperature_delta_limit_in_acc = entry.options.get(
        CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC,
        entry.data.get(CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC, DEFAULT_TEMPERATURE_DELTA_LIMIT_IN_ACC)
    )
    heating_source_temp_hysteresis = entry.options.get(
        CONF_HEATING_SOURCE_TEMP_HYSTERESIS,
        entry.data.get(CONF_HEATING_SOURCE_TEMP_HYSTERESIS, DEFAULT_HEATING_SOURCE_TEMP_HYSTERESIS)
    )
    heating_source_command_debounce_delay = entry.options.get(
        CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY,
        entry.data.get(CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY, DEFAULT_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY)
    )
    auxiliary_water_pump_for_heating = entry.options.get(
        CONF_AUXILIARY_WATER_PUMP_FOR_HEATING,
        entry.data.get(CONF_AUXILIARY_WATER_PUMP_FOR_HEATING, DEFAULT_AUXILIARY_WATER_PUMP_FOR_HEATING)
    )
    auxiliary_pump_booster_time = entry.options.get(
        CONF_AUXILIARY_PUMP_BOOSTER_TIME,
        entry.data.get(CONF_AUXILIARY_PUMP_BOOSTER_TIME, DEFAULT_AUXILIARY_PUMP_BOOSTER_TIME)
    )

    # Načítanie parametrov pre ovládanie ventilov
    valve_output_acc_strict_mode = entry.options.get(
        CONF_VALVE_OUTPUT_ACC_STRICT_MODE,
        entry.data.get(CONF_VALVE_OUTPUT_ACC_STRICT_MODE, DEFAULT_VALVE_OUTPUT_ACC_STRICT_MODE)
    )
    valve_input_acc_strict_mode = entry.options.get(
        CONF_VALVE_INPUT_ACC_STRICT_MODE,
        entry.data.get(CONF_VALVE_INPUT_ACC_STRICT_MODE, DEFAULT_VALVE_INPUT_ACC_STRICT_MODE)
    )
    valve_input_acc_closing_delay_when_heating_source_stop = entry.options.get(
        CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP,
        entry.data.get(CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP, DEFAULT_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP)
    )
    valve_timeout = entry.options.get(
        CONF_VALVE_TIMEOUT,
        entry.data.get(CONF_VALVE_TIMEOUT, DEFAULT_VALVE_TIMEOUT)
    )
        
    # Načítanie entít ventilov z konfigurácie
    entity_valve_from_hp_to_acc_or_dhw = entry.options.get(
        CONF_VALVE_FROM_TC_TO_ACC_OR_DHW,
        entry.data.get(CONF_VALVE_FROM_TC_TO_ACC_OR_DHW, DEFAULT_ENTITY_VALVE_FROM_TC_TO_ACC_OR_DHW)
    )
    entity_valve_output_acc1 = entry.options.get(
        CONF_VALVE_OUTPUT_ACC1,
        entry.data.get(CONF_VALVE_OUTPUT_ACC1, DEFAULT_ENTITY_VALVE_OUTPUT_ACC1)
    )
    entity_valve_output_acc2 = entry.options.get(
        CONF_VALVE_OUTPUT_ACC2,
        entry.data.get(CONF_VALVE_OUTPUT_ACC2, DEFAULT_ENTITY_VALVE_OUTPUT_ACC2)
    )
    entity_valve_input_acc1 = entry.options.get(
        CONF_VALVE_INPUT_ACC1,
        entry.data.get(CONF_VALVE_INPUT_ACC1, DEFAULT_ENTITY_VALVE_INPUT_ACC1)
    )
    entity_valve_input_acc2 = entry.options.get(
        CONF_VALVE_INPUT_ACC2,
        entry.data.get(CONF_VALVE_INPUT_ACC2, DEFAULT_ENTITY_VALVE_INPUT_ACC2)
    )
    entity_valve_from_acc_to_heat_or_dhw = entry.options.get(
        CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW,
        entry.data.get(CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW, DEFAULT_ENTITY_VALVE_FROM_ACC_TO_HEAT_OR_DHW)
    )
    entity_valve_output_heating = entry.options.get(
        CONF_VALVE_OUTPUT_HEATING,
        entry.data.get(CONF_VALVE_OUTPUT_HEATING, DEFAULT_ENTITY_VALVE_OUTPUT_HEATING)
    )

    # Načítanie entít teplotných senzorov z konfigurácie
    entity_temp_acc1 = entry.options.get(
        CONF_SENSOR_TEMP_ACC1,
        entry.data.get(CONF_SENSOR_TEMP_ACC1, DEFAULT_ENTITY_TEMP_ACC1)
    )
    entity_temp_acc2 = entry.options.get(
        CONF_SENSOR_TEMP_ACC2,
        entry.data.get(CONF_SENSOR_TEMP_ACC2, DEFAULT_ENTITY_TEMP_ACC2)
    )
    entity_temp_dhw = entry.options.get(
        CONF_SENSOR_TEMP_DHW,
        entry.data.get(CONF_SENSOR_TEMP_DHW, DEFAULT_ENTITY_TEMP_DHW)
    )
    
    # Načítanie entít obehových čerpadiel z konfigurácie
    entity_water_pump_acc_output = entry.options.get(
        CONF_WATER_PUMP_ACC_OUTPUT,
        entry.data.get(CONF_WATER_PUMP_ACC_OUTPUT, DEFAULT_ENTITY_WATER_PUMP_ACC_OUTPUT)
    )
    entity_water_pump_dhw = entry.options.get(
        CONF_WATER_PUMP_DHW,
        entry.data.get(CONF_WATER_PUMP_DHW, DEFAULT_ENTITY_WATER_PUMP_DHW)
    )
    entity_water_pump_floor_heating = entry.options.get(
        CONF_WATER_PUMP_FLOOR_HEATING,
        entry.data.get(CONF_WATER_PUMP_FLOOR_HEATING, DEFAULT_ENTITY_WATER_PUMP_FLOOR_HEATING)
    )
    entity_water_pump_heating = entry.options.get(
        CONF_WATER_PUMP_HEATING,
        entry.data.get(CONF_WATER_PUMP_HEATING, DEFAULT_ENTITY_WATER_PUMP_HEATING)
    )
    
    # Načítanie entít stavov termostatov a tepelného čerpadla z konfigurácie
    entity_thermostat_state = entry.options.get(
        CONF_THERMOSTAT_STATE,
        entry.data.get(CONF_THERMOSTAT_STATE, DEFAULT_ENTITY_THERMOSTAT_STATE)
    )
    entity_heating_state = entry.options.get(
        CONF_HEATING_STATE,
        entry.data.get(CONF_HEATING_STATE, DEFAULT_ENTITY_HEATING_STATE)
    )
    entity_floor_heating_state = entry.options.get(
        CONF_FLOOR_HEATING_STATE,
        entry.data.get(CONF_FLOOR_HEATING_STATE, DEFAULT_ENTITY_FLOOR_HEATING_STATE)
    )

# ******************************************************************************************
# **** Uloženie všetkých nastavení do inštancie a do "core.config_entries"******************
# ******************************************************************************************    
    instance = Heating_Controller_Instance()
    # Nastavenie hass objektu a entry_id do inštancie
    instance.hass = hass
    instance._entry_id = entry.entry_id
    
    # Nastavenia základných parametrov
    instance.settings.timeout_for_heat_dhw_from_acc = timeout_for_heat_dhw_from_acc
    instance.settings.temperature_delta_limit_acc_dhw = temperature_delta_limit_acc_dhw
    instance.settings.disabled_acc_temperature_limit = disabled_acc_temperature_limit
    instance.settings.min_temperature_for_heating = min_temperature_for_heating
    instance.settings.temperature_delta_limit_in_acc = temperature_delta_limit_in_acc
    instance.settings.heating_source_temp_hysteresis = heating_source_temp_hysteresis
    instance.settings.heating_source_command_debounce_delay = heating_source_command_debounce_delay
    instance.settings.auxiliary_water_pump_for_heating = int(auxiliary_water_pump_for_heating)
    instance.settings.auxiliary_pump_booster_time = auxiliary_pump_booster_time
    # Nastavenie parametrov pre ovládanie ventilov
    instance.settings.valve_output_acc_strict_mode = int(valve_output_acc_strict_mode)
    instance.settings.valve_input_acc_strict_mode = int(valve_input_acc_strict_mode)
    instance.settings.valve_input_acc_closing_delay_when_heating_source_stop = valve_input_acc_closing_delay_when_heating_source_stop
    instance.settings.valve_timeout = valve_timeout
    # Entity ventilov
    instance.settings.entity_valve_from_hp_to_acc_or_dhw = entity_valve_from_hp_to_acc_or_dhw
    instance.settings.entity_valve_output_acc1 = entity_valve_output_acc1
    instance.settings.entity_valve_output_acc2 = entity_valve_output_acc2
    instance.settings.entity_valve_input_acc1 = entity_valve_input_acc1
    instance.settings.entity_valve_input_acc2 = entity_valve_input_acc2
    instance.settings.entity_valve_from_acc_to_heat_or_dhw = entity_valve_from_acc_to_heat_or_dhw
    instance.settings.entity_valve_output_heating = entity_valve_output_heating
    # Entity teplotných senzorov
    instance.settings.entity_temp_acc1 = entity_temp_acc1
    instance.settings.entity_temp_acc2 = entity_temp_acc2
    instance.settings.entity_temp_dhw = entity_temp_dhw
    # Entity obehových čerpadiel
    instance.settings.entity_water_pump_acc_output = entity_water_pump_acc_output
    instance.settings.entity_water_pump_dhw = entity_water_pump_dhw
    instance.settings.entity_water_pump_floor_heating = entity_water_pump_floor_heating
    instance.settings.entity_water_pump_heating = entity_water_pump_heating
    # Entity stavov termostatov a tepelného čerpadla
    instance.settings.entity_thermostat_state = entity_thermostat_state
    instance.settings.entity_heating_state = entity_heating_state
    instance.settings.entity_floor_heating_state = entity_floor_heating_state

    try:
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {
            "instance": instance,
            CONF_TIMEOUT_HEAT_DHW: timeout_for_heat_dhw_from_acc,
            CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW: temperature_delta_limit_acc_dhw,
            CONF_DISABLED_ACC_TEMPERATURE_LIMIT: disabled_acc_temperature_limit,
            CONF_MIN_TEMPERATURE_FOR_HEATING: min_temperature_for_heating,
            CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC: temperature_delta_limit_in_acc,
            CONF_HEATING_SOURCE_TEMP_HYSTERESIS: heating_source_temp_hysteresis,
            CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY: heating_source_command_debounce_delay,
            CONF_AUXILIARY_WATER_PUMP_FOR_HEATING: auxiliary_water_pump_for_heating,
            CONF_AUXILIARY_PUMP_BOOSTER_TIME: auxiliary_pump_booster_time,
            CONF_VALVE_OUTPUT_ACC_STRICT_MODE: valve_output_acc_strict_mode,
            CONF_VALVE_INPUT_ACC_STRICT_MODE: valve_input_acc_strict_mode,
            CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP: valve_input_acc_closing_delay_when_heating_source_stop,
            CONF_VALVE_TIMEOUT: valve_timeout,
            CONF_VALVE_FROM_TC_TO_ACC_OR_DHW: entity_valve_from_hp_to_acc_or_dhw,
            CONF_VALVE_OUTPUT_ACC1: entity_valve_output_acc1,
            CONF_VALVE_OUTPUT_ACC2: entity_valve_output_acc2,
            CONF_VALVE_INPUT_ACC1: entity_valve_input_acc1,
            CONF_VALVE_INPUT_ACC2: entity_valve_input_acc2,
            CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW: entity_valve_from_acc_to_heat_or_dhw,
            CONF_VALVE_OUTPUT_HEATING: entity_valve_output_heating,
            CONF_SENSOR_TEMP_ACC1: entity_temp_acc1,
            CONF_SENSOR_TEMP_ACC2: entity_temp_acc2,
            CONF_SENSOR_TEMP_DHW: entity_temp_dhw,
            CONF_WATER_PUMP_ACC_OUTPUT: entity_water_pump_acc_output,
            CONF_WATER_PUMP_DHW: entity_water_pump_dhw,
            CONF_WATER_PUMP_FLOOR_HEATING: entity_water_pump_floor_heating,
            CONF_WATER_PUMP_HEATING: entity_water_pump_heating,
            CONF_THERMOSTAT_STATE: entity_thermostat_state,
            CONF_HEATING_STATE: entity_heating_state,
            CONF_FLOOR_HEATING_STATE: entity_floor_heating_state,
        }

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Registrácia služieb
        if not hass.services.has_service(DOMAIN, SERVICE_SYSTEM_STARTED):
            hass.services.async_register(
                DOMAIN,
                SERVICE_SYSTEM_STARTED,
                system_started_service,
            )
        
        # Register update listener for options changes
        entry.async_on_unload(entry.add_update_listener(update_listener))
            
        async def async_update_settings_sensors(_now=None):
            """Asynchrónna aktualizácia settings senzorov."""
            async_dispatcher_send(hass, f"{DOMAIN}_settings_update_{entry.entry_id}")
        
        async def async_run_heating_control(_now=None):
            """Periodické spúšťanie heating control system."""
            await instance.heating_control_system()

        # Debounce premenné pre state_changed
        state_change_debounce = {
            "pending": False,
            "cancel_callback": None,
        }
        
        async def async_state_changed(event):
            """Reakcia na zmenu stavu sledovaných entít s debounce."""
            entity_id = event.data.get("entity_id")
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            
            # Ignoruj ak sa stav nezmenil
            if old_state and new_state and old_state.state == new_state.state:
                return
            
            LOGGER.debug(f"State change detected: {entity_id} changed from {old_state.state if old_state else 'None'} to {new_state.state if new_state else 'None'}")
            
            # Ak už je naplánované spustenie, netreba robiť nič
            if state_change_debounce["pending"]:
                LOGGER.debug("Debounce active, state change queued")
                return
            
            # Označiť že máme pending zmenu
            state_change_debounce["pending"] = True
            
            @callback
            def _debounce_callback(_now=None):
                """Callback po uplynutí debounce času."""
                state_change_debounce["pending"] = False
                state_change_debounce["cancel_callback"] = None
                LOGGER.debug("Debounce finished, running heating control system")
                hass.async_create_task(instance.heating_control_system())
            
            # Naplánovať spustenie po debounce delay
            state_change_debounce["cancel_callback"] = async_call_later(
                hass, DEBOUNCE_DELAY, _debounce_callback
            )

        # Definovanie všetkých entít ktorých stavy sú sledované
        tracked_entities = [
            # Interné entity ovládacích prvkov
            instance.SWITCH_ENTITY_AUTOMATIC_MODE,
            instance.SWITCH_ENTITY_ACC1_ENABLE,
            instance.SWITCH_ENTITY_ACC2_ENABLE,
            instance.SWITCH_ENTITY_HEAT_DHW_FROM_ACC,
            instance.SWITCH_ENTITY_HP_ACC,
            instance.SWITCH_ENTITY_HP_DHW,
            instance.SWITCH_ENTITY_HEATING_SOURCE_ON_OFF,
            instance.NUMBER_ENTITY_DHW_TARGET_TEMPERATURE,
            instance.NUMBER_ENTITY_ACC_TARGET_TEMPERATURE,
            instance.SELECT_ENTITY_HEATING_OPERATING_MODE,
            # Teplotné senzory
            entity_temp_acc1,
            entity_temp_acc2,
            entity_temp_dhw,
            # Ventily
            entity_valve_from_hp_to_acc_or_dhw,
            entity_valve_output_acc1,
            entity_valve_output_acc2,
            entity_valve_input_acc1,
            entity_valve_input_acc2,
            entity_valve_from_acc_to_heat_or_dhw,
            entity_valve_output_heating,
            # Čerpadlá
            entity_water_pump_acc_output,
            entity_water_pump_dhw,
            entity_water_pump_floor_heating,
            entity_water_pump_heating,
            # Stavy
            entity_thermostat_state,
            entity_heating_state,
            entity_floor_heating_state,
        ]

        # Odstránenie duplicít a None hodnôt
        tracked_entities = list(set(filter(None, tracked_entities)))

        # Plán jednorazových volaní
        async_call_later(hass, 2, async_update_settings_sensors)
        
        # Periodické spúšťanie heating control system každé UPDATE_INTERVAL sekúnd
        async_call_later(hass, 3, async_run_heating_control)  # Prvé spustenie po 30 sekundách
        entry.async_on_unload(

            async_track_state_change_event(
                hass,
                tracked_entities,
                async_state_changed
            )

            # async_track_time_interval(
            #     hass,
            #     async_run_heating_control,
            #     timedelta(seconds=UPDATE_INTERVAL)
            # )
        )


        # Voliteľný fallback - periodická kontrola každých 60 sekúnd pre bezpečnosť
        if hasattr(instance.settings, 'fallback_check_interval'):
            fallback_interval = instance.settings.fallback_check_interval
        else:
            fallback_interval = DEFAULT_FALLBACK_CHECK_INTERVAL  # default
            
        if fallback_interval > 0:
            LOGGER.info(f"Fallback periodic check enabled: every {fallback_interval} seconds")
            entry.async_on_unload(
                async_track_time_interval(
                    hass,
                    async_run_heating_control,
                    timedelta(seconds=fallback_interval)
                )
            )        
        
        LOGGER.info("Heating Controller configuration saved successfully")

    except Exception as ex:
        LOGGER.error("Error while configuration saving: %s", ex)
        raise ConfigEntryNotReady from ex        

    return True


async def system_started_service(call: ServiceCall) -> None:
    """Handle system started service call."""
    try:
        if DOMAIN not in call.hass.data or not call.hass.data[DOMAIN]:
            LOGGER.error("No integrations configured")
            return

        entry_id = next(iter(call.hass.data[DOMAIN].keys()))
        instance = call.hass.data[DOMAIN][entry_id].get("instance")

        if instance:
            await call.hass.async_add_executor_job(instance.system_started)

    except Exception as ex:
        LOGGER.error("Error in system_started: %s", ex)        


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""

    # Načítanie základných konfiguračných parametrov
    timeout_for_heat_dhw_from_acc = entry.options.get(
        CONF_TIMEOUT_HEAT_DHW,
        entry.data.get(CONF_TIMEOUT_HEAT_DHW, DEFAULT_TIMEOUT_HEAT_DHW)
    )
    temperature_delta_limit_acc_dhw = entry.options.get(
        CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW,
        entry.data.get(CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW, DEFAULT_TEMPERATURE_DELTA_LIMIT_ACC_DHW)
    )
    disabled_acc_temperature_limit = entry.options.get(
        CONF_DISABLED_ACC_TEMPERATURE_LIMIT,
        entry.data.get(CONF_DISABLED_ACC_TEMPERATURE_LIMIT, DEFAULT_DISABLED_ACC_TEMPERATURE_LIMIT)
    )
    min_temperature_for_heating = entry.options.get(
        CONF_MIN_TEMPERATURE_FOR_HEATING,
        entry.data.get(CONF_MIN_TEMPERATURE_FOR_HEATING, DEFAULT_MIN_TEMPERATURE_FOR_HEATING)
    )
    temperature_delta_limit_in_acc = entry.options.get(
        CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC,
        entry.data.get(CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC, DEFAULT_TEMPERATURE_DELTA_LIMIT_IN_ACC)
    )
    heating_source_temp_hysteresis = entry.options.get(
        CONF_HEATING_SOURCE_TEMP_HYSTERESIS,
        entry.data.get(CONF_HEATING_SOURCE_TEMP_HYSTERESIS, DEFAULT_HEATING_SOURCE_TEMP_HYSTERESIS)
    )
    heating_source_command_debounce_delay = entry.options.get(
        CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY,
        entry.data.get(CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY, DEFAULT_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY)
    )
    auxiliary_water_pump_for_heating = entry.options.get(
        CONF_AUXILIARY_WATER_PUMP_FOR_HEATING,
        entry.data.get(CONF_AUXILIARY_WATER_PUMP_FOR_HEATING, DEFAULT_AUXILIARY_WATER_PUMP_FOR_HEATING)
    )
    auxiliary_pump_booster_time = entry.options.get(
        CONF_AUXILIARY_PUMP_BOOSTER_TIME,
        entry.data.get(CONF_AUXILIARY_PUMP_BOOSTER_TIME, DEFAULT_AUXILIARY_PUMP_BOOSTER_TIME)
    )

    # Načítanie parametrov pre ovládanie ventilov
    valve_output_acc_strict_mode = entry.options.get(
        CONF_VALVE_OUTPUT_ACC_STRICT_MODE,
        entry.data.get(CONF_VALVE_OUTPUT_ACC_STRICT_MODE, DEFAULT_VALVE_OUTPUT_ACC_STRICT_MODE)
    )
    valve_input_acc_strict_mode = entry.options.get(
        CONF_VALVE_INPUT_ACC_STRICT_MODE,
        entry.data.get(CONF_VALVE_INPUT_ACC_STRICT_MODE, DEFAULT_VALVE_INPUT_ACC_STRICT_MODE)
    )
    valve_input_acc_closing_delay_when_heating_source_stop = entry.options.get(
        CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP,
        entry.data.get(CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP, DEFAULT_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP)
    )
    valve_timeout = entry.options.get(
        CONF_VALVE_TIMEOUT,
        entry.data.get(CONF_VALVE_TIMEOUT, DEFAULT_VALVE_TIMEOUT)
    )
        
    # Načítanie entít ventilov z konfigurácie
    entity_valve_from_hp_to_acc_or_dhw = entry.options.get(
        CONF_VALVE_FROM_TC_TO_ACC_OR_DHW,
        entry.data.get(CONF_VALVE_FROM_TC_TO_ACC_OR_DHW, DEFAULT_ENTITY_VALVE_FROM_TC_TO_ACC_OR_DHW)
    )
    entity_valve_output_acc1 = entry.options.get(
        CONF_VALVE_OUTPUT_ACC1,
        entry.data.get(CONF_VALVE_OUTPUT_ACC1, DEFAULT_ENTITY_VALVE_OUTPUT_ACC1)
    )
    entity_valve_output_acc2 = entry.options.get(
        CONF_VALVE_OUTPUT_ACC2,
        entry.data.get(CONF_VALVE_OUTPUT_ACC2, DEFAULT_ENTITY_VALVE_OUTPUT_ACC2)
    )
    entity_valve_input_acc1 = entry.options.get(
        CONF_VALVE_INPUT_ACC1,
        entry.data.get(CONF_VALVE_INPUT_ACC1, DEFAULT_ENTITY_VALVE_INPUT_ACC1)
    )
    entity_valve_input_acc2 = entry.options.get(
        CONF_VALVE_INPUT_ACC2,
        entry.data.get(CONF_VALVE_INPUT_ACC2, DEFAULT_ENTITY_VALVE_INPUT_ACC2)
    )
    entity_valve_from_acc_to_heat_or_dhw = entry.options.get(
        CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW,
        entry.data.get(CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW, DEFAULT_ENTITY_VALVE_FROM_ACC_TO_HEAT_OR_DHW)
    )
    entity_valve_output_heating = entry.options.get(
        CONF_VALVE_OUTPUT_HEATING,
        entry.data.get(CONF_VALVE_OUTPUT_HEATING, DEFAULT_ENTITY_VALVE_OUTPUT_HEATING)
    )
    
    # Načítanie entít teplotných senzorov z konfigurácie
    entity_temp_acc1 = entry.options.get(
        CONF_SENSOR_TEMP_ACC1,
        entry.data.get(CONF_SENSOR_TEMP_ACC1, DEFAULT_ENTITY_TEMP_ACC1)
    )
    entity_temp_acc2 = entry.options.get(
        CONF_SENSOR_TEMP_ACC2,
        entry.data.get(CONF_SENSOR_TEMP_ACC2, DEFAULT_ENTITY_TEMP_ACC2)
    )
    entity_temp_dhw = entry.options.get(
        CONF_SENSOR_TEMP_DHW,
        entry.data.get(CONF_SENSOR_TEMP_DHW, DEFAULT_ENTITY_TEMP_DHW)
    )
    
    # Načítanie entít obehových čerpadiel z konfigurácie
    entity_water_pump_acc_output = entry.options.get(
        CONF_WATER_PUMP_ACC_OUTPUT,
        entry.data.get(CONF_WATER_PUMP_ACC_OUTPUT, DEFAULT_ENTITY_WATER_PUMP_ACC_OUTPUT)
    )
    entity_water_pump_dhw = entry.options.get(
        CONF_WATER_PUMP_DHW,
        entry.data.get(CONF_WATER_PUMP_DHW, DEFAULT_ENTITY_WATER_PUMP_DHW)
    )
    entity_water_pump_floor_heating = entry.options.get(
        CONF_WATER_PUMP_FLOOR_HEATING,
        entry.data.get(CONF_WATER_PUMP_FLOOR_HEATING, DEFAULT_ENTITY_WATER_PUMP_FLOOR_HEATING)
    )
    entity_water_pump_heating = entry.options.get(
        CONF_WATER_PUMP_HEATING,
        entry.data.get(CONF_WATER_PUMP_HEATING, DEFAULT_ENTITY_WATER_PUMP_HEATING)
    )
    
    # Načítanie entít stavov termostatov a tepelného čerpadla z konfigurácie
    entity_thermostat_state = entry.options.get(
        CONF_THERMOSTAT_STATE,
        entry.data.get(CONF_THERMOSTAT_STATE, DEFAULT_ENTITY_THERMOSTAT_STATE)
    )
    entity_heating_state = entry.options.get(
        CONF_HEATING_STATE,
        entry.data.get(CONF_HEATING_STATE, DEFAULT_ENTITY_HEATING_STATE)
    )
    entity_floor_heating_state = entry.options.get(
        CONF_FLOOR_HEATING_STATE,
        entry.data.get(CONF_FLOOR_HEATING_STATE, DEFAULT_ENTITY_FLOOR_HEATING_STATE)
    )

# ******************************************************************************************
# **** Aktualizácia všetkých nastavení v inštancii a v  v "core.config_entries" ************
# ****************************************************************************************** 
    try:
        # Získanie inštancie
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            instance = hass.data[DOMAIN][entry.entry_id].get("instance")   
            if instance:
                # Nastavenia základných parametrov
                instance.settings.timeout_for_heat_dhw_from_acc = timeout_for_heat_dhw_from_acc
                instance.settings.temperature_delta_limit_acc_dhw = temperature_delta_limit_acc_dhw
                instance.settings.disabled_acc_temperature_limit = disabled_acc_temperature_limit
                instance.settings.min_temperature_for_heating = min_temperature_for_heating
                instance.settings.temperature_delta_limit_in_acc = temperature_delta_limit_in_acc
                instance.settings.heating_source_temp_hysteresis = heating_source_temp_hysteresis
                instance.settings.heating_source_command_debounce_delay = heating_source_command_debounce_delay
                instance.settings.auxiliary_water_pump_for_heating = int(auxiliary_water_pump_for_heating)
                instance.settings.auxiliary_pump_booster_time = auxiliary_pump_booster_time
                # Nastavenie parametrov pre ovládanie ventilov
                instance.settings.valve_output_acc_strict_mode = int(valve_output_acc_strict_mode)
                instance.settings.valve_input_acc_strict_mode = int(valve_input_acc_strict_mode)
                instance.settings.valve_input_acc_closing_delay_when_heating_source_stop = valve_input_acc_closing_delay_when_heating_source_stop
                instance.settings.valve_timeout = valve_timeout
                # Entity ventilov
                instance.settings.entity_valve_from_hp_to_acc_or_dhw = entity_valve_from_hp_to_acc_or_dhw
                instance.settings.entity_valve_output_acc1 = entity_valve_output_acc1
                instance.settings.entity_valve_output_acc2 = entity_valve_output_acc2
                instance.settings.entity_valve_input_acc1 = entity_valve_input_acc1
                instance.settings.entity_valve_input_acc2 = entity_valve_input_acc2
                instance.settings.entity_valve_from_acc_to_heat_or_dhw = entity_valve_from_acc_to_heat_or_dhw
                instance.settings.entity_valve_output_heating = entity_valve_output_heating
                # Entity teplotných senzorov
                instance.settings.entity_temp_acc1 = entity_temp_acc1
                instance.settings.entity_temp_acc2 = entity_temp_acc2
                instance.settings.entity_temp_dhw = entity_temp_dhw
                # Entity obehových čerpadiel
                instance.settings.entity_water_pump_acc_output = entity_water_pump_acc_output
                instance.settings.entity_water_pump_dhw = entity_water_pump_dhw
                instance.settings.entity_water_pump_floor_heating = entity_water_pump_floor_heating
                instance.settings.entity_water_pump_heating = entity_water_pump_heating
                # Entity stavov termostatov a tepelného čerpadla
                instance.settings.entity_thermostat_state = entity_thermostat_state
                instance.settings.entity_heating_state = entity_heating_state
                instance.settings.entity_floor_heating_state = entity_floor_heating_state
                
                # Aktualizácia všetkých údaje nastavení v "core.config_entries"
                hass.data[DOMAIN][entry.entry_id].update({
                    CONF_TIMEOUT_HEAT_DHW: timeout_for_heat_dhw_from_acc,
                    CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW: temperature_delta_limit_acc_dhw,
                    CONF_DISABLED_ACC_TEMPERATURE_LIMIT: disabled_acc_temperature_limit,
                    CONF_MIN_TEMPERATURE_FOR_HEATING: min_temperature_for_heating,
                    CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC: temperature_delta_limit_in_acc,
                    CONF_HEATING_SOURCE_TEMP_HYSTERESIS: heating_source_temp_hysteresis,
                    CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY: heating_source_command_debounce_delay,
                    CONF_AUXILIARY_WATER_PUMP_FOR_HEATING: auxiliary_water_pump_for_heating,
                    CONF_AUXILIARY_PUMP_BOOSTER_TIME: auxiliary_pump_booster_time,
                    CONF_VALVE_OUTPUT_ACC_STRICT_MODE: valve_output_acc_strict_mode,
                    CONF_VALVE_INPUT_ACC_STRICT_MODE: valve_input_acc_strict_mode,
                    CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP: valve_input_acc_closing_delay_when_heating_source_stop,
                    CONF_VALVE_TIMEOUT: valve_timeout,
                    CONF_VALVE_FROM_TC_TO_ACC_OR_DHW: entity_valve_from_hp_to_acc_or_dhw,
                    CONF_VALVE_OUTPUT_ACC1: entity_valve_output_acc1,
                    CONF_VALVE_OUTPUT_ACC2: entity_valve_output_acc2,
                    CONF_VALVE_INPUT_ACC1: entity_valve_input_acc1,
                    CONF_VALVE_INPUT_ACC2: entity_valve_input_acc2,
                    CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW: entity_valve_from_acc_to_heat_or_dhw,
                    CONF_VALVE_OUTPUT_HEATING: entity_valve_output_heating,
                    CONF_SENSOR_TEMP_ACC1: entity_temp_acc1,
                    CONF_SENSOR_TEMP_ACC2: entity_temp_acc2,
                    CONF_SENSOR_TEMP_DHW: entity_temp_dhw,
                    CONF_WATER_PUMP_ACC_OUTPUT: entity_water_pump_acc_output,
                    CONF_WATER_PUMP_DHW: entity_water_pump_dhw,
                    CONF_WATER_PUMP_FLOOR_HEATING: entity_water_pump_floor_heating,
                    CONF_WATER_PUMP_HEATING: entity_water_pump_heating,
                    CONF_THERMOSTAT_STATE: entity_thermostat_state,
                    CONF_HEATING_STATE: entity_heating_state,
                    CONF_FLOOR_HEATING_STATE: entity_floor_heating_state,
                })
                
                LOGGER.info("Heating Controller configuration updated successfully")
    except Exception as ex:
        LOGGER.error("Error while configuration update: %s", ex)
        raise ConfigEntryNotReady from ex

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id, None)

        return unload_ok

    except Exception as ex:
        LOGGER.error("Error unloading entry: %s", ex)
        # Ensure we cleanup even on error
        if DOMAIN in hass.data and entry.entry_id in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN].pop(entry.entry_id, None)
        return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)