import datetime

from flask import escape

import pytest
from passari_workflow.db.models import FreezeSource, MuseumObject
from passari_workflow.heartbeat import HeartbeatSource, submit_heartbeat
from passari_workflow.queue.queues import QueueType, get_queue
from rq import SimpleWorker
from rq.registry import StartedJobRegistry

TEST_DATE = datetime.datetime(2019, 1, 1, 0, 0)


@pytest.mark.usefixtures("user")
class TestChangePassword:
    def test_change_password(self, session, client, app):
        """
        Change the password and ensure it can be used to login
        """
        client.post(
            "/web-ui/change",
            data={
                "password": "testpassword",
                "new_password": "newtestpassword",
                "new_password_confirm": "newtestpassword"
            },
        )
        client.get("/web-ui/logout")
        result = client.get("/web-ui/login")

        # User was logged out
        assert b"Login" in result.data

        client.post(
            "/web-ui/login",
            data={"email": "test@test.com", "password": "newtestpassword"},
            follow_redirects=True
        )
        result = client.get("/web-ui/overview/")
        assert b"Logged in as" in result.data

    def test_invalid_password(self, session, client, app):
        """
        Try changing a password while providing the wrong password
        """
        result = client.post(
            "/web-ui/change",
            data={
                "password": "invalid",
                "new_password": "new_password",
                "new_password_confirm": "new_password"
            }
        )

        assert b"Invalid password" in result.data


@pytest.mark.usefixtures("user")
class TestSystemStatus:
    def test_system_status(self, session, client, app):
        """
        Test that system status is reported correctly using the heartbeat
        timestamps
        """
        result = client.get("/web-ui/system-status/")

        # No heartbeats have been recorded yet
        assert result.data.count(b"Last run: Never") == 4
        assert result.data.count(b"No heartbeat recorded</span>") == 4

        # Record a heartbeat
        submit_heartbeat(HeartbeatSource.SYNC_PROCESSED_SIPS)

        result = client.get("/web-ui/system-status/")

        # One heartbeat has been recorded now
        assert result.data.count(b"Last run: Never") == 3
        assert result.data.count(b"No heartbeat recorded") == 3
        assert result.data.count(b"Active</span>") == 1

        # Make the interval for 'sync_processed_sips' impossibly short.
        # This means it will appear as inactive.
        app.config["HEARTBEAT_INTERVAL_SYNC_PROCESSED_SIPS"] = "0"

        result = client.get("/web-ui/system-status/")

        assert result.data.count(b"Inactive</span>") == 1


@pytest.mark.usefixtures("user")
class TestEnqueueObjects:
    def test_enqueue_objects(self, session, client, museum_object_factory):
        """
        Test enqueueing two new objects with five fake preservable objects
        available
        """
        for i in range(0, 5):
            # Create five fake preservable objects
            museum_object_factory(
                id=i, created_date=TEST_DATE, modified_date=TEST_DATE,
                metadata_hash="", attachment_metadata_hash=""
            )

        result = client.get("/web-ui/enqueue-objects/")
        assert b"Enqueue objects</h1>" in result.data
        assert b"<b>5</b> are available" in result.data

        result = client.post(
            "/web-ui/enqueue-objects/", data={"object_count": "2"},
            follow_redirects=True
        )
        assert b"2 object(s) will be enqueued." in result.data

    def test_enqueue_objects_not_available(self, client):
        """
        Test enqueueing two new objects when no objects are available
        """
        result = client.post(
            "/web-ui/enqueue-objects/", data={"object_count": "2"}
        )
        assert b"There are no objects pending preservation" in result.data

    def test_enqueue_objects_incorrect_range(
            self, client, museum_object_factory):
        """
        Test enqueueing a negative aount of objects
        """
        for i in range(0, 5):
            # Create five fake preservable objects
            museum_object_factory(
                id=i, created_date=TEST_DATE, modified_date=TEST_DATE,
                metadata_hash="", attachment_metadata_hash=""
            )

        result = client.post(
            "/web-ui/enqueue-objects/", data={"object_count": "-1"}
        )
        assert b"Object count has to be in range 1 - 5" in result.data


@pytest.mark.usefixtures("user")
class TestReenqueueObject:
    def test_reenqueue_object(
            self, session, client, museum_object_factory,
            museum_package_factory):
        museum_object = museum_object_factory(
            id=2, created_date=TEST_DATE, modified_date=TEST_DATE
        )
        museum_package = museum_package_factory(
            id=4,
            museum_object=museum_object,
            sip_filename="testSIP.tar",
            rejected=True
        )
        museum_object.latest_package = museum_package
        session.commit()

        result = client.get("/web-ui/manage-sips/4")
        assert b"Re-enqueue" in result.data

        result = client.post(
            "/web-ui/manage-sips/4/reenqueue", follow_redirects=True
        )
        assert b"Object 2 was re-enqueued." in result.data

    def test_reenqueue_object_not_rejected(
            self, session, client, museum_object_factory,
            museum_package_factory):
        museum_object = museum_object_factory(
            id=2, created_date=TEST_DATE, modified_date=TEST_DATE
        )
        museum_package = museum_package_factory(
            id=4, sip_filename="testSIP.tar",
            museum_object=museum_object
        )
        museum_object.latest_package = museum_package
        session.commit()

        result = client.post(
            "/web-ui/manage-sips/4/reenqueue", follow_redirects=True
        )
        assert b"Latest package testSIP.tar wasn&#39;t rejected" in result.data


