import datetime

import pytest
from passari_workflow.db.models import FreezeSource, MuseumObject
from passari_workflow.queue.queues import QueueType, get_queue
from rq import SimpleWorker
from rq.registry import StartedJobRegistry

TEST_DATE = datetime.datetime(2019, 1, 1, 0, 0)


def successful_job():
    return ":)"


def failing_job():
    raise RuntimeError(":(")


@pytest.mark.usefixtures("user")
class TestOverviewStats:
    def test_overview_stats(
            self, session, client, museum_object_factory,
            museum_package_factory):
        def successful_job():
            return ":)"

        def failing_job():
            raise RuntimeError(":(")

        # Create 26 Museum Objects in total...
        # ...1 which is pending
        museum_object_factory()

        for _ in range(0, 2):
            # ...2 which have been accepted
            date = datetime.datetime.now()
            museum_object = museum_object_factory(
                preserved=True,
                created_date=datetime.datetime.now()
            )
            museum_package = museum_package_factory(
                museum_object=museum_object,
                object_modified_date=date, preserved=True
            )
            museum_object.latest_package = museum_package
            session.commit()

        for _ in range(0, 3):
            # ...3 which have been rejected
            museum_object = museum_object_factory()
            museum_package = museum_package_factory(
                museum_object=museum_object,
                rejected=True)
            museum_object.latest_package = museum_package
            session.commit()

        for _ in range(0, 4):
            # ...4 which have been frozen
            museum_object_factory(frozen=True)

        for _ in range(0, 5):
            # ...5 which have been submitted and are awaiting confirmation
            museum_object = museum_object_factory()
            museum_package = museum_package_factory(
                museum_object=museum_object,
                uploaded=True
            )
            museum_object.latest_package = museum_package
            session.commit()

        # Create the remaining 11 objects for the rest
        mus_id = museum_object_factory().id
        for _ in range(0, 10):
            museum_object_factory()

        # ...1 which has failed
        queue = get_queue(QueueType.CONFIRM_SIP)
        queue.enqueue(failing_job, job_id=f"confirm_sip_{mus_id}")
        SimpleWorker([queue], connection=queue.connection).work(burst=True)

        # ...1 in the 'download object' queue
        get_queue(QueueType.DOWNLOAD_OBJECT).enqueue(
            successful_job, job_id=f"download_object_{mus_id+1}")

        for i in range(2, 4):
            # ...2 in the 'create_sip' queue
            get_queue(QueueType.CREATE_SIP).enqueue(
                successful_job, job_id=f"create_sip_{mus_id+i}")

        for i in range(4, 7):
            # ...3 in the 'submit_sip' queue
            get_queue(QueueType.SUBMIT_SIP).enqueue(
                successful_job, job_id=f"submit_sip_{mus_id+i}")

        for i in range(7, 11):
            # ...4 in the 'confirm_sip' queue
            get_queue(QueueType.CONFIRM_SIP).enqueue(
                successful_job, job_id=f"confirm_sip_{mus_id+i}")

        result = client.get("/api/overview-stats").json

        assert result["steps"]["pending"]["count"] == 1
        assert result["steps"]["preserved"]["count"] == 2
        assert result["steps"]["rejected"]["count"] == 3
        assert result["steps"]["frozen"]["count"] == 4
        assert result["steps"]["submitted"]["count"] == 5
        assert result["steps"]["failed"]["count"] == 1
        assert result["steps"]["download_object"]["count"] == 1
        assert result["steps"]["create_sip"]["count"] == 2
        assert result["steps"]["submit_sip"]["count"] == 3
        assert result["steps"]["confirm_sip"]["count"] == 4

        assert result["total_count"] == 26


