from __future__ import annotations
"""The Heating Controller integration"""
"""Author: Jozef Moravcik"""
"""email: jozef.moravcik@moravcik.eu"""

""" select.py """

"""Select platform for Heating Controller integration"""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    ENTITY_HEATING_OPERATING_MODE,
    DEFAULT_HEATING_OPERATING_MODE,
    HEATING_OPERATING_MODE_OPTIONS,
)

LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heating Controller select entities."""
    instance = hass.data[DOMAIN][entry.entry_id]["instance"]

    entities = [
        HeatingControllerSelect(
            instance,
            entry.entry_id,
            ENTITY_HEATING_OPERATING_MODE,
            "Heating operating mode",
            "mdi:arrow-decision",
            options=[str(x) for x in HEATING_OPERATING_MODE_OPTIONS],
            default_value=str(DEFAULT_HEATING_OPERATING_MODE),
        ),
    ]

    # Uložím select entity do dictionary
    selects_dict = {entity._entity_id: entity for entity in entities}
    hass.data[DOMAIN][entry.entry_id]["selects"] = selects_dict

    async_add_entities(entities)

class HeatingControllerSelect(SelectEntity, RestoreEntity):
    """Representation of a Heating Controller select entity."""

    def __init__(
        self,
        instance,
        entry_id: str,
        entity_id: str,
        name: str,
        icon: str,
        options: list[str],
        default_value: str,
    ) -> None:
        """Initialize the select entity."""
        self._instance = instance
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entity_id}"
        self._attr_has_entity_name = True
        self._attr_translation_key = entity_id
        self.entity_id = f"select.{DOMAIN}_{entity_id}"
        self._attr_icon = icon
        self._entity_id = entity_id
        self._attr_options = options
        self._default_value = default_value
        self._attr_current_option = default_value

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Obnovenie stavu po reštarte
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            if last_state.state in self._attr_options:
                self._attr_current_option = last_state.state
                LOGGER.debug(f"Restored state for {self.entity_id}: {self._attr_current_option}")
            else:
                self._attr_current_option = self._default_value
                LOGGER.debug(f"Invalid restored state for {self.entity_id}, using default: {self._default_value}")
        else:
            self._attr_current_option = self._default_value
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

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()
            LOGGER.debug(f"Select {self.entity_id} set to {option}")
        else:
            LOGGER.warning(f"Invalid option {option} for {self.entity_id}")