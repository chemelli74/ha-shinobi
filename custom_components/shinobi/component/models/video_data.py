from __future__ import annotations

import sys

from homeassistant.exceptions import HomeAssistantError

from ...component.helpers.common import *
from ...component.helpers.const import *
from .monitor_data import MonitorData

_LOGGER = logging.getLogger(__name__)


class VideoData:
    monitor_id: str
    monitor_name: str
    action_url: str
    mime_type: str
    extension: str
    video_time: str

    def __init__(self, video: dict, monitors: dict[str, MonitorData]):
        try:
            monitor_id = video.get(VIDEO_DETAILS_MONITOR_ID)

            if monitor_id is None:
                raise HomeAssistantError()

            monitor = monitors.get(monitor_id)

            extension = video.get(VIDEO_DETAILS_EXTENSION)
            video_time: str = video.get(VIDEO_DETAILS_TIME)

            self.monitor_id = monitor_id
            self.monitor_name = monitor_id if monitor is None else monitor.name
            self.action_url = video.get(VIDEO_DETAILS_URL)
            self.mime_type = get_mime_type(extension)
            self.video_time = video_time
            self.extension = extension

        except HomeAssistantError:
            _LOGGER.error(
                f"Failed to extract monitor ID for video: {video}"
            )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize VideoData: {video}, Error: {ex}, Line: {line_number}"
            )

    @property
    def time(self) -> str:
        result = format_datetime(self.video_time, VIDEO_DETAILS_TIME_FORMAT)

        return result

    @property
    def time_iso(self) -> str:
        result = format_datetime(self.video_time, VIDEO_DETAILS_TIME_ISO_FORMAT)

        return result

    @property
    def thumbnail(self):
        look_for_ext = f".{self.extension}"

        url = self.action_url.replace(look_for_ext, "").replace(VIDEO_ENDPOINT_VIDEOS, VIDEO_ENDPOINT_THUMBNAIL)
        thumbnail = f"{url}/{self.extension}"

        return thumbnail

    @property
    def identifier(self):
        identifier = f"{self.action_url}|{self.mime_type}"

        return identifier

    def to_dict(self):
        obj = {
            ATTR_MONITOR_ID: self.monitor_id,
            ATTR_MONITOR_NAME: self.monitor_name,
            VIDEO_DETAILS_URL: self.action_url,
            VIDEO_DETAILS_MIME_TYPE: self.mime_type,
            VIDEO_DETAILS_TIME: self.video_time,
            VIDEO_DETAILS_IDENTIFIER: self.identifier
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
