from __future__ import annotations
"""The Heating Controller integration"""
"""Author: Jozef Moravcik"""
"""email: jozef.moravcik@moravcik.eu"""

""" sensor.py """

"""Sensor platform for Heating Controller integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import *

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heating Controller sensor entities."""
    instance = hass.data[DOMAIN][entry.entry_id]["instance"]

    entities = [
        HeatingControllerSensor(
            instance,
            entry.entry_id,
            ENTITY_CONTROL_COMMAND_HP_ON_OFF,
            "TC - ON/OFF",
            "mdi:check-circle",
        ),
        HeatingControllerSensor(
            instance,
            entry.entry_id,
            ENTITY_CONTROL_COMMAND_HP_TEMPERATURE,
            "TC - Temperature",
            "mdi:thermometer-water",
        ),
    ]

    async_add_entities(entities)

class HeatingControllerSensor(SensorEntity):
    """Representation of a Heating Controller sensor."""

    def __init__(
        self,
        instance,
        entry_id: str,
        entity_id: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        self._instance = instance
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entity_id}"
        self._attr_has_entity_name = True
        self._attr_translation_key = entity_id
        self.entity_id = f"sensor.{DOMAIN}_{entity_id}"
        self._attr_icon = icon
        self._entity_id = entity_id
        self._attr_native_value = "off"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        
        # Subscribe to updates
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_feedback_update_{self._entry_id}",
                self._handle_feedback_update,
            )
        )

    @callback
    def _handle_feedback_update(self) -> None:
        """Handle feedback update."""
        new_value = self._instance.sensor_states.get(self._entity_id)
        if new_value is not None:
            self._attr_native_value = new_value
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._attr_native_value