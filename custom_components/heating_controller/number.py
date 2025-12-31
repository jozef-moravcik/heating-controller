from __future__ import annotations
"""The Heating Controller integration"""
"""Author: Jozef Moravcik"""
"""email: jozef.moravcik@moravcik.eu"""

""" number.py """

"""Number platform for Heating Controller integration."""

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    ENTITY_DHW_TARGET_TEMPERATURE,
    ENTITY_ACC_TARGET_TEMPERATURE,
    DEFAULT_DHW_TARGET_TEMPERATURE,
    DEFAULT_ACC_TARGET_TEMPERATURE,
)

LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heating Controller number entities."""
    instance = hass.data[DOMAIN][entry.entry_id]["instance"]

    entities = [
        HeatingControllerNumber(
            instance,
            entry.entry_id,
            ENTITY_DHW_TARGET_TEMPERATURE,
            "DHW target temperature",
            "mdi:thermometer-water",
            min_value=20,
            max_value=90,
            step=1.0,
            default_value=DEFAULT_DHW_TARGET_TEMPERATURE,
        ),
        HeatingControllerNumber(
            instance,
            entry.entry_id,
            ENTITY_ACC_TARGET_TEMPERATURE,
            "ACC target temperature",
            "mdi:thermometer",
            min_value=25,
            max_value=65,
            step=1.0,
            default_value=DEFAULT_ACC_TARGET_TEMPERATURE,
        ),
    ]

    # Uložím number entity do dictionary
    numbers_dict = {entity._entity_id: entity for entity in entities}
    hass.data[DOMAIN][entry.entry_id]["numbers"] = numbers_dict

    async_add_entities(entities)


class HeatingControllerNumber(NumberEntity, RestoreEntity):
    """Representation of a Heating Controller number entity (slider)."""

    def __init__(
        self,
        instance,
        entry_id: str,
        entity_id: str,
        name: str,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        default_value: float,
    ) -> None:
        """Initialize the number entity."""
        self._instance = instance
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entity_id}"
        self._attr_has_entity_name = True
        self._attr_translation_key = entity_id
        self.entity_id = f"number.{DOMAIN}_{entity_id}"
        self._attr_icon = icon
        self._entity_id = entity_id
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_unit_of_measurement = "°C"
        self._default_value = default_value
        self._attr_native_value = default_value

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Obnovenie stavu po reštarte
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
                LOGGER.debug(f"Restored state for {self.entity_id}: {self._attr_native_value}")
            except (ValueError, TypeError):
                self._attr_native_value = self._default_value
                LOGGER.debug(f"Failed to restore state for {self.entity_id}, using default: {self._default_value}")
        else:
            self._attr_native_value = self._default_value
            LOGGER.debug(f"No saved state for {self.entity_id}, using default: {self._default_value}")

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
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set the value of the number entity."""
        self._attr_native_value = value
        self.async_write_ha_state()
        LOGGER.debug(f"Number {self.entity_id} set to {value}")
