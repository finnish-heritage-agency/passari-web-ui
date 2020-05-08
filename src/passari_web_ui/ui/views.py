from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for)
from flask_security import login_required
from sqlalchemy import func

from passari_web_ui.db import db
from passari_web_ui.ui.forms import (EnqueueObjectsForm,
                                            FreezeObjectsForm,
                                            ReenqueueObjectForm,
                                            UnfreezeObjectsForm)
from passari_web_ui.ui.util import get_available_object_count
from passari_workflow.db.models import (FreezeSource, MuseumObject,
                                               MuseumPackage)
from passari_workflow.exceptions import WorkflowJobRunningError
from passari_workflow.scripts.enqueue_objects import \
    enqueue_objects as do_enqueue_objects
from passari_workflow.scripts.freeze_objects import \
    freeze_objects as do_freeze_objects
from passari_workflow.scripts.reenqueue_object import \
    reenqueue_object as do_reenqueue_object
from passari_workflow.scripts.unfreeze_objects import \
    unfreeze_objects as do_unfreeze_objects

routes = Blueprint(
    "ui", __name__, template_folder="templates", static_folder="static")


@routes.route("/")
def home():
    """
    Redirect to "Overview" page if web UI root is accessed
    """
    return redirect(url_for("ui.overview"))


@routes.route("/overview/")
def overview():
    """
    Display a real-time overview of the preservation workflow
    """
    return render_template("tabs/overview.html")


@routes.route("/system-status/")
def system_status():
    """
    Display system status to help determine if some features are not working
    correctly
    """
    return render_template("tabs/system_status.html")


@routes.route("/reenqueue-object/", methods=("GET", "POST"))
def reenqueue_object():
    """
    Re-enqueue a rejected object
    """
    form = ReenqueueObjectForm()

    if form.validate_on_submit():
        try:
            do_reenqueue_object(form.object_id.data)
        except ValueError as exc:
            # Object hasn't been rejected yet, or it hasn't been rejected
            # at all
            return render_template(
                "tabs/reenqueue_object/reenqueue_object.html",
                form=form, error=str(exc)
            )

        flash(
            f"Object {form.object_id.data} was re-enqueued.",
            category="reenqueue_object"
        )
        return redirect(url_for("ui.reenqueue_object_success"))

    return render_template(
        "tabs/reenqueue_object/reenqueue_object.html",
        form=form
    )


@routes.route("/reenqueue-object/success/")
def reenqueue_object_success():
    """
    Display a "re-enqueue successful" message
    """
    return render_template(
        "tabs/reenqueue_object/reenqueue_object_success.html"
    )


@routes.route("/enqueue-objects/", methods=("GET", "POST"))
def enqueue_objects():
    """
    Enqueue objects pending preservation to the workflow
    """
    available_count = get_available_object_count()

    form = EnqueueObjectsForm()

    if form.validate_on_submit():
        enqueued_count = do_enqueue_objects(form.object_count.data)
        flash(
            f"{enqueued_count} object(s) were enqueued.",
            category="enqueue_objects"
        )
        return redirect(url_for("ui.enqueue_objects_success"))

    return render_template(
        "tabs/enqueue_objects/enqueue_objects.html",
        available_count=available_count,
        form=form
    )


@routes.route("/enqueue-objects/success/")
def enqueue_objects_success():
    """
    Display a "enqueueing objects successful" message
    """
    return render_template(
        "tabs/enqueue_objects/enqueue_objects_success.html"
    )


@routes.route("/manage-frozen-objects/")
def manage_frozen_objects():
    """
    Manage objects that have been frozen due to being unsuitable for
    preservation for time being
    """
    return render_template(
        "tabs/manage_frozen_objects/manage_frozen_objects.html"
    )


@routes.route("/frozen-object-statistics/")
def frozen_object_statistics():
    """
    Display a list of freeze reasons sorted by occurrence count
    """
    reason_counts = (
        db.session.query(
            MuseumObject.freeze_reason, func.count(MuseumObject.freeze_reason)
        )
        .filter(MuseumObject.frozen == True)
        .group_by(MuseumObject.freeze_reason)
        .order_by(func.count(MuseumObject.freeze_reason).desc())
        .all()
    )

    return render_template(
        "tabs/frozen_object_statistics/frozen_object_statistics.html",
        reason_counts=reason_counts
    )