@pytest.mark.usefixtures("user")
class TestNavbarStats:
    def test_navbar_stats(self, session, client):
        # Create 1 'download_object' job
        get_queue(QueueType.DOWNLOAD_OBJECT).enqueue(
            successful_job, job_id="download_object_1"
        )

        # Create 2 'create_sip' jobs
        for i in range(2, 4):
            get_queue(QueueType.CREATE_SIP).enqueue(
                successful_job, job_id=f"create_sip_{i}"
            )

        # Create 1 failed 'submit_sip' job
        submit_queue = get_queue(QueueType.SUBMIT_SIP)
        submit_queue.enqueue(
            failing_job, job_id="submit_sip_4")
        SimpleWorker(
            [submit_queue], connection=submit_queue.connection
        ).work(burst=True)

        # Create 1 started 'confirm_sip' job
        confirm_queue = get_queue(QueueType.CONFIRM_SIP)
        started_registry = StartedJobRegistry(queue=confirm_queue)
        job = confirm_queue.enqueue(successful_job, job_id="confirm_sip_5")
        started_registry.add(job, -1)

        result = client.get("/api/navbar-stats").json

        assert result["queues"]["download_object"] \
            == {"processing": 0, "pending": 1}
        assert result["queues"]["create_sip"] == \
            {"processing": 0, "pending": 2}
        assert result["queues"]["submit_sip"] == \
            {"processing": 0, "pending": 0}
        # TODO: In practice, if one worker is working on a job and there are
        # no pending jobs, this should be 'processing': 1, 'pending': 0.
        # How can we mimic a similar situation in this test scenario?
        assert result["queues"]["confirm_sip"] == \
            {"processing": 1, "pending": 1}

        assert result["failed"] == 1


@pytest.mark.usefixtures("user")
class TestListFrozenObjects:
    def test_list_frozen_objects(
            self, session, client, museum_object_factory,
            museum_package_factory):
        for i in range(0, 20):
            museum_object_factory(
                id=i,
                title=f"Object {i}",
                preserved=False,
                frozen=True,
                freeze_source=FreezeSource.USER,
                freeze_reason=f"Object {i} frozen"
            )

        # Add a latest package only for the second object
        museum_object_b = session.query(MuseumObject).get(1)
        museum_object_b.latest_package = museum_package_factory(
            id=10,
            museum_object=museum_object_b
        )
        session.commit()

        # Get the first page
        result = client.get(
            "/api/list-frozen-objects",
            query_string={"limit": 10}
        ).json

        assert len(result["results"]) == 10
        assert result["results"][0]["id"] == 0
        assert result["results"][0]["title"] == "Object 0"
        assert result["results"][0]["reason"] == "Object 0 frozen"
        assert result["results"][0]["source"] == "user"
        assert result["results"][0]["latest_package_id"] is None

        assert result["results"][1]["id"] == 1
        assert result["results"][1]["title"] == "Object 1"
        assert result["results"][1]["reason"] == "Object 1 frozen"
        assert result["results"][1]["latest_package_id"] == 10

        assert result["page_numbers"] == [1, 2]
        assert result["page_count"] == 2

        # Get the second page
        result = client.get(
            "/api/list-frozen-objects",
            query_string={"limit": 10, "page": 2}
        ).json

        assert len(result["results"]) == 10
        assert result["results"][0]["id"] == 10
        assert result["results"][0]["title"] == "Object 10"
        assert result["results"][0]["reason"] == "Object 10 frozen"
        assert result["results"][1]["id"] == 11
        assert result["results"][1]["title"] == "Object 11"
        assert result["results"][1]["reason"] == "Object 11 frozen"

    def test_list_frozen_objects_empty(self, client):
        result = client.get("/api/list-frozen-objects").json

        assert len(result["results"]) == 0
        assert result["page_numbers"] == []
        assert result["page_count"] == 0


