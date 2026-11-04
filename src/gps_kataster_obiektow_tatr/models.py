"""Structural contract for catalog YAML records.

Validation leaves cross-record relationships, coordinates and selection policy
to the catalog validator. Callers retain the original YAML mapping as source.
"""

from __future__ import annotations

from sys import float_info
from typing import Annotated, Literal

from jsonschema import FormatChecker
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidatorFunctionWrapHandler,
    WithJsonSchema,
    WrapValidator,
    field_validator,
)
from pydantic_core import PydanticCustomError

_FORMATS = FormatChecker(formats=("date", "date-time", "uri"))


def _date(value: str) -> str:
    if not _FORMATS.conforms(value, "date"):
        raise ValueError("Expected an RFC 3339 calendar date")
    return value


def _date_time(value: str) -> str:
    if not _FORMATS.conforms(value, "date-time"):
        raise ValueError("Expected an RFC 3339 timestamp with a timezone")
    return value


def _uri(value: str) -> str:
    if not _FORMATS.conforms(value, "uri"):
        raise ValueError("Expected an absolute URI")
    return value


def _version_one(value: object, _handler: ValidatorFunctionWrapHandler) -> int | float:
    # JSON Schema's numeric const accepts both 1 and 1.0, but excludes true.
    if type(value) in (int, float) and value == 1:
        return value
    raise PydanticCustomError("schema_version", "Expected schema_version 1")


def _finite_number(value: object, handler: ValidatorFunctionWrapHandler) -> int | float:
    if type(value) not in (int, float):
        raise PydanticCustomError("float_type", "Expected a number")
    # Check before Pydantic converts integers to float. This also rejects NaN.
    if not -float_info.max <= value <= float_info.max:
        raise PydanticCustomError("finite_number", "Expected a finite number in float range")
    handler(value)
    return value


def _unique_items[T: (str, BaseModel)](items: list[T]) -> list[T]:
    seen = set()
    for item in items:
        # Sorted properties ignore source key order. Keeping explicitly supplied
        # null fields distinguishes them from omissions, as JSON Schema does.
        if isinstance(item, BaseModel):
            key = tuple(sorted(item.model_dump(exclude_unset=True).items()))
        else:
            key = item
        if key in seen:
            raise ValueError("List items must be unique")
        seen.add(key)
    return items


type NonEmptyString = Annotated[str, Field(min_length=1)]
type ObjectId = Annotated[str, Field(pattern=r"^[A-Z]{2,3}-[0-9]{4,}$")]
type CaveId = Annotated[str, Field(pattern=r"^C-[0-9]{4,}$")]
type RelationId = Annotated[str, Field(pattern=r"^R-[0-9]{4,}$")]
type MeasurementId = Annotated[str, Field(pattern=r"^m-[0-9]{3,}$")]
type AttachmentId = Annotated[str, Field(pattern=r"^a-[0-9]{3,}$")]
type Prefix = Annotated[str, Field(pattern=r"^[A-Z]{2,3}$")]

# RFC helpers use regex end anchors that can accept a trailing newline.
# Use an absolute end in both the model and the published schemas.
_LITERAL_FORMAT_PATTERN = r"^\S+(?![\s\S])"

type DateString = Annotated[str, Field(json_schema_extra={"format": "date"}), AfterValidator(_date)]
type TimestampString = Annotated[
    str,
    Field(pattern=_LITERAL_FORMAT_PATTERN, json_schema_extra={"format": "date-time"}),
    AfterValidator(_date_time),
]
type UriString = Annotated[
    str,
    Field(pattern=_LITERAL_FORMAT_PATTERN, json_schema_extra={"format": "uri"}),
    AfterValidator(_uri),
]

type SchemaVersion = Annotated[
    int | float, WrapValidator(_version_one), WithJsonSchema({"const": 1})
]
type FiniteNumber = Annotated[
    float, Field(ge=-float_info.max, le=float_info.max), WrapValidator(_finite_number)
]
type NonNegativeNumber = Annotated[
    float, Field(ge=0, le=float_info.max), WrapValidator(_finite_number)
]
type Latitude = Annotated[float, Field(ge=-90, le=90), WrapValidator(_finite_number)]
type Longitude = Annotated[float, Field(ge=-180, le=180), WrapValidator(_finite_number)]

type UniqueList[T: (str, BaseModel)] = Annotated[
    list[T], AfterValidator(_unique_items), Field(json_schema_extra={"uniqueItems": True})
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, regex_engine="python-re")

    @field_validator("*")
    @classmethod
    def exportable_text(cls, value):
        """XML 1.0 exports cannot represent NUL, surrogates or forbidden controls.

        Reject rather than silently strip source text. Nested models apply this
        validator themselves; lists of strings (tags, object IDs) need this pass.
        """
        for item in value if isinstance(value, list) else (value,):
            if not isinstance(item, str):
                continue
            if any(
                not (
                    char in "\t\n\r"
                    or " " <= char <= "\ud7ff"
                    or "\ue000" <= char <= "\ufffd"
                    or "\U00010000" <= char <= "\U0010ffff"
                )
                for char in item
            ):
                raise ValueError("Text contains characters not representable in XML 1.0 exports")
        return value