@pytest.mark.usefixtures("user")
class TestFrozenObjectStatistics:
    def test_frozen_object_statistics(
            self, session, client, museum_object_factory):
        """
        Create frozen objects with different reasons and check that they
        are displayed in order of occurrence
        """
        museum_object_factory(
            id=10, frozen=True, freeze_reason="Wrong header"
        )

        for i in range(20, 22):
            museum_object_factory(
                id=i, frozen=True, freeze_reason="Wrong file size"
            )

        result = client.get("/web-ui/frozen-object-statistics/")

        # 'Wrong file size' is displayed first
        assert (
            result.data.index(b"Wrong file size")
            < result.data.index(b"Wrong header")
        )

    def test_frozen_object_statistics_none(self, session, client):
        """
        Test that nothing is shown if no frozen objects are available
        """
        result = client.get("/web-ui/frozen-object-statistics/")

        assert b"No objects have been frozen" in result.data


@pytest.mark.usefixtures("user")
class TestFreezeObjects:
    def test_freeze_objects(self, session, client, museum_object_factory):
        """
        Test freezing two objects
        """
        for i in [5, 10]:
            museum_object_factory(
                id=i, created_date=TEST_DATE, modified_date=TEST_DATE
            )

        result = client.get("/web-ui/freeze-objects/")
        assert b"Freeze objects</h1>" in result.data

        result = client.post(
            "/web-ui/freeze-objects/",
            data={"reason": "Test reason", "object_ids": "10\n5"},
            follow_redirects=True
        )
        assert b"2 object(s) were frozen, 0 package(s) were cancelled" \
            in result.data

        assert (
            session.query(MuseumObject)
            .filter(MuseumObject.id.in_([5, 10]))
            .filter_by(
                frozen=True,
                freeze_reason="Test reason",
                freeze_source=FreezeSource.USER
            )
            .count() == 2
        )

        # Auto-completion entry can be found in the page
        result = client.get("/web-ui/freeze-objects/")
        assert b"Test reason" in result.data

    def test_freeze_objects_not_found(self, session, client):
        """
        Test freezing two objects that don't exist
        """
        result = client.post(
            "/web-ui/freeze-objects/",
            data={"reason": "Test reason", "object_ids": "10\n5"}
        )
        assert escape(
            "Following objects don't exist: 5, 10"
        ).encode("utf-8") in result.data

    def test_freeze_objects_already_running(
            self, session, client, museum_object_factory):
        """
        Test freezing two objects that already have running jobs
        """
        def successful_job():
            return ":)"

        confirm_queue = get_queue(QueueType.CONFIRM_SIP)
        started_registry = StartedJobRegistry(queue=confirm_queue)

        for i in [5, 10]:
            museum_object_factory(id=i)
            job = confirm_queue.enqueue(
                successful_job, job_id=f"download_object_{i}"
            )
            started_registry.add(job, -1)

        result = client.post(
            "/web-ui/freeze-objects/",
            data={"reason": "Test reason", "object_ids": "10\n5"}
        )
        assert (
            escape(
                "following object IDs have running jobs and can't be frozen: "
                "5, 10"
            ).encode("utf-8") in result.data
        )


@pytest.mark.usefixtures("user")
class TestUnfreezeObjects:
    def test_unfreeze_objects(self, client, session, museum_object_factory):
        """
        Test unfreezing two objects with a specific reason
        """
        museum_object_factory(id=1, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=2, frozen=True, freeze_reason="Test reason B")
        museum_object_factory(id=3, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=4, frozen=True, freeze_reason="Test reason B")

        # Auto-completion entries can be found
        result = client.get("/web-ui/unfreeze-objects/")
        assert b"Test reason A" in result.data
        assert b"Test reason B" in result.data

        # Objects 1 and 3 will be unfrozen
        result = client.post(
            "/web-ui/unfreeze-objects/", data={"reason": "Test reason A"},
            follow_redirects=True
        )
        assert b"2 object(s) were unfrozen." in result.data

        assert (
            session.query(MuseumObject)
            .filter(MuseumObject.id.in_([1, 3]))
            .filter_by(frozen=False)
            .count() == 2
        )

        queue = get_queue(QueueType.DOWNLOAD_OBJECT)

        # Objects are not enqueued by default
        assert len(queue.job_ids) == 0

    def test_unfreeze_objects_enqueue(
            self, client, session, museum_object_factory):
        """
        Test unfreezing an object and enqueuing it immediately
        """
        museum_object_factory(id=1, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=2, frozen=True, freeze_reason="Test reason B")

        # Unfreeze object 2
        result = client.post(
            "/web-ui/unfreeze-objects/",
            data={
                "reason": "Test reason B",
                "enqueue": True
            },
            follow_redirects=True
        )
        assert b"1 object(s) were unfrozen." in result.data

        assert (
            session.query(MuseumObject)
            .filter_by(id=2, frozen=False)
            .count() == 1
        )

        queue = get_queue(QueueType.DOWNLOAD_OBJECT)

        # Object was enqueued
        assert set(["download_object_2"]) == set(queue.job_ids)

    def test_unfreeze_objects_not_found(self, client):
        """
        Test unfreezing objects with a reason that's not used anywhere
        """
        result = client.post(
            "/web-ui/unfreeze-objects/", data={"reason": "Nonexistent reason"}
        )
        assert b"No objects with this reason were found" in result.data


@pytest.mark.usefixtures("user")
class TestRedirectToSip:
    def test_redirect_to_sip(
            self, client, museum_package_factory, museum_object_factory):
        """
        Test that user is redirected to the "View SIP" page
        """
        museum_object = museum_object_factory(id=2)
        museum_package_factory(
            id=5, sip_id="testSipID", museum_object=museum_object
        )

        result = client.get("/web-ui/redirect-to-sip/2/testSipID")
        assert result.headers["Location"].endswith("/manage-sips/5")
