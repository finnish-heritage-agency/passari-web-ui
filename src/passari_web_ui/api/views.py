import json

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_

from passari_web_ui.db import db
from passari_workflow.db.models import MuseumObject, MuseumPackage
from passari_workflow.queue.queues import (QueueType, get_object_id2queue_map,
                                           get_queue)
from passari_workflow.redis.connection import get_redis_connection
from passari_workflow.scripts.reenqueue_object import \
    reenqueue_object as do_reenqueue_object
from passari_workflow.scripts.unfreeze_objects import \
    unfreeze_objects as do_unfreeze_objects
from rq.registry import FailedJobRegistry, StartedJobRegistry

routes = Blueprint("api", __name__)


STRING_TO_BOOLEAN = {
    "true": True,
    "1": True,
    "false": False,
    "0": False
}


def to_bool(s):
    """
    Convert a string representation of a boolean to True or False
    """
    if s in (True, False):
        # Just return the parameter if it's already a boolean
        return s

    return STRING_TO_BOOLEAN.get(s, None)


@routes.route("/overview-stats")
def overview_stats():
    """
    Retrieve real-time statistics used in the 'Overview' page
    """
    # Check cache first
    redis = get_redis_connection()
    result = redis.get("overview_stats")

    if result:
        result = json.loads(result)
        return jsonify(result)

    queues = (
        get_queue(QueueType.DOWNLOAD_OBJECT),
        get_queue(QueueType.CREATE_SIP),
        get_queue(QueueType.SUBMIT_SIP),
        get_queue(QueueType.CONFIRM_SIP)
    )
    job_count = sum([queue.count for queue in queues])

    failed_count = sum([
        FailedJobRegistry(queue=queue).count for queue in queues
    ])

    total_count = db.session.query(MuseumObject).count()

    frozen_count = (
        db.session.query(MuseumObject)
        .filter(MuseumObject.frozen)
        .count()
    )

    submitted_count = (
        db.session.query(MuseumObject)
        .join(
            MuseumPackage, MuseumObject.latest_package_id == MuseumPackage.id
        )
        .filter(
            and_(
                MuseumObject.latest_package,
                MuseumPackage.rejected == False,
                MuseumPackage.preserved == False,
                MuseumPackage.uploaded
            )
        )
        .count()
    )

    rejected_count = (
        db.session.query(MuseumObject)
        .join(
            MuseumPackage, MuseumObject.latest_package_id == MuseumPackage.id
        ).filter(
            and_(MuseumObject.latest_package, MuseumPackage.rejected)
        )
        .count()
    )

    preserved_count = (
        db.session.query(MuseumObject)
        .with_transformation(MuseumObject.exclude_preservation_pending)
        .filter(MuseumObject.preserved)
        .count()
    )

    result = {
        "steps": {
            "pending": {
                "count": int(
                    total_count
                    - job_count - failed_count - frozen_count - rejected_count
                    - submitted_count - preserved_count
                )
            },
        },
        "total_count": total_count
    }

    # Add the individual queues
    for queue in queues:
        result["steps"][queue.name] = {
            "count": queue.count
        }

    # Add counts outside of queues
    other_steps = [
        ("preserved", preserved_count),
        ("rejected", rejected_count),
        ("submitted", submitted_count),
        ("frozen", frozen_count),
        ("failed", failed_count)
    ]

    for name, count in other_steps:
        result["steps"][name] = {"count": count}

    # Cache result for 2 seconds
    redis.set("overview_stats", json.dumps(result), ex=2)
    return jsonify(result)


@routes.route("/navbar-stats")
def navbar_stats():
    """
    Retrieve object counts used for the navbar
    """
    # Check cache first
    redis = get_redis_connection()
    result = redis.get("navbar_stats")

    if result:
        result = json.loads(result)
        return jsonify(result)

    queues = (
        get_queue(QueueType.DOWNLOAD_OBJECT),
        get_queue(QueueType.CREATE_SIP),
        get_queue(QueueType.SUBMIT_SIP),
        get_queue(QueueType.CONFIRM_SIP)
    )
    result = {"queues": {}}
    for queue in queues:
        result["queues"][queue.name] = {
            "pending": queue.count,
            "processing": StartedJobRegistry(queue=queue).count
        }

    # Add failed
    result["failed"] = sum([
        FailedJobRegistry(queue=queue).count for queue in queues
    ])

    # Cache result for 2 seconds
    redis.set("navbar_stats", json.dumps(result), ex=2)
    return jsonify(result)


@routes.route("/list-frozen-objects")
def list_frozen_objects():
    """
    List and search frozen objects
    """
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    search_query = request.args.get("search", "")

    query = (
        db.session.query(MuseumObject)
        .filter_by(frozen=True)
        .order_by(MuseumObject.id)
    )

    if search_query.strip():
        try:
            # If an integer is provided, assume the user is searching
            # for a specific object
            object_id = int(search_query)
            query = query.filter_by(id=object_id)
        except ValueError:
            query = query.filter(
                or_(
                    MuseumObject.freeze_reason.ilike(f"%{search_query}%"),
                    MuseumObject.title.ilike(f"%{search_query}%")
                )
            )

    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    items = []
    for museum_object in pagination.items:
        items.append({
            "id": museum_object.id,
            "latest_package_id": museum_object.latest_package_id,
            "title": museum_object.title,
            "source": (
                "unknown" if not museum_object.freeze_source
                else museum_object.freeze_source.value
            ),
            "reason": museum_object.freeze_reason
        })

    result = {
        "results": items,
        "result_count": pagination.total,
        "page_numbers": list(pagination.iter_pages()),
        "page": page,
        "page_count": pagination.pages
    }

    return jsonify(result)


