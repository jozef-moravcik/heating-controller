from __future__ import annotations
"""The Heating Controller integration"""
"""Author: Jozef Moravcik"""
"""email: jozef.moravcik@moravcik.eu"""

""" config_flow.py """

"""Config flow for Heating Controller integration."""

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    EntitySelector,
    EntitySelectorConfig,
)
import homeassistant.helpers.config_validation as cv

from .heating_controller import Heating_Controller_Instance
from .const import *

class HeatingControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

    # Inicializačná metóda, ktorá presmeruje config flow na prvý krok konfigurácie 
    # Táto metóda tu musí byť, nesmie sa vymazať !!!
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        return await self.async_step_control_parameters(user_input)

    async def async_step_control_parameters(self, user_input=None):
        """Handle the step 1. - Control Parameters."""
        errors = {}

        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_valve_control()

        # Display a form for Control Parameters

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TIMEOUT_HEAT_DHW,
                    default=DEFAULT_TIMEOUT_HEAT_DHW,
                ): NumberSelector(NumberSelectorConfig(min=1, max=120, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW,
                    default=DEFAULT_TEMPERATURE_DELTA_LIMIT_ACC_DHW,
                ): NumberSelector(NumberSelectorConfig(min=1, max=10, step=0.5, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_DISABLED_ACC_TEMPERATURE_LIMIT,
                    default=DEFAULT_DISABLED_ACC_TEMPERATURE_LIMIT,
                ): NumberSelector(NumberSelectorConfig(min=20, max=100, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_MIN_TEMPERATURE_FOR_HEATING,
                    default=DEFAULT_MIN_TEMPERATURE_FOR_HEATING,
                ): NumberSelector(NumberSelectorConfig(min=25, max=50, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC,
                    default=DEFAULT_TEMPERATURE_DELTA_LIMIT_IN_ACC,
                ): NumberSelector(NumberSelectorConfig(min=1, max=10, step=0.5, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_HEATING_SOURCE_TEMP_HYSTERESIS,
                    default=DEFAULT_HEATING_SOURCE_TEMP_HYSTERESIS,
                ): NumberSelector(NumberSelectorConfig(min=1, max=10, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY,
                    default=DEFAULT_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY,
                ): NumberSelector(NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_AUXILIARY_WATER_PUMP_FOR_HEATING,
                    default=str(DEFAULT_AUXILIARY_WATER_PUMP_FOR_HEATING),
                ): SelectSelector(SelectSelectorConfig(options=[str(x) for x in AUXILIARY_WATER_PUMP_OPTIONS], mode=SelectSelectorMode.DROPDOWN, translation_key="auxiliary_water_pump_for_heating")),
                vol.Required(
                    CONF_AUXILIARY_PUMP_BOOSTER_TIME,
                    default=DEFAULT_AUXILIARY_PUMP_BOOSTER_TIME,
                ): NumberSelector(NumberSelectorConfig(min=1, max=15, mode=NumberSelectorMode.BOX)),
            }
        )

        return self.async_show_form(
            step_id="control_parameters",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_valve_control(self, user_input=None):
        """Handle step 2. - Valve Control."""
        errors = {}

        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_valves()

        # Display a form for Valve Control

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_VALVE_OUTPUT_ACC_STRICT_MODE,
                    default=str(DEFAULT_VALVE_OUTPUT_ACC_STRICT_MODE),
                ): SelectSelector(SelectSelectorConfig(options=[str(x) for x in VALVE_OUTPUT_ACC_STRICT_MODE_OPTIONS], mode=SelectSelectorMode.DROPDOWN, translation_key="valve_output_acc_strict_mode")),
                vol.Required(
                    CONF_VALVE_INPUT_ACC_STRICT_MODE,
                    default=str(DEFAULT_VALVE_INPUT_ACC_STRICT_MODE),
                ): SelectSelector(SelectSelectorConfig(options=[str(x) for x in VALVE_INPUT_ACC_STRICT_MODE_OPTIONS], mode=SelectSelectorMode.DROPDOWN, translation_key="valve_input_acc_strict_mode")),
                vol.Required(
                    CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP,
                    default=DEFAULT_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP,
                ): NumberSelector(NumberSelectorConfig(min=0, max=30, step=0.5, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_VALVE_TIMEOUT,
                    default=DEFAULT_VALVE_TIMEOUT,
                ): NumberSelector(NumberSelectorConfig(min=1, max=30, step=1, mode=NumberSelectorMode.BOX)),
            }
        )

        return self.async_show_form(
            step_id="valve_control",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_valves(self, user_input=None):
        """Handle step 3. - Valves."""
        errors = {}

        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_temperature_sensors()

        # Display a form for Valves

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_VALVE_FROM_TC_TO_ACC_OR_DHW,
                    default=DEFAULT_ENTITY_VALVE_FROM_TC_TO_ACC_OR_DHW,
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_OUTPUT_ACC1,
                    default=DEFAULT_ENTITY_VALVE_OUTPUT_ACC1,
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_OUTPUT_ACC2,
                    default=DEFAULT_ENTITY_VALVE_OUTPUT_ACC2,
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_INPUT_ACC1,
                    default=DEFAULT_ENTITY_VALVE_INPUT_ACC1,
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_INPUT_ACC2,
                    default=DEFAULT_ENTITY_VALVE_INPUT_ACC2,
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW,
                    default=DEFAULT_ENTITY_VALVE_FROM_ACC_TO_HEAT_OR_DHW,
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_OUTPUT_HEATING,
                    default=DEFAULT_ENTITY_VALVE_OUTPUT_HEATING,
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
            }
        )

        return self.async_show_form(
            step_id="valves",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_temperature_sensors(self, user_input=None):
        """Handle step 4. - Temperature Sensors."""
        errors = {}

        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_pumps()

        # Display a form for Temperature Sensors

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SENSOR_TEMP_ACC1,
                    default=DEFAULT_ENTITY_TEMP_ACC1,
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_TEMP_ACC2,
                    default=DEFAULT_ENTITY_TEMP_ACC2,
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_TEMP_DHW,
                    default=DEFAULT_ENTITY_TEMP_DHW,
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
            }
        )

        return self.async_show_form(
            step_id="temperature_sensors",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_pumps(self, user_input=None):
        """Handle step 5. - Water Pumps."""
        errors = {}

        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_thermostats()

        # Display a form for Water Pumps

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_WATER_PUMP_ACC_OUTPUT,
                    default=DEFAULT_ENTITY_WATER_PUMP_ACC_OUTPUT,
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
                vol.Required(
                    CONF_WATER_PUMP_DHW,
                    default=DEFAULT_ENTITY_WATER_PUMP_DHW,
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
                vol.Required(
                    CONF_WATER_PUMP_FLOOR_HEATING,
                    default=DEFAULT_ENTITY_WATER_PUMP_FLOOR_HEATING,
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
                vol.Required(
                    CONF_WATER_PUMP_HEATING,
                    default=DEFAULT_ENTITY_WATER_PUMP_HEATING,
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
            }
        )

        return self.async_show_form(
            step_id="pumps",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_thermostats(self, user_input=None):
        """Handle step 6. - Thermostat States."""
        errors = {}

        if user_input is not None:
            # Skombinuj dáta zo všetkých krokov
            self._data.update(user_input)
            
            await self.async_set_unique_id("heating_controller_unique_id")
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title="Heating Controller",
                data=self._data,
            )

        # Display a form for Thermostat States

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_THERMOSTAT_STATE,
                    default=DEFAULT_ENTITY_THERMOSTAT_STATE,
                ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
                vol.Required(
                    CONF_HEATING_STATE,
                    default=DEFAULT_ENTITY_HEATING_STATE,
                ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
                vol.Required(
                    CONF_FLOOR_HEATING_STATE,
                    default=DEFAULT_ENTITY_FLOOR_HEATING_STATE,
                ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
            }
        )

        return self.async_show_form(
            step_id="thermostats",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return HeatingControllerOptionsFlowHandler()

class HeatingControllerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Heating Controller."""

    def __init__(self):
        """Initialize options flow."""
        super().__init__()
        self._data = {}

    # Inicializačná metóda, ktorá presmeruje config flow na prvý krok konfigurácie 
    # Táto metóda tu musí byť, nesmie sa vymazať !!!
    async def async_step_init(self, user_input=None):
        """Handle the initial step of options flow."""
        return await self.async_step_control_parameters(user_input)

    async def async_step_control_parameters(self, user_input=None):
        """Manage the options - Control Parameters."""
        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_valve_control()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TIMEOUT_HEAT_DHW,
                    default=self.config_entry.options.get(
                        CONF_TIMEOUT_HEAT_DHW,
                        self.config_entry.data.get(
                            CONF_TIMEOUT_HEAT_DHW, DEFAULT_TIMEOUT_HEAT_DHW
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=120, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW,
                    default=self.config_entry.options.get(
                        CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW,
                        self.config_entry.data.get(
                            CONF_TEMPERATURE_DELTA_LIMIT_ACC_DHW, DEFAULT_TEMPERATURE_DELTA_LIMIT_ACC_DHW
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=10, step=0.5, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_DISABLED_ACC_TEMPERATURE_LIMIT,
                    default=self.config_entry.options.get(
                        CONF_DISABLED_ACC_TEMPERATURE_LIMIT,
                        self.config_entry.data.get(
                            CONF_DISABLED_ACC_TEMPERATURE_LIMIT, DEFAULT_DISABLED_ACC_TEMPERATURE_LIMIT
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=20, max=100, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_MIN_TEMPERATURE_FOR_HEATING,
                    default=self.config_entry.options.get(
                        CONF_MIN_TEMPERATURE_FOR_HEATING,
                        self.config_entry.data.get(
                            CONF_MIN_TEMPERATURE_FOR_HEATING, DEFAULT_MIN_TEMPERATURE_FOR_HEATING
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=25, max=50, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC,
                    default=self.config_entry.options.get(
                        CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC,
                        self.config_entry.data.get(
                            CONF_TEMPERATURE_DELTA_LIMIT_IN_ACC, DEFAULT_TEMPERATURE_DELTA_LIMIT_IN_ACC
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=10, step=0.5, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_HEATING_SOURCE_TEMP_HYSTERESIS,
                    default=self.config_entry.options.get(
                        CONF_HEATING_SOURCE_TEMP_HYSTERESIS,
                        self.config_entry.data.get(
                            CONF_HEATING_SOURCE_TEMP_HYSTERESIS, DEFAULT_HEATING_SOURCE_TEMP_HYSTERESIS
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=10, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY,
                    default=self.config_entry.options.get(
                        CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY,
                        self.config_entry.data.get(
                            CONF_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY, DEFAULT_HEATING_SOURCE_COMMAND_DEBOUNCE_DELAY
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX)),
                vol.Required(
                    CONF_AUXILIARY_WATER_PUMP_FOR_HEATING,
                    default=str(self.config_entry.options.get(
                        CONF_AUXILIARY_WATER_PUMP_FOR_HEATING,
                        self.config_entry.data.get(
                            CONF_AUXILIARY_WATER_PUMP_FOR_HEATING, DEFAULT_AUXILIARY_WATER_PUMP_FOR_HEATING
                        ),
                    )),
                ): SelectSelector(SelectSelectorConfig(options=[str(x) for x in AUXILIARY_WATER_PUMP_OPTIONS], mode=SelectSelectorMode.DROPDOWN, translation_key="auxiliary_water_pump_for_heating")),
                vol.Required(
                    CONF_AUXILIARY_PUMP_BOOSTER_TIME,
                    default=self.config_entry.options.get(
                        CONF_AUXILIARY_PUMP_BOOSTER_TIME,
                        self.config_entry.data.get(
                            CONF_AUXILIARY_PUMP_BOOSTER_TIME, DEFAULT_AUXILIARY_PUMP_BOOSTER_TIME
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=15, mode=NumberSelectorMode.BOX)),
            }
        )

        return self.async_show_form(step_id="control_parameters", data_schema=data_schema)

    async def async_step_valve_control(self, user_input=None):
        """Manage the options - Valve control."""
        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            if not hasattr(self, '_data'):
                self._data = {}
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_valves()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_VALVE_OUTPUT_ACC_STRICT_MODE,
                    default=str(self.config_entry.options.get(
                        CONF_VALVE_OUTPUT_ACC_STRICT_MODE,
                        self.config_entry.data.get(
                            CONF_VALVE_OUTPUT_ACC_STRICT_MODE, DEFAULT_VALVE_OUTPUT_ACC_STRICT_MODE
                        ),
                    )),
                ): SelectSelector(SelectSelectorConfig(options=[str(x) for x in VALVE_OUTPUT_ACC_STRICT_MODE_OPTIONS], mode=SelectSelectorMode.DROPDOWN, translation_key="valve_output_acc_strict_mode")),
                vol.Required(
                    CONF_VALVE_INPUT_ACC_STRICT_MODE,
                    default=str(self.config_entry.options.get(
                        CONF_VALVE_INPUT_ACC_STRICT_MODE,
                        self.config_entry.data.get(
                            CONF_VALVE_INPUT_ACC_STRICT_MODE, DEFAULT_VALVE_INPUT_ACC_STRICT_MODE
                        ),
                    )),
                ): SelectSelector(SelectSelectorConfig(options=[str(x) for x in VALVE_INPUT_ACC_STRICT_MODE_OPTIONS], mode=SelectSelectorMode.DROPDOWN, translation_key="valve_input_acc_strict_mode")),
                
                vol.Required(
                    CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP,
                    default=self.config_entry.options.get(
                        CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP,
                        self.config_entry.data.get(
                            CONF_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP, DEFAULT_VALVE_INPUT_ACC_CLOSING_DELAY_WHEN_HEATING_SOURCE_STOP
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=0, max=30, step=0.5, mode=NumberSelectorMode.BOX)),
                
                vol.Required(
                    CONF_VALVE_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_VALVE_TIMEOUT,
                        self.config_entry.data.get(
                            CONF_VALVE_TIMEOUT, DEFAULT_VALVE_TIMEOUT
                        ),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=30,  step=1, mode=NumberSelectorMode.BOX)),
            }
        )

        return self.async_show_form(step_id="valve_control", data_schema=data_schema)

    async def async_step_valves(self, user_input=None):
        """Manage the options - Valves."""
        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            if not hasattr(self, '_data'):
                self._data = {}
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_temperature_sensors()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_VALVE_FROM_TC_TO_ACC_OR_DHW,
                    default=self.config_entry.options.get(
                        CONF_VALVE_FROM_TC_TO_ACC_OR_DHW,
                        self.config_entry.data.get(
                            CONF_VALVE_FROM_TC_TO_ACC_OR_DHW, DEFAULT_ENTITY_VALVE_FROM_TC_TO_ACC_OR_DHW
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_OUTPUT_ACC1,
                    default=self.config_entry.options.get(
                        CONF_VALVE_OUTPUT_ACC1,
                        self.config_entry.data.get(
                            CONF_VALVE_OUTPUT_ACC1, DEFAULT_ENTITY_VALVE_OUTPUT_ACC1
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_OUTPUT_ACC2,
                    default=self.config_entry.options.get(
                        CONF_VALVE_OUTPUT_ACC2,
                        self.config_entry.data.get(
                            CONF_VALVE_OUTPUT_ACC2, DEFAULT_ENTITY_VALVE_OUTPUT_ACC2
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_INPUT_ACC1,
                    default=self.config_entry.options.get(
                        CONF_VALVE_INPUT_ACC1,
                        self.config_entry.data.get(
                            CONF_VALVE_INPUT_ACC1, DEFAULT_ENTITY_VALVE_INPUT_ACC1
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_INPUT_ACC2,
                    default=self.config_entry.options.get(
                        CONF_VALVE_INPUT_ACC2,
                        self.config_entry.data.get(
                            CONF_VALVE_INPUT_ACC2, DEFAULT_ENTITY_VALVE_INPUT_ACC2
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW,
                    default=self.config_entry.options.get(
                        CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW,
                        self.config_entry.data.get(
                            CONF_VALVE_FROM_ACC_TO_HEAT_OR_DHW, DEFAULT_ENTITY_VALVE_FROM_ACC_TO_HEAT_OR_DHW
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
                vol.Required(
                    CONF_VALVE_OUTPUT_HEATING,
                    default=self.config_entry.options.get(
                        CONF_VALVE_OUTPUT_HEATING,
                        self.config_entry.data.get(
                            CONF_VALVE_OUTPUT_HEATING, DEFAULT_ENTITY_VALVE_OUTPUT_HEATING
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="cover")),
            }
        )

        return self.async_show_form(step_id="valves", data_schema=data_schema)

    async def async_step_temperature_sensors(self, user_input=None):
        """Manage the options - Temperature Sensors."""
        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            if not hasattr(self, '_data'):
                self._data = {}
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_pumps()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SENSOR_TEMP_ACC1,
                    default=self.config_entry.options.get(
                        CONF_SENSOR_TEMP_ACC1,
                        self.config_entry.data.get(
                            CONF_SENSOR_TEMP_ACC1, DEFAULT_ENTITY_TEMP_ACC1
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_TEMP_ACC2,
                    default=self.config_entry.options.get(
                        CONF_SENSOR_TEMP_ACC2,
                        self.config_entry.data.get(
                            CONF_SENSOR_TEMP_ACC2, DEFAULT_ENTITY_TEMP_ACC2
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_TEMP_DHW,
                    default=self.config_entry.options.get(
                        CONF_SENSOR_TEMP_DHW,
                        self.config_entry.data.get(
                            CONF_SENSOR_TEMP_DHW, DEFAULT_ENTITY_TEMP_DHW
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
            }
        )

        return self.async_show_form(step_id="temperature_sensors", data_schema=data_schema)


    async def async_step_pumps(self, user_input=None):
        """Manage the options - Water Pumps."""
        if user_input is not None:
            # Uložiť dáta z predchádzajúceho kroku
            if not hasattr(self, '_data'):
                self._data = {}
            self._data.update(user_input)
            # Prejsť na ďalší krok
            return await self.async_step_thermostats()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_WATER_PUMP_ACC_OUTPUT,
                    default=self.config_entry.options.get(
                        CONF_WATER_PUMP_ACC_OUTPUT,
                        self.config_entry.data.get(
                            CONF_WATER_PUMP_ACC_OUTPUT, DEFAULT_ENTITY_WATER_PUMP_ACC_OUTPUT
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
                vol.Required(
                    CONF_WATER_PUMP_DHW,
                    default=self.config_entry.options.get(
                        CONF_WATER_PUMP_DHW,
                        self.config_entry.data.get(
                            CONF_WATER_PUMP_DHW, DEFAULT_ENTITY_WATER_PUMP_DHW
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
                vol.Required(
                    CONF_WATER_PUMP_FLOOR_HEATING,
                    default=self.config_entry.options.get(
                        CONF_WATER_PUMP_FLOOR_HEATING,
                        self.config_entry.data.get(
                            CONF_WATER_PUMP_FLOOR_HEATING, DEFAULT_ENTITY_WATER_PUMP_FLOOR_HEATING
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
                vol.Required(
                    CONF_WATER_PUMP_HEATING,
                    default=self.config_entry.options.get(
                        CONF_WATER_PUMP_HEATING,
                        self.config_entry.data.get(
                            CONF_WATER_PUMP_HEATING, DEFAULT_ENTITY_WATER_PUMP_HEATING
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="switch")),
            }
        )

        return self.async_show_form(step_id="pumps", data_schema=data_schema)

    async def async_step_thermostats(self, user_input=None):
        """Manage the options - Thermostat and Heating Pump States."""
        if user_input is not None:
            # Skombinuj dáta zo všetkých krokov
            if not hasattr(self, '_data'):
                self._data = {}
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_THERMOSTAT_STATE,
                    default=self.config_entry.options.get(
                        CONF_THERMOSTAT_STATE,
                        self.config_entry.data.get(
                            CONF_THERMOSTAT_STATE, DEFAULT_ENTITY_THERMOSTAT_STATE
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
                vol.Required(
                    CONF_HEATING_STATE,
                    default=self.config_entry.options.get(
                        CONF_HEATING_STATE,
                        self.config_entry.data.get(
                            CONF_HEATING_STATE, DEFAULT_ENTITY_HEATING_STATE
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
                vol.Required(
                    CONF_FLOOR_HEATING_STATE,
                    default=self.config_entry.options.get(
                        CONF_FLOOR_HEATING_STATE,
                        self.config_entry.data.get(
                            CONF_FLOOR_HEATING_STATE, DEFAULT_ENTITY_FLOOR_HEATING_STATE
                        ),
                    ),
                ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
            }
        )

        return self.async_show_form(step_id="thermostats", data_schema=data_schema)