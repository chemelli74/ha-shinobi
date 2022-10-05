"""
Support for MyDolphin Plus.
For more details about this platform, please refer to the documentation at
https://github.com/sh00t2kill/dolphin-robot
"""
from __future__ import annotations

import logging

from homeassistant.components.vacuum import VacuumEntityFeature

from .component.helpers.const import *
from .core.components.vacuum import CoreVacuum
from .core.helpers.setup_base_entry import async_setup_base_entry

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [DOMAIN]

CURRENT_DOMAIN = DOMAIN_VACUUM

VACUUM_FEATURES = VacuumEntityFeature.STATE | \
                  VacuumEntityFeature.FAN_SPEED | \
                  VacuumEntityFeature.RETURN_HOME | \
                  VacuumEntityFeature.SEND_COMMAND | \
                  VacuumEntityFeature.START | \
                  VacuumEntityFeature.STOP


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Switch."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CoreVacuum.get_domain(), CoreVacuum.get_component
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"Unload entry for {CoreVacuum.get_domain()} domain: {config_entry}")

    return True


async def async_remove_entry(hass, entry) -> None:
    _LOGGER.info(f"Remove entry for {CoreVacuum.get_domain()} entry: {entry}")
