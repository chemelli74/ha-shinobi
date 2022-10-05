"""
Core HA Manager.
"""
from __future__ import annotations

import datetime
import logging
import sys
from typing import Any

from cryptography.fernet import InvalidToken

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import EntityRegistry, async_get
from homeassistant.helpers.event import async_track_time_interval

from ...core.helpers.const import *
from ...core.managers.device_manager import DeviceManager
from ...core.managers.entity_manager import EntityManager
from ...core.managers.storage_manager import StorageManager
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class HomeAssistantManager:
    def __init__(self,
                 hass: HomeAssistant,
                 scan_interval: datetime.timedelta,
                 heartbeat_interval: datetime.timedelta | None = None
                 ):

        self._hass = hass

        self._is_initialized = False
        self._is_updating = False
        self._scan_interval = scan_interval
        self._heartbeat_interval = heartbeat_interval

        self._entity_registry = None

        self._entry: ConfigEntry | None = None

        self._storage_manager = StorageManager(self._hass)
        self._entity_manager = EntityManager(self._hass, self)
        self._device_manager = DeviceManager(self._hass, self)

        self._entity_registry = async_get(self._hass)

        self._async_track_time_handlers = []
        self._last_heartbeat = None
        self._update_lock = False
        self._actions: dict = {}

        def _send_heartbeat(internal_now):
            self._last_heartbeat = internal_now

            self._hass.async_create_task(self.async_send_heartbeat())

        self._send_heartbeat = _send_heartbeat

    @property
    def entity_manager(self) -> EntityManager:
        if self._entity_manager is None:
            self._entity_manager = EntityManager(self._hass, self)

        return self._entity_manager

    @property
    def device_manager(self) -> DeviceManager:
        return self._device_manager

    @property
    def entity_registry(self) -> EntityRegistry:
        return self._entity_registry

    @property
    def storage_manager(self) -> StorageManager:
        return self._storage_manager

    @property
    def entry_id(self) -> str:
        return self._entry.entry_id

    @property
    def entry_title(self) -> str:
        return self._entry.title

    async def async_component_initialize(self, entry: ConfigEntry):
        """ Component initialization """
        pass

    async def async_send_heartbeat(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    def register_services(self, entry: ConfigEntry | None = None):
        """ Must be implemented to be able to expose services """
        pass

    async def async_initialize_data_providers(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    async def async_stop_data_providers(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    async def async_update_data_providers(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    def load_entities(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    def load_devices(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    async def async_init(self, entry: ConfigEntry):
        try:
            self._entry = entry

            await self.async_component_initialize(entry)

            self._hass.loop.create_task(self._async_load_platforms())

        except InvalidToken:
            error_message = "Encryption key got corrupted, please remove the integration and re-add it"

            _LOGGER.error(error_message)

            data = await self._storage_manager.async_load_from_store()
            data.key = None

            await self._storage_manager.async_save_to_store(data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_init, error: {ex}, line: {line_number}")

    async def _async_load_platforms(self):
        load = self._hass.config_entries.async_forward_entry_setup

        for domain in PLATFORMS:
            await load(self._entry, domain)

        self.register_services()

        self._is_initialized = True

        await self.async_update_entry()

    def _update_entities(self, now):
        self._hass.async_create_task(self.async_update(now))

    async def async_update_entry(self, entry: ConfigEntry | None = None):
        entry_changed = entry is not None

        if entry_changed:
            self._entry = entry

            _LOGGER.info(f"Handling ConfigEntry load: {entry.as_dict()}")

        else:
            entry = self._entry

            remove_async_track_time = async_track_time_interval(
                self._hass, self._update_entities, self._scan_interval
            )

            self._async_track_time_handlers.append(remove_async_track_time)

            if self._heartbeat_interval is not None:
                remove_async_heartbeat_track_time = async_track_time_interval(
                    self._hass, self._send_heartbeat, self._heartbeat_interval
                )

                self._async_track_time_handlers.append(remove_async_heartbeat_track_time)

            _LOGGER.info(f"Handling ConfigEntry change: {entry.as_dict()}")

        await self.async_initialize_data_providers()

    async def async_unload(self):
        _LOGGER.info(f"HA was stopped")

        for handler in self._async_track_time_handlers:
            if handler is not None:
                handler()

        self._async_track_time_handlers.clear()

        await self.async_stop_data_providers()

    async def async_remove(self, entry: ConfigEntry):
        _LOGGER.info(f"Removing current integration - {entry.title}")

        await self.async_unload()

        unload = self._hass.config_entries.async_forward_entry_unload

        for domain in PLATFORMS:
            await unload(entry, domain)

        await self._device_manager.async_remove()

        self._entry = None
        self.entity_manager.entities.clear()

        _LOGGER.info(f"Current integration ({entry.title}) removed")

    def update(self):
        if self._update_lock:
            return

        self._update_lock = True

        self.load_devices()
        self.load_entities()

        self.entity_manager.update()

        self._hass.async_create_task(self.dispatch_all())

        self._update_lock = False

    async def async_update(self, event_time):
        if not self._is_initialized:
            _LOGGER.info(f"NOT INITIALIZED - Failed updating @{event_time}")
            return

        try:
            if self._is_updating:
                _LOGGER.debug(f"Skip updating @{event_time}")
                return

            _LOGGER.debug(f"Updating @{event_time}")

            self._is_updating = True

            await self.async_update_data_providers()

            self.update()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_update, Error: {ex}, Line: {line_number}")

        self._is_updating = False

    async def dispatch_all(self):
        if not self._is_initialized:
            _LOGGER.info("NOT INITIALIZED - Failed discovering components")
            return

        for domain in PLATFORMS:
            signal = PLATFORMS.get(domain)

            async_dispatcher_send(self._hass, signal)

    def set_action(self, entity_id: str, action_name: str, action):
        key = f"{entity_id}:{action_name}"
        self._actions[key] = action

    def get_action(self, entity_id: str, action_name: str):
        key = f"{entity_id}:{action_name}"
        action = self._actions.get(key)

        return action

    async def get_core_entity_fan_speed(self, entity: EntityData) -> str | None:
        """ Handles ACTION_GET_CORE_ENTITY_FAN_SPEED. """
        pass

    def async_core_entity_return_to_base(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_RETURN_TO_BASE. """
        pass

    async def async_core_entity_set_fan_speed(self, entity: EntityData, fan_speed: str) -> None:
        """ Handles ACTION_CORE_ENTITY_SET_FAN_SPEED. """
        pass

    async def async_core_entity_start(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_START. """
        pass

    async def async_core_entity_stop(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_STOP. """
        pass

    async def async_core_entity_turn_on(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_TURN_ON. """
        pass

    async def async_core_entity_turn_off(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_TURN_OFF. """
        pass

    async def async_core_entity_toggle(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_TOGGLE. """
        pass

    async def async_core_entity_send_command(
            self,
            entity: EntityData,
            command: str,
            params: dict[str, Any] | list[Any] | None = None
    ) -> None:
        """ Handles ACTION_CORE_ENTITY_SEND_COMMAND. """
        pass

    async def async_core_entity_locate(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_LOCATE. """
        pass

    async def async_core_entity_select_option(self, entity: EntityData, option: str) -> None:
        """ Handles ACTION_CORE_ENTITY_SELECT_OPTION. """
        pass

    async def async_core_entity_enable_motion_detection(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_ENABLE_MOTION_DETECTION. """
        pass

    async def async_core_entity_disable_motion_detection(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_DISABLE_MOTION_DETECTION. """
        pass

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")
