"""Type definitions for UDS simulator."""

from typing import NotRequired, TypedDict

# Structured records loaded from DIDs/users.json.
type DIDValue = int | str | None


class UserRecord(TypedDict):
    """User record info."""

    password: str
    role: str


class DIDInfo(TypedDict):
    """DID info."""

    name: str
    readable: bool
    writable: bool
    value: DIDValue
    unit: str
    type: str
    roles: list[str]
    description: NotRequired[str]


class DIDInfoWithId(DIDInfo):
    """DID info with integer and string identifiers."""

    did_int: int
    did_str: str


# UDS trace log entry used by GUI table rendering.
class UDSLogByte(TypedDict):
    """Structured byte info for GUI display."""

    value: str
    color: str


class UDSLogEntry(TypedDict):
    """Structured log entry for GUI display."""

    time: str
    addr: str
    sender: str
    frame_type: str
    bytes: list[UDSLogByte]
    protocol: str
    service: str


# Generic client result that can carry service-specific fields.
class UDSClientResult(TypedDict):
    """Generic client result that can carry service-specific fields."""

    success: bool
    sid: int
    payload: list[int]
    nrc: int | None
    nrc_name: str | None
    session_name: NotRequired[str]
    reset_name: NotRequired[str]
    did: NotRequired[int]
    did_name: NotRequired[str]
    raw_bytes: NotRequired[list[int]]
    unit: NotRequired[str]
    value: NotRequired[int | str | list[int] | None]


class SessionConfig(TypedDict):
    """Configuration for a diagnostic session."""

    allowed_services: list[int]
    description: str


class RolePermissions(TypedDict):
    """Permissions for a user role."""

    can_read: bool
    can_reset: bool
    can_change_session: bool
    can_security_access: bool
