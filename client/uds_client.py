# =============================================================================
# client/uds_client.py
# UDS Simulator — Client Side (Tester)
# =============================================================================
# Fichier hada huwa "tester" f simulator dyalna.
# Kaybni UDS requests w kaysiftime l ECU — direct call (mashi CAN HW).
#
# Services supported:
#   0x10 — DiagnosticSessionControl
#   0x11 — ECUReset
#   0x22 — ReadDataByIdentifier
#   0x2E — WriteDataByIdentifier
# =============================================================================

from common.uds_constants import (
    # Addresses
    CLIENT_ADDR, ECU_ADDR,
    # SIDs
    SID_DIAGNOSTIC_SESSION_CONTROL,
    SID_ECU_RESET,
    SID_READ_DATA_BY_IDENTIFIER,
    NEGATIVE_RESPONSE_SID,
    # Sessions
    SESSION_NAMES,
    # Resets
    RESET_HARD, RESET_NAMES,
    # Security Access
    SEC_NAMES,
    # NRC
    NRC_NAMES,
)
from utils import (
    build_uds_frame,
    parse_uds_frame,
    build_uds_log_entry,
)


class UDSClient:

    # -------------------------------------------------------------------------
    # Constructor
    # -------------------------------------------------------------------------
    def __init__(self, ecu):
        """
        - ecu : ECUSimulator — direct reference, kaysiftime requests bla CAN HW
        """
        self.ecu = ecu

        # Callback — GUI tconnectiw bih bach tchargi log entries
        self.on_frame_logged = None

    # =========================================================================
    # PRIVATE — _send
    # =========================================================================

    def _send(self, payload: list[int]) -> dict:
        """
        Kaybni UDS frame mn payload, kaysiftime l ECU, kayrd parsed response.

        - payload : list[int] — UDS bytes bla PCI (ex: [0x10, 0x03])
        - return  : dict b response info:
            {
                "success"  : bool,
                "sid"      : int,       # response SID
                "payload"  : list[int], # response payload complet
                "nrc"      : int|None,  # NRC code ila negative response
                "nrc_name" : str|None,  # NRC name lisible
            }

        Flow:
            1. build_uds_frame(payload) → request frame 8 bytes
            2. Log request frame
            3. ecu.process_request(frame) → response frame
            4. parse_uds_frame(response) → response payload
            5. Rd dict b result
        """
        # 1. Bni request frame
        request_frame = build_uds_frame(payload)

        # 2. Log request
        self._log(CLIENT_ADDR, request_frame, "Client(DiagBox)")

        # 3. Sift l ECU — direct call
        response_frame = self.ecu.process_request(request_frame)

        # 4. Parse response
        try:
            response_payload = parse_uds_frame(response_frame)
        except ValueError:
            return {
                "success"  : False,
                "sid"      : 0x00,
                "payload"  : [],
                "nrc"      : None,
                "nrc_name" : "Invalid response frame"
            }

        if not response_payload:
            return {
                "success"  : False,
                "sid"      : 0x00,
                "payload"  : [],
                "nrc"      : None,
                "nrc_name" : "Empty response"
            }

        response_sid = response_payload[0]

        # 5. Negative response? [0x7F, SID, NRC]
        if response_sid == NEGATIVE_RESPONSE_SID:
            nrc      = response_payload[2] if len(response_payload) >= 3 else 0x00
            nrc_name = NRC_NAMES.get(nrc, f"Unknown NRC 0x{nrc:02X}")
            return {
                "success"  : False,
                "sid"      : response_sid,
                "payload"  : response_payload,
                "nrc"      : nrc,
                "nrc_name" : nrc_name
            }

        # Positive response
        return {
            "success"  : True,
            "sid"      : response_sid,
            "payload"  : response_payload,
            "nrc"      : None,
            "nrc_name" : None
        }

    # =========================================================================
    # PUBLIC SERVICE METHODS
    # =========================================================================

    # -------------------------------------------------------------------------
    # 0x10 — DiagnosticSessionControl
    # -------------------------------------------------------------------------
    def change_session(self, session: int) -> dict:
        """
        Ybddel UDS session.

        - session : int — SESSION_DEFAULT / SESSION_EXTENDED / SESSION_PROGRAMMING
        - return  : dict b result (success, session_name, nrc...)

        Request payload  : [0x10, session]
        Response payload : [0x50, session, P2_H, P2_L, P2Ex_H, P2Ex_L]

        Exemple:
            result = client.change_session(SESSION_EXTENDED)
            # result["success"] → True
            # result["session_name"] → "Extended Session (0x03)"
        """
        payload = [SID_DIAGNOSTIC_SESSION_CONTROL, session]
        result  = self._send(payload)

        if result["success"]:
            result["session_name"] = SESSION_NAMES.get(session, f"Unknown 0x{session:02X}")

        return result

    # -------------------------------------------------------------------------
    # 0x11 — ECUReset
    # -------------------------------------------------------------------------
    def reset_ecu(self, reset_type: int = RESET_HARD) -> dict:
        """
        Yreset ECU.

        - reset_type : int — RESET_HARD / RESET_KEY_OFF / RESET_SOFT
        - return     : dict b result

        Request payload  : [0x11, reset_type]
        Response payload : [0x51, reset_type]

        Exemple:
            result = client.reset_ecu(RESET_SOFT)
            # result["success"] → True
            # result["reset_name"] → "Soft Reset (0x03)"
        """
        payload = [SID_ECU_RESET, reset_type]
        result  = self._send(payload)

        if result["success"]:
            result["reset_name"] = RESET_NAMES.get(reset_type, f"Unknown 0x{reset_type:02X}")

        return result

    # -------------------------------------------------------------------------
    # 0x22 — ReadDataByIdentifier
    # -------------------------------------------------------------------------
    def read_did(self, did: int) -> dict:
        """
        Yqra valeur dial DID wahd.

        - did    : int — ex: 0xF40D
        - return : dict b result + value

        Request payload  : [0x22, DID_H, DID_L]
        Response payload : [0x62, DID_H, DID_L, <value bytes>]

        Exemple:
            result = client.read_did(0xF40D)
            # result["success"]    → True
            # result["did"]        → 0xF40D
            # result["did_name"]   → "Vehicle Speed"
            # result["raw_bytes"]  → [0x32]
            # result["value"]      → 50  (decoded)
            # result["unit"]       → "km/h"
        """
        did_h   = (did >> 8) & 0xFF
        did_l   =  did       & 0xFF
        payload = [SID_READ_DATA_BY_IDENTIFIER, did_h, did_l]
        result  = self._send(payload)

        if result["success"]:
            resp        = result["payload"]   # [0x62, DID_H, DID_L, value...]
            raw_bytes   = resp[3:] if len(resp) > 3 else []
            did_info    = self.ecu.db.get_did_info(did)

            result["did"]       = did
            result["did_name"]  = did_info.get("name", f"DID 0x{did:04X}")
            result["raw_bytes"] = raw_bytes
            result["unit"]      = did_info.get("unit", "")

            # Decode value
            try:
                result["value"] = self._decode_did_value(raw_bytes, did_info.get("type", "uint8"))
            except Exception:
                result["value"] = raw_bytes   # rd raw ila decode fshel

        return result

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _decode_did_value(self, raw_bytes: list[int], value_type: str):
        """
        Decode raw bytes → Python value selon type.
        Proxy l decode_value() dial utils.
        """
        from utils import decode_value
        return decode_value(raw_bytes, value_type)

    def send_raw(self, payload: list[int]) -> dict:
        from utils import build_uds_frame, build_uds_log_entry
        frame = build_uds_frame(payload)
        
        if self.on_frame_logged:
            entry = build_uds_log_entry(CLIENT_ADDR, frame, "Client(DiagBox)")
            self.on_frame_logged(entry) 
        
        response_frame = self.ecu.process_request(frame)
        return {"success": False, "payload": response_frame}
    
    def _log(self, addr: int, frame: list[int], sender: str):
        """
        Ysift log entry l GUI via callback.
        Ila GUI mashi connectée — ma kaydirch walo.
        """
        if self.on_frame_logged:
            entry = build_uds_log_entry(addr, frame, sender)
            self.on_frame_logged(entry)