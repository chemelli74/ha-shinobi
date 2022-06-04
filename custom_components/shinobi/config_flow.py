"""Config flow to configure Shinobi Video."""
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from .component.helpers.const import *
from .component.helpers.exceptions import AlreadyExistsError, LoginError
from .core.managers.config_flow_manager import ConfigFlowManager

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class DomainFlowHandler(config_entries.ConfigFlow):
    """Handle a domain config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        super().__init__()

        self._config_flow = ConfigFlowManager()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DomainOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        _LOGGER.debug(f"Starting async_step_user of {DEFAULT_NAME}")

        errors = None

        await self._config_flow.initialize(self.hass)

        new_user_input = self._config_flow.clone_items(user_input)

        if user_input is not None:
            try:
                data = await self._config_flow.update_data(user_input, CONFIG_FLOW_DATA)

                _LOGGER.debug("Completed")

                return self.async_create_entry(title=self._config_flow.title, data=data)
            except LoginError as lex:
                del new_user_input[CONF_PASSWORD]

                errors = lex.errors

            except AlreadyExistsError as aeex:
                errors = {"base": "already_configured"}

        if errors is not None:
            error_message = errors.get("base")

            _LOGGER.warning(f"Failed to create integration, Error: {error_message}")

        schema = await self._config_flow.get_default_data(new_user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=new_user_input,
        )

    async def async_step_import(self, info):
        """Import existing configuration."""
        _LOGGER.debug(f"Starting async_step_import of {DEFAULT_NAME}")

        title = f"{DEFAULT_NAME} (import from configuration.yaml)"

        return self.async_create_entry(title=title, data=info)


class DomainOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle domain options."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize domain options flow."""
        super().__init__()

        self._config_entry = config_entry

        self._config_flow = ConfigFlowManager()

    async def async_step_init(self, user_input=None):
        """Manage the domain options."""
        return await self.async_step_shinobi_additional_settings(user_input)

    async def async_step_shinobi_additional_settings(self, user_input=None):
        _LOGGER.info(f"Starting additional settings step: {user_input}")
        errors = None

        await self._config_flow.initialize(self.hass, self._config_entry)

        if user_input is not None:
            try:
                options = await self._config_flow.update_options(
                    user_input, CONFIG_FLOW_OPTIONS
                )

                return self.async_create_entry(
                    title=self._config_flow.title, data=options
                )
            except LoginError as lex:
                del user_input[CONF_PASSWORD]

                errors = lex.errors

            except AlreadyExistsError as aeex:
                errors = {"base": "already_configured"}

        if errors is not None:
            error_message = errors.get("base")

            _LOGGER.warning(f"Failed to update integration, Error: {error_message}")

        schema = self._config_flow.get_default_options()

        return self.async_show_form(
            step_id="shinobi_additional_settings",
            data_schema=schema,
            errors=errors,
            description_placeholders=user_input,
        )
