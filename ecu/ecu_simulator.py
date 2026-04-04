# =============================================================================
# ecu/ecu_simulator.py
# UDS Simulator — ECU Side
# =============================================================================
# Fichier hada huwa "ECU" f simulator dyalna.
# Kaysmk 3la UDS requests, kayprocessiw, w kayrd responses.
#
# Services supported:
#   0x10 — DiagnosticSessionControl
#   0x11 — ECUReset
#   0x22 — ReadDataByIdentifier
#   0x2E — WriteDataByIdentifier
#   0x27 _ Security access
# =============================================================================

from common.uds_constants import (
    # Addresses
    ECU_ADDR, CLIENT_ADDR,
    # SIDs
    SID_DIAGNOSTIC_SESSION_CONTROL,
    SID_ECU_RESET,
    SID_READ_DATA_BY_IDENTIFIER,
    POSITIVE_RESPONSE_OFFSET,
    NEGATIVE_RESPONSE_SID,
    SID_SECURITY_ACCESS,
    # Sessions
    SESSION_DEFAULT, SESSION_EXTENDED, SESSION_PROGRAMMING,
    SESSION_NAMES, SESSION_SERVICE_MATRIX,
    # Resets
    RESET_HARD, RESET_KEY_OFF, RESET_SOFT,
    # NRC codes
    NRC_GENERAL_REJECT,
    NRC_SERVICE_NOT_SUPPORTED,             
    NRC_SUBFUNCTION_NOT_SUPPORTED,         
    NRC_INCORRECT_MESSAGE_LENGTH, 
    NRC_REQUEST_SEQUENCE_ERROR,
    NRC_INVALID_KEY,                          
    NRC_REQUEST_OUT_OF_RANGE,                  
    NRC_SECURITY_ACCESS_DENIED,                                
    NRC_SERVICE_NOT_SUPPORTED_IN_SESSION,  
    NRC_CONDITIONS_NOT_CORRECT,
    NRC_REQUEST_TOO_LONG,
    NRC_EXCEEDED_NUMBER_OF_ATTEMPTS,
    # DID constants
    DID_ACTIVE_SESSION,
    DID_VEHICLE_SPEED,
)
from common.db_handler import DatabaseHandler
from utils import (
    build_uds_frame,
    parse_uds_frame,
    encode_value,
    decode_value,
    build_uds_log_entry,
)