@pytest.mark.usefixtures("user")
class TestListSips:
    def test_list_sips(
            self, client, session, museum_object_factory,
            museum_package_factory):
        # Create a preserved and a rejected package
        museum_package_factory(
            id=1,
            sip_filename="rejected.tar",
            uploaded=True,
            rejected=True,
            museum_object=museum_object_factory(
                id=10,
                title="Object that will be rejected"
            )
        )
        museum_package_factory(
            id=2,
            sip_filename="preserved.tar",
            uploaded=True,
            preserved=True,
            museum_object=museum_object_factory(
                id=20,
                preserved=True,
                title="Object that will be preserved"
            )
        )

        result = client.get(
            "/api/list-sips",
            query_string={"limit": 10}
        ).json

        assert len(result["results"]) == 2
        assert result["results"][0] == {
            "id": 2,
            "object_id": 20,
            "filename": "preserved.tar",
            "title": "Object that will be preserved",
            "status": "preserved",
            "uploaded": True,
            "queues": [],
            "can_reenqueue": False
        }
        assert result["results"][1] == {
            "id": 1,
            "object_id": 10,
            "filename": "rejected.tar",
            "title": "Object that will be rejected",
            "status": "rejected",
            "uploaded": True,
            "queues": [],
            "can_reenqueue": False
        }

    def test_list_sips_can_reenqueue(
            self, client, session, museum_object_factory,
            museum_package_factory):
        museum_package = museum_package_factory(
            id=1, sip_filename="test.tar", rejected=True,
            museum_object=museum_object_factory(
                id=10, title="Object"
            )
        )

        result = client.get("/api/list-sips").json

        assert not result["results"][0]["can_reenqueue"]

        # Re-enqueuing is possible when the latest package has failed
        museum_package.museum_object.latest_package = museum_package
        session.commit()

        result = client.get("/api/list-sips").json

        assert result["results"][0]["can_reenqueue"]

    def test_list_sips_filter_by_status(
            self, client, session, museum_object_factory,
            museum_package_factory):
        museum_object_a = museum_object_factory(
            id=10, preserved=True, title="Object A"
        )
        museum_object_b = museum_object_factory(
            id=20, title="Object B"
        )

        museum_package_factory(
            museum_object=museum_object_a,
            sip_filename="testA_a.tar", preserved=True
        )
        museum_package_factory(
            museum_object=museum_object_a,
            sip_filename="testA_b.tar", rejected=True
        )
        museum_package_factory(
            museum_object=museum_object_a,
            sip_filename="testA_c.tar", cancelled=True
        )
        museum_package_factory(
            museum_object=museum_object_a,
            sip_filename="testA_d.tar"
        )

        museum_package_factory(
            museum_object=museum_object_b,
            sip_filename="testB_a.tar", preserved=True
        )
        museum_package_factory(
            museum_object=museum_object_b,
            sip_filename="testB_b.tar", rejected=True
        )
        museum_package_factory(
            museum_object=museum_object_b,
            sip_filename="testB_c.tar", cancelled=True
        )
        museum_package_factory(
            museum_object=museum_object_b,
            sip_filename="testB_d.tar"
        )

        # At first, retrieve all packages, using no query parameters
        # and using all query parameters
        result = client.get("/api/list-sips").json
        assert len(result["results"]) == 8
        result = client.get(
            "/api/list-sips",
            query_string={
                "preserved": "true", "rejected": "true",
                "cancelled": "true", "processing": "true"
            }
        ).json
        assert len(result["results"]) == 8

        # Retrieve only preserved packages
        result = client.get(
            "/api/list-sips",
            query_string={"preserved": "true"}
        ).json
        assert len(result["results"]) == 2
        assert result["results"][0]["filename"] == "testB_a.tar"
        assert result["results"][1]["filename"] == "testA_a.tar"

        # Retrieve only rejected packages
        result = client.get(
            "/api/list-sips",
            query_string={"rejected": "true"}
        ).json
        assert len(result["results"]) == 2
        assert result["results"][0]["filename"] == "testB_b.tar"
        assert result["results"][1]["filename"] == "testA_b.tar"

        # Retrieve only cancelled packages
        result = client.get(
            "/api/list-sips",
            query_string={"cancelled": "true"}
        ).json
        assert len(result["results"]) == 2
        assert result["results"][0]["filename"] == "testB_c.tar"
        assert result["results"][1]["filename"] == "testA_c.tar"

        # Retrieve only packages under processing
        result = client.get(
            "/api/list-sips",
            query_string={"processing": "true"}
        ).json
        assert len(result["results"]) == 2
        assert result["results"][0]["filename"] == "testB_d.tar"
        assert result["results"][1]["filename"] == "testA_d.tar"

    def test_list_sips_only_latest(
            self, client, session, museum_object_factory,
            museum_package_factory):
        museum_object_a = museum_object_factory(
            id=10, preserved=True, title="Object A"
        )
        museum_object_b = museum_object_factory(
            id=20, title="Object B"
        )
        museum_object_c = museum_object_factory(
            id=30, preserved=True, title="Object C"
        )

        museum_package_factory(
            museum_object=museum_object_a,
            sip_filename="testA_A.tar", preserved=True
        )
        pkg_a_b = museum_package_factory(
            museum_object=museum_object_a,
            sip_filename="testA_B.tar", rejected=True,
            created_date=datetime.datetime(
                year=2019, month=2, day=1, tzinfo=datetime.timezone.utc
            )
        )
        museum_object_a.latest_package = pkg_a_b

        pkg_b = museum_package_factory(
            museum_object=museum_object_b,
            sip_filename="testB.tar", rejected=True,
            created_date=datetime.datetime(
                year=2019, month=3, day=1, tzinfo=datetime.timezone.utc
            )
        )
        museum_object_b.latest_package = pkg_b

        museum_package_factory(
            museum_object=museum_object_c,
            sip_filename="testC_A.tar", rejected=True
        )
        pkg_c_b = museum_package_factory(
            museum_object=museum_object_c,
            sip_filename="testC_B.tar", preserved=True,
            created_date=datetime.datetime(
                year=2019, month=1, day=1, tzinfo=datetime.timezone.utc
            )
        )
        museum_object_c.latest_package = pkg_c_b

        session.commit()

        result = client.get(
            "/api/list-sips",
            query_string={"only_latest": "true"}
        ).json

        # Only three results should be returned in this order: B, A, C
        assert len(result["results"]) == 3
        assert result["results"][0]["filename"] == "testB.tar"
        assert result["results"][1]["filename"] == "testA_B.tar"
        assert result["results"][2]["filename"] == "testC_B.tar"

    def test_list_sips_queues(
            self, client, session, museum_object_factory,
            museum_package_factory):
        """
        Test that the queue names for object are provided correctly
        """
        museum_object_a = museum_object_factory(
            id=10, preserved=True, title="Object A"
        )
        museum_object_b = museum_object_factory(
            id=20, title="Object B"
        )

        museum_package_a = museum_package_factory(
            museum_object=museum_object_a,
            sip_filename="testA.tar"
        )
        museum_object_a.latest_package = museum_package_a

        museum_package_factory(
            museum_object=museum_object_b,
            sip_filename="testB.tar"
        )

        session.commit()

        # Enqueue two tasks for each package
        get_queue(QueueType.DOWNLOAD_OBJECT).enqueue(
            successful_job, job_id="download_object_10"
        )
        get_queue(QueueType.SUBMIT_SIP).enqueue(
            successful_job, job_id="submit_sip_20"
        )

        result = client.get("/api/list-sips",).json

        # Only object A will report the queue names, since it's the latest
        # package
        assert len(result["results"]) == 2
        assert result["results"][0]["filename"] == "testB.tar"
        assert result["results"][0]["queues"] == []

        assert result["results"][1]["filename"] == "testA.tar"
        assert result["results"][1]["queues"] == ["download_object"]


