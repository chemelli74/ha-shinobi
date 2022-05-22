from homeassistant.exceptions import HomeAssistantError


class MonitorNotFoundError(HomeAssistantError):
    monitor_id: str

    def __init__(self, monitor_id: str):
        self.monitor_id = monitor_id


class AlreadyExistsError(HomeAssistantError):
    title: str

    def __init__(self, title: str):
        self.title = title


class LoginError(HomeAssistantError):
    errors: dict

    def __init__(self, errors):
        self.errors = errors