class ECUSimulator:

    # -------------------------------------------------------------------------
    # Constructor
    # -------------------------------------------------------------------------
    def __init__(self, db: DatabaseHandler, role: str):
        """
        - db   : DatabaseHandler — kaystawdih l DID access w permissions
        - role : str             — role dial user connected (ROLE_ADMIN, ...)
        """
        self.db              = db
        self.role            = role
        self.current_session = SESSION_DEFAULT   # ECU ybda f Default session
        self._failed_key_attempts = 0
        self._max_key_attempts    = 3
        self._key_off_allowed = False
        self.engine_running = bool(self.db.get_did_value(DID_VEHICLE_SPEED))
        # Callback — GUI tconnectiw bih bach tchargi log entries
        # tstawdih hakda: ecu.on_frame_logged = my_gui_function
        self.on_frame_logged = None

    # =========================================================================
    # PUBLIC — process_request
    # =========================================================================

    def process_request(self, request_frame: list[int]) -> list[int]:
        """
        Entry point dial ECU — kayakhod request frame w kayrd response frame.

        - request_frame : list[int] — 8 bytes (UDS frame complet)
        - return        : list[int] — 8 bytes (response frame)

        Flow:
            1. Parse frame → payload
            2. Extract SID
            3. Check wash service msmoh f current session
            4. Dispatch l handler dyalo
            5. Rd response frame
        """
        # -- Parse
        try:
            payload = parse_uds_frame(request_frame)
        except ValueError:
            return self._negative_response(0x00, NRC_INCORRECT_MESSAGE_LENGTH)

        if not payload:
            return self._negative_response(0x00, NRC_INCORRECT_MESSAGE_LENGTH)

        sid = payload[0]

        # -- SID valid check → NRC_GENERAL_REJECT
        VALID_SIDS = [0x10, 0x11, 0x22, 0x27, 0x2E, 0x31, 0x36, 0x3E]
        if sid not in VALID_SIDS:
            response = self._negative_response(sid, NRC_GENERAL_REJECT)
            self._log(ECU_ADDR, response, "ECU")
            return response

        # -- Check session permissions
        allowed = SESSION_SERVICE_MATRIX.get(self.current_session, {}).get("allowed_services", [])
        if sid not in allowed:
            response = self._negative_response(sid, NRC_SERVICE_NOT_SUPPORTED_IN_SESSION)
            self._log(ECU_ADDR, response, "ECU")
            return response

        # -- Dispatch
        if sid == SID_DIAGNOSTIC_SESSION_CONTROL:
            response = self._handle_dsc(payload)

        elif sid == SID_ECU_RESET:
            response = self._handle_reset(payload)

        elif sid == SID_READ_DATA_BY_IDENTIFIER:
            response = self._handle_read_did(payload)

        elif sid == SID_SECURITY_ACCESS:
            response = self._handle_security_access(payload)

        else:
            response = self._negative_response(sid, NRC_SERVICE_NOT_SUPPORTED)

        # -- Log response
        self._log(ECU_ADDR, response, "ECU")
        return response

    # =========================================================================
    # SERVICE HANDLERS
    # =========================================================================

    # -------------------------------------------------------------------------
    # 0x10 — DiagnosticSessionControl
    # -------------------------------------------------------------------------
    # Request  : [0x10, sub_function]
    # Response : [0x50, sub_function, 0x00, 0x19, 0x01, 0xF4]
    #             ^^^^                ^^^^^^^^^^^^^^^^^^^^^^^^^
    #             SID+0x40            P2 timing bytes (standard values)
    # -------------------------------------------------------------------------
    def _handle_dsc(self, payload: list[int]) -> list[int]:

        # ===============================
        # 1. Length check FIRST
        # ===============================
        if len(payload) < 2:
            return self._negative_response(
                SID_DIAGNOSTIC_SESSION_CONTROL,
                NRC_INCORRECT_MESSAGE_LENGTH
            )

        # ===============================
        # 2. Extract sub_function
        # ===============================
        sub_function = payload[1]

        # ===============================
        # 3. Sub-function validation
        # ===============================
        if sub_function not in [SESSION_DEFAULT, SESSION_EXTENDED, SESSION_PROGRAMMING]:
            return self._negative_response(
                SID_DIAGNOSTIC_SESSION_CONTROL,
                NRC_SUBFUNCTION_NOT_SUPPORTED
            )
        # ===============================
        # 4. CONDITIONS (Programming only)
        # ===============================
        if sub_function == SESSION_PROGRAMMING:
            if self.is_engine_running():
                return self._negative_response(
                    SID_DIAGNOSTIC_SESSION_CONTROL,
                    NRC_CONDITIONS_NOT_CORRECT
                )
        # ===============================
        # 5. Security check
        # ===============================
        if sub_function == SESSION_EXTENDED:
            if not getattr(self, '_security_unlocked', False):
                return self._negative_response(
                    SID_DIAGNOSTIC_SESSION_CONTROL,
                    NRC_SECURITY_ACCESS_DENIED
                )

        # ===============================
        # 6. Role check
        # ===============================
        ok, _ = self.db.can_change_session(self.role)
        if not ok:
            return self._negative_response(
                SID_DIAGNOSTIC_SESSION_CONTROL,
                NRC_SECURITY_ACCESS_DENIED
            )

        # ===============================
        # 7. Apply session
        # ===============================
        self.current_session = sub_function
        self.db.set_did_value(DID_ACTIVE_SESSION, sub_function)

        # ===============================
        # 8. Positive response
        # ===============================
        response_payload = [
            SID_DIAGNOSTIC_SESSION_CONTROL + POSITIVE_RESPONSE_OFFSET,
            sub_function,
            0x00, 0x14,
            0x00, 0xC8
        ]

        return build_uds_frame(response_payload)

    # -------------------------------------------------------------------------
    # 0x11 — ECUReset
    # -------------------------------------------------------------------------
    # Request  : [0x11, reset_type]
    # Response : [0x51, reset_type]
    # -------------------------------------------------------------------------
    def _handle_reset(self, payload: list[int]) -> list[int]:
        if len(payload) < 2:
            return self._negative_response(SID_ECU_RESET,
                                           NRC_INCORRECT_MESSAGE_LENGTH)

        reset_type = payload[1]

        # Reset type valid?
        if reset_type not in [RESET_SOFT, RESET_HARD]:
            return self._negative_response(SID_ECU_RESET,
                                           NRC_SUBFUNCTION_NOT_SUPPORTED)
        if reset_type in [RESET_KEY_OFF, RESET_HARD]:
            if not getattr(self, '_security_unlocked', False):
                return self._negative_response(
                    SID_ECU_RESET,
                    NRC_SECURITY_ACCESS_DENIED
            )
        # Role check
        ok, reason = self.db.can_reset_ecu(self.role)
        if not ok:
            return self._negative_response(SID_ECU_RESET,
                                           NRC_SECURITY_ACCESS_DENIED)

        # Reset — ECU yrj3 l Default session
        self.current_session = SESSION_DEFAULT
        self.db.set_did_value(DID_ACTIVE_SESSION, SESSION_DEFAULT)

        
        self._failed_key_attempts = 0
        self._security_unlocked   = False  # ← lock again
        self._seed                = None   # ← clear seed

        response_payload = [
            SID_ECU_RESET + POSITIVE_RESPONSE_OFFSET,
            reset_type
        ]
        return build_uds_frame(response_payload)

    # -------------------------------------------------------------------------
    # 0x22 — ReadDataByIdentifier
    # -------------------------------------------------------------------------
    # Request  : [0x22, DID_H, DID_L]
    # Response : [0x62, DID_H, DID_L, <value bytes>]
    # -------------------------------------------------------------------------
    def _handle_read_did(self, payload: list[int]) -> list[int]:

        length = len(payload)  # includes SID byte

        # -------------------------------
        # 0. Length check
        # -------------------------------
        if length < 3:
            return self._negative_response(
                SID_READ_DATA_BY_IDENTIFIER,
                NRC_INCORRECT_MESSAGE_LENGTH
            )

        if length > 3:
            did_bytes = length - 1
            if did_bytes % 2 == 0:
                return self._negative_response(
                    SID_READ_DATA_BY_IDENTIFIER,
                    NRC_REQUEST_TOO_LONG
                )
            else:
                return self._negative_response(
                    SID_READ_DATA_BY_IDENTIFIER,
                    NRC_INCORRECT_MESSAGE_LENGTH
                )

        # -------------------------------
        # 1. Extract DID
        # -------------------------------
        did = (payload[1] << 8) | payload[2]

        # -------------------------------
        # 2. Security check ONLY for VIN (0xF190)
        # -------------------------------
        if did == 0xF18C:
            if not getattr(self, "_security_unlocked", False):
                return self._negative_response(
                    SID_READ_DATA_BY_IDENTIFIER,
                    NRC_SECURITY_ACCESS_DENIED
                )

        # -------------------------------
        # 3. DID exists?
        # -------------------------------
        did_info = self.db.get_did_info(did)
        if did_info["value"] is None:
            return self._negative_response(
                SID_READ_DATA_BY_IDENTIFIER,
                NRC_REQUEST_OUT_OF_RANGE
            )

        # -------------------------------
        # 4. Access check (roles)
        # -------------------------------
        ok, _ = self.db.can_read_did(did, self.role)
        if not ok:
            return self._negative_response(
                SID_READ_DATA_BY_IDENTIFIER,
                NRC_SECURITY_ACCESS_DENIED
            )

        # -------------------------------
        # 5. VIN condition (speed = 0)
        # -------------------------------
        if did == 0xF190:
            speed = self.db.get_did_value(0xF40D)
            if speed != 0:
                return self._negative_response(
                    SID_READ_DATA_BY_IDENTIFIER,
                    NRC_CONDITIONS_NOT_CORRECT
                )

        # -------------------------------
        # 6. Encode value
        # -------------------------------
        value_bytes = encode_value(did_info["value"], did_info["type"])

        response_payload = [
            SID_READ_DATA_BY_IDENTIFIER + POSITIVE_RESPONSE_OFFSET,
            (did >> 8) & 0xFF,
            did & 0xFF,
            *value_bytes
        ]

        # -------------------------------
        # 7. Single Frame limit
        # -------------------------------
        if len(response_payload) > 7:
            return self._negative_response(
                SID_READ_DATA_BY_IDENTIFIER,
                NRC_REQUEST_TOO_LONG
            )

        return build_uds_frame(response_payload)
    # -------------------------------------------------------------------------
    # 0x27 — SecurityAccess
    # -------------------------------------------------------------------------
    # Request seed : [0x27, 0x01]
    # Response seed: [0x67, 0x01, seed_H, seed_L]
    # Request key  : [0x27, 0x02, key_H, key_L]
    # Response key : [0x67, 0x02]
    # -------------------------------------------------------------------------
    def _handle_security_access(self, payload: list[int]) -> list[int]:
 
        if len(payload) < 2:
            return self._negative_response(SID_SECURITY_ACCESS,
                                        NRC_SUBFUNCTION_NOT_SUPPORTED)
        sub = payload[1]

        if sub not in [0x01, 0x02]:
            return self._negative_response(SID_SECURITY_ACCESS,
                                        NRC_SUBFUNCTION_NOT_SUPPORTED)

        # -- 0x01 — Seed request
        if sub == 0x01:
            # must be exactly [0x27, 0x01] — no extra bytes
            if len(payload) != 2:
                return self._negative_response(SID_SECURITY_ACCESS,
                                            NRC_SUBFUNCTION_NOT_SUPPORTED)
            self._seed = [0x12, 0x34]
            response_payload = [
                SID_SECURITY_ACCESS + POSITIVE_RESPONSE_OFFSET,
                0x01,
                *self._seed
            ]
            return build_uds_frame(response_payload)

        # -- 0x02 — Key send
        elif sub == 0x02:
            # Check seed requested first
            if not hasattr(self, '_seed') or self._seed is None:
                return self._negative_response(SID_SECURITY_ACCESS,
                                            NRC_REQUEST_SEQUENCE_ERROR)

            # Check if locked out
            if self._failed_key_attempts >= self._max_key_attempts:
                return self._negative_response(SID_SECURITY_ACCESS,
                                            NRC_EXCEEDED_NUMBER_OF_ATTEMPTS)

            # Any payload for 0x02 that isn't exactly 4 bytes → invalid key
            if len(payload) != 4:
                self._failed_key_attempts += 1
                if self._failed_key_attempts >= self._max_key_attempts:
                    self._seed = None
                    return self._negative_response(SID_SECURITY_ACCESS,
                                                NRC_EXCEEDED_NUMBER_OF_ATTEMPTS)
                return self._negative_response(SID_SECURITY_ACCESS,
                                            NRC_INVALID_KEY)

            # Check key
            received_key = [payload[2], payload[3]]
            expected_key = [b ^ 0xFF for b in self._seed]

            if received_key != expected_key:
                self._failed_key_attempts += 1
                if self._failed_key_attempts >= self._max_key_attempts:
                    self._seed = None
                    return self._negative_response(SID_SECURITY_ACCESS,
                                                NRC_EXCEEDED_NUMBER_OF_ATTEMPTS)
                return self._negative_response(SID_SECURITY_ACCESS,
                                            NRC_INVALID_KEY)

            # Correct key
            self._failed_key_attempts = 0
            self._security_unlocked   = True
            self._seed                = None

            response_payload = [
                SID_SECURITY_ACCESS + POSITIVE_RESPONSE_OFFSET,
                0x02
            ]
            return build_uds_frame(response_payload)
    # =========================================================================
    # HELPERS
    # =========================================================================

    def _negative_response(self, sid: int, nrc: int) -> list[int]:
        """
        Bni Negative Response frame.
        Format: [0x7F, SID, NRC, padding...]

        Ex: [0x7F, 0x22, 0x31, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA]
        """
        payload = [NEGATIVE_RESPONSE_SID, sid, nrc]
        return build_uds_frame(payload)

    def _log(self, addr: int, frame: list[int], sender: str):
        """
        Ysift log entry l GUI via callback.
        Ila GUI mashi connectée — ma kaydirch walo.
        """
        if self.on_frame_logged:
            entry = build_uds_log_entry(addr, frame, sender)
            self.on_frame_logged(entry)

    # =========================================================================
    # GETTERS
    # =========================================================================

    def get_current_session(self) -> int:
        """Yrd current session (SESSION_DEFAULT, SESSION_EXTENDED, SESSION_PROGRAMMING)."""
        return self.current_session

    def get_session_name(self) -> str:
        """Yrd current session name — pour affichage f GUI."""
        return SESSION_NAMES.get(self.current_session, "Unknown Session")

    def is_engine_running(self) -> bool:
        """Yrd wach engine khdama awla stopped."""
        return self.engine_running

    def is_security_unlocked(self) -> bool:
        """Yrd wach security access unlocked awla locked."""
        return getattr(self, '_security_unlocked', False)

    def start_engine(self) -> bool:
        """Start engine by updating vehicle speed and RPM state."""
        if self.engine_running:
            return False
        self.engine_running = True
        self.db.set_did_value(DID_VEHICLE_SPEED, 20)
        self.db.set_did_value(0xF406, 1500)
        return True

    def stop_engine(self) -> bool:
        """Stop engine by setting vehicle speed and RPM to zero."""
        if not self.engine_running:
            return False
        self.engine_running = False
        self.db.set_did_value(DID_VEHICLE_SPEED, 0)
        self.db.set_did_value(0xF406, 0)
        return True

    def toggle_engine(self) -> bool:
        """Toggle engine status and return new running state."""
        if self.engine_running:
            self.stop_engine()
        else:
            self.start_engine()
        return self.engine_running

    def set_role(self, role: str):
        """Ybddel role — waqtash user ybddel account."""
        self.role = role