class CreatedRecord(ContractModel):
    created_at: TimestampString
    created_by: NonEmptyString


class UpdatedRecord(ContractModel):
    updated_at: TimestampString
    updated_by: NonEmptyString


class ExternalReference(ContractModel):
    system: Literal["TPN", "PIG", "geoportal", "NR_INWENT", "inne"]
    ref_type: Literal[
        "source_globalid", "inventory_number", "catalog_id", "url", "source_row", "other"
    ]
    external_id: NonEmptyString
    url: UriString | None = None
    scope: Literal["object", "cave", "cave_system", "inventory_entry", "unknown"] | None = None
    notes: str | None = None


class Attachment(CreatedRecord):
    id: AttachmentId
    kind: Literal["raport_gnss", "zdjecie", "inne"]
    path: NonEmptyString
    measurement_id: MeasurementId | None = None
    caption: str | None = None
    date: DateString | None = None


class Measurement(CreatedRecord):
    id: MeasurementId
    lat: Latitude
    lon: Longitude
    x_1992: FiniteNumber
    y_1992: FiniteNumber
    elevation_m: FiniteNumber | None = None
    elevation_datum: (
        Literal["unknown", "ellipsoidal", "PL-EVRF2007-NH", "Kronstadt86", "other"] | None
    ) = None
    elevation_source: (
        Literal["gps", "gnss", "map", "dem", "barometric", "source_record", "unknown", "other"]
        | None
    ) = None
    horizontal_accuracy_m: NonNegativeNumber | None = None
    vertical_accuracy_m: NonNegativeNumber | None = None
    source: Literal["TPN", "PIG", "geoportal", "wlasne", "publikacja", "inne"]
    source_ref: str | None = None
    observed_at: TimestampString | None = None
    observed_date: DateString
    source_date: DateString | None = None
    method: Literal[
        "gps_receiver",
        "gnss",
        "smartfon",
        "mapa_topo",
        "source_record",
        "siec_pomiarowa",
        "ustalenie",
        "inne",
    ]
    device: str | None = None
    tags: UniqueList[NonEmptyString] = Field(default_factory=list)
    verification_status: Literal["nieweryfikowany", "zweryfikowany", "odrzucony"]
    verified_by: NonEmptyString | None = None
    verified_at: TimestampString | None = None
    notes: str | None = None


class BestMeasurementFields(UpdatedRecord):
    measurement_id: MeasurementId


class AutoBestMeasurement(BestMeasurementFields):
    mode: Literal["auto"]
    reason: str | None = None


class ManualBestMeasurement(BestMeasurementFields):
    mode: Literal["manual"]
    reason: NonEmptyString


type BestMeasurement = Annotated[
    AutoBestMeasurement | ManualBestMeasurement, Field(discriminator="mode")
]


class IdAssignmentFields(ContractModel):
    assigned_from_measurement_id: MeasurementId
    assigned_prefix: Prefix


class AutoIdAssignment(IdAssignmentFields):
    method: Literal["auto"]
    prefix_override_reason: str | None = None


class ManualIdAssignment(IdAssignmentFields):
    method: Literal["manual"]
    prefix_override_reason: NonEmptyString


type IdAssignment = Annotated[AutoIdAssignment | ManualIdAssignment, Field(discriminator="method")]


class ObjectRecord(CreatedRecord, UpdatedRecord):
    model_config = ConfigDict(title="Obiekt")

    schema_version: SchemaVersion
    id: ObjectId
    category: Literal["jaskinia_otwor", "ponor", "wywierzysko", "sztolnia", "inne"]
    name_local: str | None = None
    cave_id: CaveId | None = None
    id_assignment: IdAssignment
    external_refs: UniqueList[ExternalReference]
    measurements: Annotated[list[Measurement], Field(min_length=1)]
    best_measurement: BestMeasurement
    attachments: UniqueList[Attachment]
    notes: str | None = None


class CaveRecord(CreatedRecord, UpdatedRecord):
    model_config = ConfigDict(title="Jaskinia")

    schema_version: SchemaVersion
    id: CaveId
    name: NonEmptyString
    system_name: str | None = None
    external_refs: UniqueList[ExternalReference]
    object_ids: UniqueList[ObjectId]
    notes: str | None = None


class RelationRecord(ContractModel):
    model_config = ConfigDict(title="Relacja")

    schema_version: SchemaVersion
    id: RelationId
    from_object_id: ObjectId
    to_object_id: ObjectId
    relation_type: Literal["sasiad", "czesc_systemu", "mozliwy_duplikat", "inne"]
    notes: str | None = None


RECORD_MODELS: dict[str, type[ContractModel]] = {
    "object": ObjectRecord,
    "cave": CaveRecord,
    "relation": RelationRecord,
}
