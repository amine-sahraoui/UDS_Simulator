# =============================================================================
# common/db_handler.py
# UDS Simulator — Database Handler
# =============================================================================
# This module handles two data stores:
#   1. DID database (did_database.json)
#   2. Users database (users.json)
#      + authenticate_user() validates username/password and returns role
# =============================================================================

import os

from common.type_defs import (
    DIDInfo,
    DIDInfoWithId,
    DIDValue,
    UserRecord,
)
from common.uds_constants import (
    ROLE_ADMIN,
    ROLE_PERMISSIONS_MAP,
    ROLE_READER,
    ROLE_TECHNICIAN,
)
from utils import did_str_to_int, load_json, resource_path, save_json


class DatabaseHandler:
    """Handles DID and user databases."""

    # -------------------------------------------------------------------------
    # Constructor: load both JSON databases.
    # -------------------------------------------------------------------------
    def __init__(
        self,
        did_db_path: str = "DIDs/did_database.json",
        users_path: str = "DIDs/users.json",
    ) -> None:
        self.did_db_path = did_db_path
        self.users_path = users_path

        self.did_db: dict[str, DIDInfo] = {}  # DID database — dict in memory (dynamic)
        self.users: dict[str, UserRecord] = {}  # Users database — dict in memory

        self._load_databases()

    # -------------------------------------------------------------------------
    # _load_databases: private helper that loads both JSON files.
    # -------------------------------------------------------------------------
    def _load_databases(self) -> None:
        # 1. Load DID database
        self.did_db = load_json(self.did_db_path)

        if not self.did_db:
            print(f"[WARN] DID database not found: {self.did_db_path}")

        # 2. Load users. If missing, create defaults and save users.json.
        self.users = load_json(self.users_path)

        if not self.users:
            print("[INFO] users.json not found - loading default users")
            self.users = self._default_users()
            self._save_users()

    # -------------------------------------------------------------------------
    # _default_users: return default users when users.json is missing.
    # -------------------------------------------------------------------------
    def _default_users(self) -> dict[str, UserRecord]:
        return {
            "admin": {"password": "admin123", "role": ROLE_ADMIN},
            "technician": {"password": "tech456", "role": ROLE_TECHNICIAN},
            "reader": {"password": "read789", "role": ROLE_READER},
        }

    # -------------------------------------------------------------------------
    # _save_users: persist users dictionary to users.json.
    # -------------------------------------------------------------------------
    def _save_users(self) -> None:
        save_json(self.users_path, self.users)

    # =========================================================================
    # AUTH
    # =========================================================================

    def authenticate_user(self, username: str, password: str) -> str | None:
        """Validate username and password.

        - If valid: return role (ROLE_ADMIN / ROLE_TECHNICIAN / ROLE_READER)
        - If invalid: return None

        Example:
            role = db.authenticate_user("admin", "admin123")
            # → "admin"

            role = db.authenticate_user("admin", "wrong")
            # → None

        """
        user: UserRecord | None = self.users.get(username)

        if user is None:
            return None  # Username not found.

        if user["password"] != password:
            return None  # Wrong password.

        return user["role"]

    # =========================================================================
    # DID — READ
    # =========================================================================

    def get_did_info(self, did: int) -> DIDInfo:
        """Return complete info for one DID (name, value, type, roles...).

        - did    : int — e.g. 0xF40D
        - return : dict from did_database.json
                   If DID is missing, return a default "Unknown DID" dict.

        Example:
            info = db.get_did_info(0xF40D)
            # → {"name": "Vehicle Speed", "value": 50, "unit": "km/h", ...}

        """
        # JSON keys are strings like "0xF40D", so convert int → string.
        key = f"0x{did:04X}"
        return self.did_db.get(
            key,
            {
                "name": f"Unknown DID {key}",
                "readable": False,
                "writable": False,
                "value": None,
                "unit": "",
                "type": "uint8",
                "roles": [],
            },
        )

    def get_did_value(self, did: int) -> DIDValue:
        """Return current DID value from in-memory runtime data.

        - did    : int — e.g. 0xF40D
        - return : value (int or string) or None if not found
        """
        info = self.get_did_info(did)
        return info.get("value")

    def get_all_dids(self) -> list[DIDInfoWithId]:
        """Return list of all available DIDs for GUI display.

        Return: list of dicts. Each dict includes:
            {"did_int": 0xF40D, "did_str": "0xF40D", "name": "Vehicle Speed", ...}
        """
        result: list[DIDInfoWithId] = []
        for key, info in self.did_db.items():
            if key.startswith("_"):  # skip _comment keys
                continue
            try:
                did_int = int(key, 16)
                result.append(
                    {
                        "did_int": did_int,
                        "did_str": key,
                        **info,  # Include all DID fields (name, value, type, ...)
                    },
                )
            except ValueError:
                continue
        return result

    # =========================================================================
    # DID — WRITE
    # =========================================================================

    def set_did_value(self, did: int, new_value: DIDValue) -> bool:
        """Update DID value in memory (not persisted to JSON by default).

        - did       : int — e.g. 0xF40D
        - new_value : new value
        - return    : True if updated, False if DID does not exist

        Note: call save_did_database() to persist changes.
        """
        key = f"0x{did:04X}"
        if key not in self.did_db:
            return False

        self.did_db[key]["value"] = new_value
        return True

    def save_did_database(self) -> None:
        """Save current DID database state to did_database.json."""
        save_json(self.did_db_path, self.did_db)

    # =========================================================================
    # ACCESS CONTROL — check permissions
    # =========================================================================

    def can_read_did(self, did: int, role: str) -> tuple[bool, str]:
        """Check whether a role can read the given DID.

        - return : (True, "") if allowed
                   (False, "reason") if denied

        Example:
            ok, reason = db.can_read_did(0xF190, ROLE_READER)
            # → (False, "Role 'reader' is not allowed for this DID")

        """
        info = self.get_did_info(did)

        # 1. DID readable?
        if not info.get("readable", False):
            return False, f"DID 0x{did:04X} is not readable"

        # 2. Role permission global
        role_permissions = ROLE_PERMISSIONS_MAP.get(role, None)
        if role_permissions is None:
            return False, f"Role '{role}' is not recognized in the system"

        permission = role_permissions.get("can_read", False)
        if not permission:
            return False, f"Role '{role}' does not have can_read permission"

        # 3. DID-specific roles
        allowed_roles = info.get("roles", [])
        if allowed_roles and role not in allowed_roles:
            return False, f"Role '{role}' is not in the allowed roles for this DID"

        return True, ""

    def can_change_session(self, role: str) -> tuple[bool, str]:
        """Check whether role can change session."""
        role_permissions = ROLE_PERMISSIONS_MAP.get(role, None)
        if role_permissions is None:
            return False, f"Role '{role}' is not recognized in the system"

        permission = role_permissions.get("can_change_session", False)
        if permission:
            return True, ""
        return False, f"Role '{role}' is not allowed to change session"

    def can_reset_ecu(self, role: str) -> tuple[bool, str]:
        """Check whether role can reset ECU."""
        role_permissions = ROLE_PERMISSIONS_MAP.get(role, None)
        if role_permissions is None:
            return False, f"Role '{role}' is not recognized in the system"

        permission = role_permissions.get("can_reset", False)
        if permission:
            return True, ""
        return False, f"Role '{role}' is not allowed to reset ECU"