@routes.route("/list-sips")
def list_sips():
    """
    Query SIPs
    """
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    search_query = request.args.get("search", "")
    only_latest = to_bool(request.args.get("only_latest", False))
    preserved = to_bool(request.args.get("preserved", False))
    rejected = to_bool(request.args.get("rejected", False))
    processing = to_bool(request.args.get("processing", False))
    cancelled = to_bool(request.args.get("cancelled", False))

    query = db.session.query(MuseumPackage)

    if only_latest:
        query = (
            query.join(
                MuseumObject,
                MuseumPackage.id == MuseumObject.latest_package_id
            )
        )
    else:
        query = query.join(
            MuseumObject,
            MuseumPackage.museum_object_id == MuseumObject.id
        )

    all_selected = sum([preserved, rejected, processing, cancelled]) == 4
    none_selected = sum([preserved, rejected, processing, cancelled]) == 0
    if not all_selected and not none_selected:
        # If no filters are selected or all filters are selected, apply
        # no filters at all and retrieve all results
        or_clauses = []
        if preserved:
            or_clauses.append(MuseumPackage.preserved == True)
        if rejected:
            or_clauses.append(MuseumPackage.rejected == True)
        if cancelled:
            or_clauses.append(MuseumPackage.cancelled == True)
        if processing:
            # Package is under processing if none of the other statuses
            # apply
            or_clauses.append(
                and_(
                    MuseumPackage.preserved == False,
                    MuseumPackage.rejected == False,
                    MuseumPackage.cancelled == False
                )
            )

        query = query.filter(or_(*or_clauses))

    query = query.order_by(MuseumPackage.created_date.desc())

    if search_query.strip():
        try:
            # If an integer is provided, assume the user is searching
            # for a specific object
            object_id = int(search_query)
            query = query.filter(MuseumPackage.museum_object_id == object_id)
        except ValueError:
            query = query.filter(
                or_(
                    MuseumPackage.sip_filename.ilike(f"%{search_query}%"),
                    MuseumObject.title.ilike(f"%{search_query}%")
                )
            )

    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    # Retrieve the workflow status for each museum package
    object_ids = [
        museum_package.museum_object_id for museum_package in pagination.items
        if museum_package == museum_package.museum_object.latest_package
    ]
    object_id2queue_names = get_object_id2queue_map(object_ids)

    items = []
    for museum_package in pagination.items:
        if museum_package.cancelled:
            status = "cancelled"
        elif museum_package.preserved:
            status = "preserved"
        elif museum_package.rejected:
            status = "rejected"
        else:
            status = "processing"

        is_latest_package = \
            museum_package == museum_package.museum_object.latest_package

        items.append({
            "id": museum_package.id,
            "filename": museum_package.sip_filename,
            "object_id": museum_package.museum_object_id,
            "title": museum_package.museum_object.title,
            "status": status,
            "can_reenqueue": museum_package.rejected and is_latest_package,
            # Get the current queues for the object if they exist
            "queues": (
                object_id2queue_names[museum_package.museum_object_id]
                if is_latest_package and status == "processing" else []
            ),
            "uploaded": museum_package.uploaded
        })

    result = {
        "results": items,
        "result_count": pagination.total,
        "page_numbers": list(pagination.iter_pages()),
        "page": page,
        "page_count": pagination.pages
    }

    return jsonify(result)


@routes.route("/reenqueue-object", methods=["POST"])
def reenqueue_object():
    """
    Try re-enqueuing a single object
    """
    object_id = request.form.get("object_id", None)

    error = None

    try:
        do_reenqueue_object(object_id)
    except ValueError as exc:
        # Object hasn't been rejected yet, or it hasn't been rejected at all
        error = str(exc)

    if error:
        return jsonify({"success": False, "error": error})

    return jsonify({"success": True})


@routes.route("/unfreeze-objects", methods=["POST"])
def unfreeze_objects():
    """
    Try unfreezing multiple objects
    """
    object_ids = request.form.get("object_ids", None)
    reason = request.form.get("reason", None)
    enqueue = to_bool(request.form.get("enqueue", False))

    if object_ids:
        object_ids = object_ids.split(",")

    count = do_unfreeze_objects(
        object_ids=object_ids, reason=reason, enqueue=enqueue
    )

    return jsonify({"success": True, "count": count})


@routes.route("/get-log-content")
def get_log_content():
    """
    Get the content of a single log file for a SIP
    """
    sip_filename = request.args.get("sip_filename", None)
    log_filename = request.args.get("log_filename", None)

    museum_package = (
        db.session.query(MuseumPackage)
        .filter_by(sip_filename=sip_filename)
        .one()
    )

    log_content = museum_package.get_log_file_content(log_filename)

    return jsonify({"success": True, "data": log_content})