@pytest.mark.usefixtures("user")
class TestUnfreezeObjects:
    def test_unfreeze_objects_reason(
            self, client, session, museum_object_factory):
        """
        Unfreeze two objects using a reason as the filter
        """
        museum_object_factory(id=1, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=2, frozen=True, freeze_reason="Test reason B")
        museum_object_factory(id=3, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=4, frozen=True, freeze_reason="Test reason B")

        # Objects 1 and 3 will be unfrozen
        result = client.post(
            "/api/unfreeze-objects",
            data={"reason": "Test reason A"}
        )
        assert result.json == {"success": True, "count": 2}

        assert (
            session.query(MuseumObject)
            .filter(MuseumObject.id.in_([1, 3]))
            .filter(MuseumObject.frozen == False)
            .count() == 2
        )

        queue = get_queue(QueueType.DOWNLOAD_OBJECT)

        # Object is not enqueued by default
        assert len(queue.job_ids) == 0

    def test_unfreeze_objects_enqueue(
            self, client, session, museum_object_factory):
        """
        Unfreeze an object and enqueue it
        """
        museum_object_factory(id=1, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=2, frozen=True, freeze_reason="Test reason B")

        # Object 2 will be unfrozen
        result = client.post(
            "/api/unfreeze-objects",
            data={"reason": "Test reason B", "enqueue": "true"}
        )
        assert result.json == {"success": True, "count": 1}

        assert (
            session.query(MuseumObject)
            .filter_by(id=2, frozen=False)
            .count() == 1
        )

        queue = get_queue(QueueType.DOWNLOAD_OBJECT)

        assert set(["download_object_2"]) == set(queue.job_ids)

    def test_unfreeze_objects_object_ids(
            self, client, session, museum_object_factory):
        """
        Unfreeze two objects using object IDs
        """
        for i in range(0, 4):
            museum_object_factory(
                id=i, frozen=True, freeze_reason="Test reason"
            )

        # Objects 1 and 3 will be frozen
        result = client.post(
            "/api/unfreeze-objects",
            data={"object_ids": "1,3"}
        )
        assert result.json == {"success": True, "count": 2}

        assert (
            session.query(MuseumObject)
            .filter(MuseumObject.id.in_([1, 3]))
            .filter(MuseumObject.frozen == False)
            .count() == 2
        )

    def test_unfreeze_objects_reason_and_object_ids(
            self, client, session, museum_object_factory):
        """
        Unfreeze one object using object IDs and a reason as filters
        """
        museum_object_factory(id=1, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=2, frozen=True, freeze_reason="Test reason B")
        museum_object_factory(id=3, frozen=True, freeze_reason="Test reason A")
        museum_object_factory(id=4, frozen=True, freeze_reason="Test reason B")

        # Only object 3 will be frozen in this case
        result = client.post(
            "/api/unfreeze-objects",
            data={"object_ids": "2,3", "reason": "Test reason A"}
        )
        assert result.json == {"success": True, "count": 1}

        assert (
            session.query(MuseumObject)
            .filter(MuseumObject.frozen == False)
            .one().id == 3
        )


@pytest.mark.usefixtures("user")
class TestReenqueueObject:
    def test_reenqueue_object(
            self, session, client, museum_object_factory,
            museum_package_factory):
        museum_object = museum_object_factory(
            id=2, created_date=TEST_DATE, modified_date=TEST_DATE
        )
        museum_package = museum_package_factory(
            sip_filename="testSIP.tar",
            rejected=True
        )
        museum_object.latest_package = museum_package
        session.commit()

        result = client.get("/web-ui/reenqueue-object/")
        assert b"Re-enqueue object</h1>" in result.data

        result = client.post(
            "/api/reenqueue-object", data={"object_id": "2"}
        ).json
        assert result["success"]

    def test_reenqueue_object_not_rejected(
            self, session, client, museum_object_factory,
            museum_package_factory):
        museum_object = museum_object_factory(
            id=2, created_date=TEST_DATE, modified_date=TEST_DATE
        )
        museum_package = museum_package_factory(
            sip_filename="testSIP.tar",
        )
        museum_object.latest_package = museum_package
        session.commit()

        result = client.post(
            "/api/reenqueue-object", data={"object_id": "2"},
        ).json
        assert not result["success"]
        assert result["error"] == "Latest package testSIP.tar wasn't rejected"
