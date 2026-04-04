# =============================================================================
# common/db_handler.py
# UDS Simulator — Database Handler
# =============================================================================
# Fichier hada kaydir 2 hajat:
#   1. Ychargi w ykhzen DID database (did_database.json)
#   2. Ychargi w ykhzen Users database (users.json)
#      + authenticate_user() — ycheck username/password → yrd role
# =============================================================================

import os
from utils import load_json, save_json, resource_path, did_str_to_int
from common.uds_constants import (
    ROLE_ADMIN, ROLE_TECHNICIAN, ROLE_READER,
    ROLE_PERMISSIONS
)


class DatabaseHandler:

    # -------------------------------------------------------------------------
    # Constructor — waqtash ndiro DatabaseHandler() kaychargi les 2 fichiers
    # -------------------------------------------------------------------------
    def __init__(
        self,
        did_db_path : str = "DIDs/did_database.json",
        users_path  : str = "DIDs/users.json"
    ):
        self.did_db_path = did_db_path
        self.users_path  = users_path

        self.did_db = {}   # DID database — dict f memory (dynamique)
        self.users  = {}   # Users database — dict f memory

        self._load_databases()

    # -------------------------------------------------------------------------
    # _load_databases — private method — kaychargi les 2 JSONs
    # -------------------------------------------------------------------------
    def _load_databases(self):
        self.did_db = load_json(self.did_db_path)
        # 1. Chargi DID database
        self.did_db = load_json(self.did_db_path)

        if not self.did_db:
            print(f"[WARN] DID database malqahaxh: {self.did_db_path}")

        # 2. Chargi users — ila malqahaxh, dir default users
        self.users = load_json(self.users_path)

        if not self.users:
            print("[INFO] users.json malqahaxh — kayban default users")
            self.users = self._default_users()
            self._save_users()

    # -------------------------------------------------------------------------
    # _default_users — kayrd default users ila users.json malqahaxh
    # -------------------------------------------------------------------------
    def _default_users(self) -> dict:
        return {
            "admin": {
                "password" : "admin123",
                "role"     : ROLE_ADMIN
            },
            "technician": {
                "password" : "tech456",
                "role"     : ROLE_TECHNICIAN
            },
            "reader": {
                "password" : "read789",
                "role"     : ROLE_READER
            }
        }

    # -------------------------------------------------------------------------
    # _save_users — sauvegarde users dict → users.json
    # -------------------------------------------------------------------------
    def _save_users(self):
        save_json(self.users_path, self.users)

    # =========================================================================
    # AUTH
    # =========================================================================

    def authenticate_user(self, username: str, password: str):
        """
        Ycheck username + password.

        - Ila sah  → yrd role dyalo (ROLE_ADMIN / ROLE_TECHNICIAN / ROLE_READER)
        - Ila ghalat → yrd None

        Exemple:
            role = db.authenticate_user("admin", "admin123")
            # → "admin"

            role = db.authenticate_user("admin", "wrong")
            # → None
        """
        user = self.users.get(username)

        if user is None:
            return None   # Username malqahaxh

        if user["password"] != password:
            return None   # Password ghalat

        return user["role"]

    # =========================================================================
    # DID — READ
    # =========================================================================

    def get_did_info(self, did: int) -> dict:
        """
        Yrd kol info dial DID wahd (name, value, type, roles...).

        - did    : int — ex: 0xF40D
        - return : dict mn did_database.json
                   Ila DID malqahaxh → yrd dict b "Unknown DID"

        Exemple:
            info = db.get_did_info(0xF40D)
            # → {"name": "Vehicle Speed", "value": 50, "unit": "km/h", ...}
        """
        # JSON keys = strings "0xF40D" — lazm nconvertiw int → string
        key = f"0x{did:04X}"
        return self.did_db.get(key, {
            "name"     : f"Unknown DID {key}",
            "readable" : False,
            "writable" : False,
            "value"    : None,
            "unit"     : "",
            "type"     : "uint8",
            "roles"    : []
        })

    def get_did_value(self, did: int):
        """
        Yrd valeur actuelle dial DID (mn memory — dynamique).

        - did    : int — ex: 0xF40D
        - return : valeur (int wla string) wla None ila malqahaxh
        """
        info = self.get_did_info(did)
        return info.get("value")

    def get_all_dids(self) -> list[dict]:
        """
        Yrd liste d kol DIDs disponibles — pour affichage f GUI.

        Return: liste d dicts, kol dict fih:
            {"did_int": 0xF40D, "did_str": "0xF40D", "name": "Vehicle Speed", ...}
        """
        result = []
        for key, info in self.did_db.items():
            if key.startswith("_"):      # skip _comment keys
                continue
            try:
                did_int = int(key, 16)
                result.append({
                    "did_int" : did_int,
                    "did_str" : key,
                    **info       # yzid kol fields (name, value, type...)
                })
            except ValueError:
                continue
        return result

    # =========================================================================
    # DID — WRITE
    # =========================================================================

    def set_did_value(self, did: int, new_value) -> bool:
        """
        Ybddel valeur dial DID f memory (mashi f JSON — runtime ghir).

        - did       : int — ex: 0xF40D
        - new_value : valeur jdida
        - return    : True ila tbddel / False ila DID malqahaxh

        Note: ila bghiti tsauvgardi → appel save_did_database()
        """
        key = f"0x{did:04X}"
        if key not in self.did_db:
            return False

        self.did_db[key]["value"] = new_value
        return True

    def save_did_database(self):
        """
        Sauvegarde état actuel dial DID database → did_database.json.
        Kaytsamma ghir ila bghiti tpersisti changes (sinon RAM ghir).
        """
        save_json(self.did_db_path, self.did_db)

    # =========================================================================
    # ACCESS CONTROL — check permissions
    # =========================================================================

    def can_read_did(self, did: int, role: str) -> tuple[bool, str]:
        """
        Ycheck wash had role yqdr yqra had DID.

        - return : (True, "") ila msmoh
                   (False, "raison") ila mashi msmoh

        Exemple:
            ok, reason = db.can_read_did(0xF190, ROLE_READER)
            # → (False, "Role 'reader' mashi f roles dial had DID")
        """
        info = self.get_did_info(did)

        # 1. DID readable?
        if not info.get("readable", False):
            return False, f"DID 0x{did:04X} mashi readable"

        # 2. Role permission global
        if not ROLE_PERMISSIONS.get(role, {}).get("can_read", False):
            return False, f"Role '{role}' mashi 3ndu can_read permission"

        # 3. DID-specific roles
        allowed_roles = info.get("roles", [])
        if allowed_roles and role not in allowed_roles:
            return False, f"Role '{role}' mashi f roles dial had DID"

        return True, ""

    def can_change_session(self, role: str) -> tuple[bool, str]:
        """Ycheck wash role yqdr ybddel session."""
        if ROLE_PERMISSIONS.get(role, {}).get("can_change_session", False):
            return True, ""
        return False, f"Role '{role}' mashi msmoh ybddel session"

    def can_reset_ecu(self, role: str) -> tuple[bool, str]:
        """Ycheck wash role yqdr yreset ECU."""
        if ROLE_PERMISSIONS.get(role, {}).get("can_reset", False):
            return True, ""
        return False, f"Role '{role}' mashi msmoh yreset ECU"