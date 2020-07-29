from flask_wtf import FlaskForm
from wtforms.fields import BooleanField, Field, IntegerField, StringField
from wtforms.validators import InputRequired, ValidationError
from wtforms.widgets import TextArea

from passari_web_ui.db import db
from passari_web_ui.ui.utils import get_available_object_count
from passari_workflow.db.models import MuseumObject


class EnqueueObjectsForm(FlaskForm):
    """
    Form to enqueue a certain amount of objects
    """
    object_count = IntegerField(validators=[InputRequired()])

    def validate_object_count(self, field):
        available_count = get_available_object_count()

        if available_count == 0:
            raise ValidationError(
                "There are no objects pending preservation at the moment"
            )

        if field.data < 1 or field.data > available_count:
            raise ValidationError(
                f"Object count has to be in range 1 - {available_count}"
            )


class ReenqueueObjectForm(FlaskForm):
    """
    Form to re-enqueue a single object
    """
    object_id = IntegerField("Object ID", validators=[InputRequired()])

    def validate_object_id(self, field):
        exists = (
            db.session.query(MuseumObject)
            .filter(MuseumObject.id == field.data)
            .one_or_none()
        )
        if not exists:
            raise ValidationError("Object with the given ID does not exist")


class MultipleObjectIDField(Field):
    """
    Field for retrieving a list of multiple object IDs
    """
    widget = TextArea()

    def _value(self):
        if self.data:
            return "\n".join(self.data)
        else:
            return ""

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = [
                    int(entry.strip()) for entry in valuelist[0].split("\n")
                ]
            except ValueError:
                self.data = None
        else:
            self.data = []


def object_ids_exist_check(form, field):
    """
    Check that all given object IDs exist
    """
    if not field.data:
        raise ValidationError("No object ID was provided")

    existing_object_ids = [
        result[0] for result in
        db.session.query(MuseumObject.id)
        .filter(MuseumObject.id.in_(field.data))
        .all()
    ]

    missing_object_ids = set(field.data) - set(existing_object_ids)

    if missing_object_ids:
        raise ValidationError(
            f"Following objects don't exist: "
            f"{', '.join([str(o) for o in sorted(missing_object_ids)])}"
        )


class FreezeObjectsForm(FlaskForm):
    """
    Form for freezing multiple objects with a single reason
    """
    object_ids = MultipleObjectIDField(
        "Object IDs", validators=[object_ids_exist_check]
    )
    reason = StringField(
        description=(
            "Reason for freezing the object(s). Use an identical reason for "
            "multiple related objects to ensure they can be all unfrozen with "
            "one query."
        ),
        validators=[InputRequired()]
    )


def object_with_reason_exist_check(form, field):
    """
    Check that at least one frozen object with the given reason exists
    """
    result = (
        db.session.query(MuseumObject)
        .filter(MuseumObject.frozen)
        .filter(MuseumObject.freeze_reason == field.data)
        .first()
    )

    if not result:
        raise ValidationError("No objects with this reason were found.")


class UnfreezeObjectsForm(FlaskForm):
    """
    Form to unfreeze objects with the given reason
    """
    reason = StringField(
        description=(
            "Reason used to freeze the object(s). All objects with this exact "
            "reason are unfrozen."
        ),
        validators=[object_with_reason_exist_check]
    )
    enqueue = BooleanField(
        description="Enqueue objects immediately after unfreezing.",
        default=False
    )
