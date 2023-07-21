from abc import ABC
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_STATE, Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import ACTION_ENTITY_SELECT_OPTION, ATTR_ATTRIBUTES
from .common.entity_descriptions import IntegrationSelectEntityDescription
from .common.monitor_data import MonitorData
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.SELECT,
        IntegrationSelectEntity,
        async_add_entities,
    )


class IntegrationSelectEntity(IntegrationBaseEntity, SelectEntity, ABC):
    """Representation of a sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: IntegrationSelectEntityDescription,
        coordinator: Coordinator,
        monitor: MonitorData,
    ):
        super().__init__(hass, entity_description, coordinator, monitor)

        self.entity_description = entity_description

        self._attr_options = entity_description.options
        self._attr_current_option = entity_description.options[0]

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.async_execute_device_action(ACTION_ENTITY_SELECT_OPTION, option)

    def update_component(self, data):
        """Fetch new state parameters for the sensor."""
        if data is not None:
            state = data.get(ATTR_STATE)
            attributes = data.get(ATTR_ATTRIBUTES)

            self._attr_current_option = state
            self._attr_extra_state_attributes = attributes

        else:
            self._attr_current_option = self.entity_description.options[0]
