from __future__ import annotations

import json
import logging
import sys
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntryDisabler

from ...core.helpers.const import *
from ...core.helpers.enums import EntityStatus
from ...core.models.domain_data import DomainData
from ...core.models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class EntityManager:
    """ Entity Manager is agnostic to component - PLEASE DON'T CHANGE """

    hass: HomeAssistant
    domain_component_manager: dict[str, DomainData]
    entities: dict[str, EntityData]

    def __init__(self, hass, ha):
        self.hass: HomeAssistant = hass
        self._ha = ha
        self.domain_component_manager: dict[str, DomainData] = {}
        self.entities = {}

    @property
    def entity_registry(self) -> EntityRegistry:
        return self._ha.entity_registry

    @property
    def available_domains(self):
        return self.domain_component_manager.keys()

    def set_domain_data(self, domain_data: DomainData):
        self.domain_component_manager[domain_data.name] = domain_data

    def get_domain_data(self, domain: str) -> DomainData | None:
        domain_data = self.domain_component_manager[domain]

        return domain_data

    def update(self):
        self.hass.async_create_task(self._async_update())

    async def _handle_disabled_entity(self, entity_id, entity: EntityData):
        entity_item = self.entity_registry.async_get(entity_id)

        if entity_item is not None:
            if entity.disabled:
                _LOGGER.info(f"Disabling entity, Data: {entity}")

                self.entity_registry.async_update_entity(entity_id,
                                                         disabled_by=RegistryEntryDisabler.INTEGRATION)

            else:
                entity.disabled = entity_item.disabled

    async def _handle_restored_entity(self, entity_id, component):
        if entity_id is not None:
            component.entity_id = entity_id
            state = self.hass.states.get(entity_id)

            if state is not None:
                restored = state.attributes.get("restored", False)

                if restored:
                    _LOGGER.debug(f"Restored {entity_id} ({component.name})")

    async def _async_add_components(self):
        try:
            components: dict[str, list] = {}
            for unique_id in self.entities:
                entity = self.entities.get(unique_id)

                if entity.status == EntityStatus.CREATED:
                    entity_id = self.entity_registry.async_get_entity_id(
                        entity.domain, DOMAIN, unique_id
                    )

                    await self._handle_disabled_entity(entity_id, entity)

                    domain_manager = self.domain_component_manager.get(entity.domain)
                    component = domain_manager.initializer(self.hass, entity)

                    await self._handle_restored_entity(entity_id, component)

                    domain_components = components.get(entity.domain, [])
                    domain_components.append(component)

                    components[entity.domain] = domain_components

                    entity.status = EntityStatus.READY

            for domain in self.domain_component_manager:
                domain_manager = self.domain_component_manager.get(domain)

                domain_components = components.get(domain, [])
                components_count = len(domain_components)

                if components_count > 0:
                    domain_manager.async_add_devices(domain_components)

                    _LOGGER.info(f"{components_count} {domain} components created")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to add component, "
                f"Error: {str(ex)}, "
                f"Line: {line_number}"
            )

    async def _async_delete_components(self):
        deleted = 0
        for unique_id in self.entities:
            entity = self.entities.get(unique_id)

            if entity.status == EntityStatus.DELETED:
                entity_id = self.entity_registry.async_get_entity_id(
                    entity.domain, DOMAIN, unique_id
                )

                entity_item = self.entity_registry.async_get(entity_id)

                if entity_item is not None:
                    _LOGGER.info(f"Removed {entity_id} ({entity.name})")

                    self.entity_registry.async_remove(entity_id)

                del self.entities[entity.id]

                deleted += 1

        if deleted > 0:
            _LOGGER.info(f"{deleted} components deleted")

    async def _async_update(self):
        _LOGGER.debug("Starting to update entities")

        try:
            await self._async_add_components()
            await self._async_delete_components()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to update, "
                f"Error: {str(ex)}, "
                f"Line: {line_number}"
            )

    def _compare_data(self,
                      entity: EntityData,
                      state: str,
                      attributes: dict,
                      device_name: str,
                      entity_description: EntityDescription | None = None,
                      details: dict | None = None):
        msgs = []

        if entity.state != state:
            msgs.append(f"State {entity.state} -> {state}")

        if entity.attributes != attributes:
            from_attributes = self._get_attributes_json(entity.attributes)
            to_attributes = self._get_attributes_json(attributes)

            msgs.append(f"Attributes {from_attributes} -> {to_attributes}")

        if entity.device_name != device_name:
            msgs.append(f"Device name {entity.device_name} -> {device_name}")

        if entity_description is not None and entity.entity_description != entity_description:
            msgs.append(f"Description {str(entity.entity_description)} -> {str(entity_description)}")

        if details is not None and entity.details != details:
            from_details = self._get_attributes_json(entity.details)
            to_details = self._get_attributes_json(details)

            msgs.append(f"Details {from_details} -> {to_details}")

        modified = len(msgs) > 0

        if modified:
            full_message = " | ".join(msgs)

            _LOGGER.debug(f"{entity.entity_description.name} | {entity.domain} | {full_message}")

        return modified

    @staticmethod
    def _get_attributes_json(attributes: dict):
        new_attributes = {}
        for key in attributes:
            value = attributes[key]
            new_attributes[key] = str(value)

        result = json.dumps(new_attributes)

        return result

    def get(self, unique_id: str) -> EntityData | None:
        entity = self.entities.get(unique_id)

        return entity

    def set_entity(self,
                   domain: str,
                   entry_id: str,
                   state: str | bool,
                   attributes: dict,
                   device_name: str,
                   entity_description: EntityDescription | None,
                   details: dict | None = None,
                   destructors: list[bool] = None
                   ):

        entity = self.entities.get(entity_description.key)

        if entity is None:
            entity = EntityData(entry_id, entity_description)
            entity.status = EntityStatus.CREATED
            entity.domain = domain

            self._compare_data(entity, state, attributes, device_name)

        else:
            was_modified = self._compare_data(entity, state, attributes, device_name, entity_description, details)

            if was_modified:
                entity.status = EntityStatus.UPDATED

        if entity.status in [EntityStatus.CREATED, EntityStatus.UPDATED]:
            entity.state = state
            entity.attributes = attributes
            entity.device_name = device_name
            entity.details = details

        if destructors is not None and True in destructors:
            if entity.status == EntityStatus.CREATED:
                entity = None

            else:
                entity.status = EntityStatus.DELETED

        if entity is None:
            _LOGGER.debug(f"{entity_description.name} ignored")

        else:
            self.entities[entity_description.key] = entity

            if entity.status != EntityStatus.READY:
                _LOGGER.info(f"{entity.name} ({entity.domain}) {entity.status}, state: {entity.state}")
