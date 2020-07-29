import datetime

from flask import current_app

import arrow
from passari_web_ui.db import db
from passari_workflow.db.models import MuseumObject
from passari_workflow.heartbeat import HeartbeatSource, get_heartbeats
from passari_workflow.queue.queues import get_enqueued_object_ids


class SystemStatus:
    """
    Container for heartbeats and possibly other system health status
    information in the future
    """
    def __init__(self, heartbeats):
        self.heartbeats = heartbeats

    def get_heartbeat_interval(self, source):
        """
        Get the expected heartbeat interval as a timedelta
        """
        source = HeartbeatSource(source)

        # Get the name for the configuration parameter
        interval_config_name = f"HEARTBEAT_INTERVAL_{source.value.upper()}"

        # Default to 24 hours if no expected interval is configured for
        # the heartbeat
        interval = int(current_app.config.get(interval_config_name, 86400))
        interval = datetime.timedelta(seconds=interval)

        return interval

    def is_heartbeat_recent(self, source):
        """
        Check if the heartbeat is recent or overdue.

        :returns: True if the heartbeat is recent, False if it's overdue or
                  None if no heartbeat has been submitted yet
        """
        source = HeartbeatSource(source)

        interval = self.get_heartbeat_interval(source)
        timestamp = self.heartbeats[source]

        if not timestamp:
            return None

        now = datetime.datetime.now(datetime.timezone.utc)

        # Is the timestamp recent?
        return timestamp > now - interval

    def get_heartbeat_natural_time(self, source):
        """
        Get the elapsed time for a heartbeat as a readable duration
        (eg. "2 hours ago")
        """
        source = HeartbeatSource(source)

        timestamp = self.heartbeats[source]

        if timestamp is None:
            return "Never"

        # Use arrow to create a humanized 'x time ago' string
        timestamp = arrow.get(timestamp)
        return timestamp.humanize()

    def get_interval_natural_time(self, source):
        """
        Get the expected heartbeat interval as a readable duration
        (eg. "24 hours")
        """
        source = HeartbeatSource(source)

        interval = self.get_heartbeat_interval(source)

        distance = arrow.utcnow() - interval
        return distance.humanize(only_distance=True)

    @property
    def is_all_ok(self):
        """
        Check if all heartbeats are recent enough
        """
        for source in HeartbeatSource:
            if not self.is_heartbeat_recent(source):
                return False

        return True

    @property
    def is_any_overdue(self):
        """
        Check if any of the heartbeats is overdue. This might mean some
        automated procedure is failing.

        Note that this doesn't account for heartbeats that haven't been
        submitted yet.
        """
        for source in HeartbeatSource:
            if self.is_heartbeat_recent(source) is False:
                return True

        return False


def get_system_status():
    heartbeats = get_heartbeats()

    return SystemStatus(heartbeats=heartbeats)


def get_available_object_count():
    """
    Get the amount of objects that can be enqueued at the moment
    """
    pending_count = (
        db.session.query(MuseumObject)
        .with_transformation(MuseumObject.filter_preservation_pending)
        .count()
    )

    # Don't count the objects that are currently in the workflow
    pending_count -= len(get_enqueued_object_ids())

    return pending_count