@routes.route("/freeze-objects/", methods=("GET", "POST"))
def freeze_objects():
    """
    Freeze objects to prevent them from being enqueued
    """
    object_ids = request.args.get("object_ids", "")
    # Prepopulate the "object IDs" field if GET parameter was provided
    form = FreezeObjectsForm(data={"object_ids": object_ids})

    if form.validate_on_submit():
        object_ids = [object_id for object_id in form.object_ids.data]

        try:
            frozen_count, cancel_count = do_freeze_objects(
                reason=form.reason.data if form.reason.data != "" else "",
                object_ids=object_ids,
                source=FreezeSource.USER
            )
        except WorkflowJobRunningError as exc:
            # Object couldn't be frozen because a workflow job was already
            # running
            return render_template(
                "tabs/freeze_objects/freeze_objects.html",
                form=form, error=str(exc)
            )

        flash(
            f"{frozen_count} object(s) were frozen, "
            f"{cancel_count} package(s) were cancelled.",
            category="freeze_objects"
        )
        return redirect(url_for("ui.freeze_objects_success"))

    return render_template(
        "tabs/freeze_objects/freeze_objects.html",
        form=form
    )


@routes.route("/freeze-objects/success/")
def freeze_objects_success():
    """
    Display a "freezing object successful" message
    """
    return render_template(
        "tabs/freeze_objects/freeze_objects_success.html"
    )


@routes.route("/unfreeze-objects/", methods=("GET", "POST"))
def unfreeze_objects():
    """
    Unfreeze objects to make them eligible for preservation again
    """
    reason = request.args.get("reason", "")
    # Prepopulate the "reason" field if GET parameter was provided
    form = UnfreezeObjectsForm(data={"reason": reason})

    if form.validate_on_submit():
        unfrozen_count = do_unfreeze_objects(
            reason=form.reason.data,
            enqueue=form.enqueue.data
        )
        flash(
            f"{unfrozen_count} object(s) were unfrozen.",
            category="unfreeze_objects"
        )
        return redirect(url_for("ui.unfreeze_objects_success"))

    return render_template(
        "tabs/unfreeze_objects/unfreeze_objects.html",
        form=form
    )


@routes.route("/unfreeze-objects/success/")
def unfreeze_objects_success():
    """
    Display a "unfreezing objects successful" message
    """
    return render_template(
        "tabs/unfreeze_objects/unfreeze_objects_success.html"
    )


@routes.route("/redirect-to-sip/<object_id>/<sip_id>")
def redirect_to_sip(object_id, sip_id):
    """
    Redirect to the SIP's "View single SIP" page.

    This is used in the RQ dashboard views where we don't have access to the
    SIP filename.
    """
    object_id = int(object_id)

    museum_package = (
        db.session.query(MuseumPackage)
        .filter(MuseumPackage.museum_object_id == object_id)
        .filter(MuseumPackage.sip_id == sip_id)
        .one()
    )

    return redirect(
        url_for("ui.view_single_sip", package_id=museum_package.id)
    )


@routes.route("/manage-sips/")
def manage_sips():
    """
    Manage SIPs (eg. re-enqueue rejected SIPs, view logs, perform searches)
    """
    return render_template(
        "tabs/manage_sips/manage_sips.html"
    )


@routes.route("/manage-sips/<package_id>")
def view_single_sip(package_id):
    """
    View a SIP and its log files
    """
    package_id = int(package_id)

    museum_package = (
        db.session.query(MuseumPackage)
        .join(MuseumObject, MuseumPackage.museum_object_id == MuseumObject.id)
        .filter(MuseumPackage.id == package_id)
        .one()
    )

    log_filenames = museum_package.get_log_filenames()

    can_reenqueue = (
        museum_package.rejected
        and museum_package == museum_package.museum_object.latest_package
    )

    return render_template(
        "tabs/manage_sips/view_single_sip.html",
        package=museum_package,
        log_filenames=log_filenames,
        can_reenqueue=can_reenqueue
    )


@routes.route("/manage-sips/<package_id>/reenqueue", methods=("POST",))
def view_single_sip_reenqueue(package_id):
    """
    Re-enqueue a SIP
    """
    package_id = int(package_id)

    museum_package = (
        db.session.query(MuseumPackage)
        .join(MuseumObject, MuseumPackage.museum_object_id == MuseumObject.id)
        .filter(MuseumPackage.id == package_id)
        .one()
    )

    try:
        do_reenqueue_object(museum_package.museum_object_id)
        flash(
            f"Object {museum_package.museum_object_id} was re-enqueued.",
            category="view_single_sip"
        )
    except ValueError as exc:
        # Object hasn't been rejected yet, or it hasn't been rejected
        # at all
        flash(str(exc), category="view_single_sip_error")

    return redirect(url_for("ui.view_single_sip", package_id=package_id))
