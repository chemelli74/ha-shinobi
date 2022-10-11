"""Storage handlers."""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *

_LOGGER = logging.getLogger(__name__)


class StorageAPI(BaseAPI):
    _storages: dict[str, Store] | None

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self._storages = None

    @property
    def _storage_config(self) -> Store:
        storage = self._storages.get(STORAGE_DATA_FILE_CONFIG)

        return storage

    @property
    def _storage_api(self) -> Store:
        storage = self._storages.get(STORAGE_DATA_FILE_API_DEBUG)

        return storage

    @property
    def _storage_ws(self) -> Store:
        storage = self._storages.get(STORAGE_DATA_FILE_WS_DEBUG)

        return storage

    @property
    def use_original_stream(self):
        use_original_stream = self.data.get(STORAGE_DATA_USE_ORIGINAL_STREAM, False)

        return use_original_stream

    @property
    def store_debug_data(self):
        result = self.data.get(STORAGE_DATA_STORE_DEBUG_DATA, False)

        return result

    async def initialize(self, config_data: ConfigData):
        storages = {}
        entry_id = config_data.entry.entry_id

        for storage_data_file in STORAGE_DATA_FILES:
            file_name = f"{DOMAIN}.{entry_id}.{storage_data_file}.json"

            storages[storage_data_file] = Store(self.hass, STORAGE_VERSION, file_name, encoder=JSONEncoder)

        self._storages = storages

        await self._async_load_configuration()

    async def _async_load_configuration(self):
        """Load the retained data from store and return de-serialized data."""
        self.data = await self._storage_config.async_load()

        if self.data is None:
            self.data = {
                STORAGE_DATA_USE_ORIGINAL_STREAM: False,
                STORAGE_DATA_STORE_DEBUG_DATA: False
            }

            await self._async_save()

        _LOGGER.debug(f"Loaded configuration data: {self.data}")

        await self.set_status(ConnectivityStatus.Connected)
        await self.fire_data_changed_event()

    async def _async_save(self):
        """Generate dynamic data to store and save it to the filesystem."""
        _LOGGER.info(f"Save configuration, Data: {self.data}")

        await self._storage_config.async_save(self.data)

        await self.fire_data_changed_event()

    async def set_use_original_stream(self, is_on: bool):
        _LOGGER.debug(f"Set use original stream to {is_on}")

        self.data[STORAGE_DATA_USE_ORIGINAL_STREAM] = is_on

        await self._async_save()

    async def set_store_debug_data(self, enabled: bool):
        _LOGGER.debug(f"Set store debug data to {enabled}")

        self.data[STORAGE_DATA_STORE_DEBUG_DATA] = enabled

        await self._async_save()

    async def debug_log_api(self, data: dict):
        if self.store_debug_data:
            await self._storage_api.async_save(data)

    async def debug_log_ws(self, data: dict):
        if self.store_debug_data:
            await self._storage_ws.async_save(data)
