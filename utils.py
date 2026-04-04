# =============================================================================
# utils.py
# UDS Simulator — Utility / Helper Functions
# =============================================================================
# Fichier hada fih fonctions "transversales" — mashi UDS logic,
# walakin kaystakhdamhom ECU + Client + GUI kolhom.
# =============================================================================

import os
import sys
import json
from datetime import datetime

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# -----------------------------------------------------------------------------
# 1. resource_path — PyInstaller compatibility
# -----------------------------------------------------------------------------
# Waqtash tpackagi application b PyInstaller (→ .exe / binary),
# les fichiers (JSON, images...) kaytkono f dossier temporaire "_MEIPASS".
# resource_path() kayrd path sahi swa kant f dev mode wla packagé.
# -----------------------------------------------------------------------------

def resource_path(relative_path: str) -> str:
    """
    Rd absolute path — compatible avec PyInstaller w dev mode.

    Dev mode    : rd path relatif l dossier dial script
    Packagé     : rd path relatif l _MEIPASS (dossier temp dial PyInstaller)
    """
    if hasattr(sys, '_MEIPASS'):
        # Packagé — fichiers f dossier temp
        base_path = sys._MEIPASS
    else:
        # Dev mode — fichiers jnb script
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)


# -----------------------------------------------------------------------------
# 2. build_uds_frame — Construit UDS frame complet (8 bytes)
# -----------------------------------------------------------------------------
# F UDS layer, kol message = exactement 8 bytes.
# UDS payload kaydkhl men b3d PCI byte.
# Les bytes li fadlin kaytmlaw b UDS_PADDING_BYTE (0xAA).
#
# Exemple:
#   payload = [0x10, 0x03]   (DSC Extended Session)
#   → PCI byte = 0x02        (Single Frame, length=2)
#   → frame    = [02, 10, 03, AA, AA, AA, AA, AA]
# -----------------------------------------------------------------------------

from common.uds_constants import UDS_FRAME_SIZE, UDS_PADDING_BYTE

# =============================================================================
# utils.py — updated frame helpers
# =============================================================================
# -------------------------------------------------------------------------
# 1. build_uds_frame — Construct UDS frame from payload
# -------------------------------------------------------------------------
def build_uds_frame(payload: list[int]) -> list[int]:
    """
    Build complete 8-byte UDS frame from payload.

    - payload : list of bytes (UDS payload without PCI)
    - returns : list of 8 bytes (PCI + payload + padding)

    Rules:
    - Single Frame only (max 7 bytes payload)
    - If payload > 7 → ValueError
    """
    if len(payload) > UDS_FRAME_SIZE - 1:
        # Too long for single frame → should trigger NRC upstream
        raise ValueError(
            f"Payload too long for Single Frame: {len(payload)} bytes (max 7)."
        )

    # PCI byte: High nibble = 0 (SF), Low nibble = payload length
    pci_byte = len(payload) & 0x0F

    # Frame = PCI + payload + padding
    frame = [pci_byte] + payload
    frame += [UDS_PADDING_BYTE] * (UDS_FRAME_SIZE - len(frame))

    return frame


# -------------------------------------------------------------------------
# 2. parse_uds_frame — Extract payload from UDS frame
# -------------------------------------------------------------------------
def parse_uds_frame(frame: list[int]) -> list[int]:
    """
    Parse UDS frame → extract payload (no PCI, no padding)

    - frame : list of 8 bytes
    - returns : list of payload bytes

    Raises ValueError if:
    - frame length != 8
    - PCI type is not Single Frame (SF)
    """
    if len(frame) != UDS_FRAME_SIZE:
        raise ValueError(f"UDS frame must be 8 bytes (got {len(frame)})")

    pci_byte = frame[0]
    frame_type = (pci_byte & 0xF0) >> 4  # High nibble = frame type
    payload_len = pci_byte & 0x0F        # Low nibble = payload length

    if frame_type != 0x0:
        raise ValueError(
            f"Only Single Frame supported. PCI type=0x{frame_type:X}"
        )

    # Extract real payload (ignore padding)
    payload = frame[1 : 1 + payload_len]

    # Extra check: payload length cannot exceed 7
    if payload_len > UDS_FRAME_SIZE - 1:
        raise ValueError(
            f"Invalid payload length {payload_len}, exceeds Single Frame limit"
        )

    return payload

# -----------------------------------------------------------------------------
# 5. did_str_to_int — Convertit DID string → int
# -----------------------------------------------------------------------------
# JSON keys kaykuno strings ("0xF40D") — lazm nconvertihom l int
# bach nqadro nqaranohom m3 bytes li jiw mn UDS frame.
# -----------------------------------------------------------------------------

def did_str_to_int(did_str: str) -> int:
    """
    Convertit DID string → int.
    "0xF40D" → 0xF40D (= 62477)
    "F40D"   → 0xF40D  (b wla bla 0x prefix)
    """
    return int(did_str, 16)


def did_int_to_str(did_int: int) -> str:
    """
    Convertit DID int → string formatée.
    0xF40D → "0xF40D"
    """
    return f"0x{did_int:04X}"


# -----------------------------------------------------------------------------
# 6. encode_value / decode_value — Convertit valeur ↔ bytes
# -----------------------------------------------------------------------------
# Kol DID 3ndu "type" f JSON (uint8, uint16, uint32, string).
# encode_value : Python value → bytes list (l envoi f UDS frame)
# decode_value : bytes list → Python value (men b3d réception)
# -----------------------------------------------------------------------------

def encode_value(value, value_type: str) -> list[int]:
    """
    Convertit valeur Python → liste d bytes pour UDS frame.

    Types supportés:
    - uint8   : 1 byte  — ex: 50  → [0x32]
    - uint16  : 2 bytes — ex: 3000 → [0x0B, 0xB8]  (big-endian)
    - uint32  : 4 bytes — ex: 123456 → [0x00, 0x01, 0xE2, 0x40]
    - string  : ASCII bytes — ex: "ABC" → [0x41, 0x42, 0x43]
    """
    if value_type == "uint8":
        return [int(value) & 0xFF]

    elif value_type == "uint16":
        v = int(value) & 0xFFFF
        return [(v >> 8) & 0xFF, v & 0xFF]   # big-endian

    elif value_type == "uint32":
        v = int(value) & 0xFFFFFFFF
        return [
            (v >> 24) & 0xFF,
            (v >> 16) & 0xFF,
            (v >>  8) & 0xFF,
             v        & 0xFF
        ]

    elif value_type == "string":
        return list(str(value).encode("ascii"))

    else:
        raise ValueError(f"Type mashi ma3rof: {value_type}")


def decode_value(raw_bytes: list[int], value_type: str):
    """
    Convertit liste d bytes → valeur Python.

    Inverse d encode_value.
    """
    if value_type == "uint8":
        return raw_bytes[0]

    elif value_type == "uint16":
        return (raw_bytes[0] << 8) | raw_bytes[1]

    elif value_type == "uint32":
        return (
            (raw_bytes[0] << 24) |
            (raw_bytes[1] << 16) |
            (raw_bytes[2] <<  8) |
             raw_bytes[3]
        )

    elif value_type == "string":
        return bytes(raw_bytes).decode("ascii", errors="replace")

    else:
        raise ValueError(f"Type mashi ma3rof: {value_type}")


# -----------------------------------------------------------------------------
# 7. load_json / save_json — Helper l fichiers JSON
# -----------------------------------------------------------------------------

def load_json(path: str) -> dict:
    """Chargi JSON fichier w rd dict. Rd {} ila fichier mawjodch."""
    full_path = resource_path(path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(path: str, data: dict) -> None:
    """Sauvegarde dict → JSON fichier (indent=2 pour lisibilité)."""
    full_path = resource_path(path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -----------------------------------------------------------------------------
# 4. build_uds_log_entry — Format UDS frame → structured dict pour GUI log
# -----------------------------------------------------------------------------
# Kayrd dict b kol info dial frame — GUI takhdo w tban b couleurs bhal image.
#
# Colors (bhal image):
#   PCI field       → #FF4444  (rouge)
#   SID request     → #4488FF  (bleu)
#   UDS DID         → #44CCCC  (cyan)
#   SID response    → #44AAFF  (bleu clair)
#   Payload/value   → #44FF88  (vert)
#   Padding/unused  → #888888  (gris)
#   Addr            → #FF8800  (orange)
# -----------------------------------------------------------------------------

# Couleurs — importables par GUI directement
UDS_COLORS = {
    "pci"          : "#FF4444",
    "sid_request"  : "#4488FF",
    "did"          : "#44CCCC",
    "sid_response" : "#44AAFF",
    "payload"      : "#1FB155",
    "padding"      : "#888888",
    "addr"         : "#FF8800",
}

def build_uds_log_entry(
    addr       : int,
    frame      : list[int],
    sender     : str,
    frame_type : str = "Single Frame (SF)"
) -> dict:
    """
    Kayrd structured dict dial frame — GUI takhdo w tban b couleurs.

    - addr       : int   — ex: 0x7E0
    - frame      : list  — 8 bytes complets (PCI + payload + padding)
    - sender     : str   — "Client" wla "ECU"
    - frame_type : str   — "Single Frame (SF)" par défaut
    """
    from common.uds_constants import (
        UDS_FRAME_SIZE, UDS_PADDING_BYTE,
        POSITIVE_RESPONSE_OFFSET, NEGATIVE_RESPONSE_SID,
        SESSION_NAMES, RESET_NAMES,SEC_NAMES,
        SID_DIAGNOSTIC_SESSION_CONTROL, SID_ECU_RESET,
        SID_READ_DATA_BY_IDENTIFIER, SID_SECURITY_ACCESS,
        NRC_NAMES,
    )

    import time
    timestamp = f"{time.time() % 10:.3f}"

    colored_bytes = []

    if len(frame) != UDS_FRAME_SIZE:
        for b in frame:
            colored_bytes.append({"value": f"{b:02X}", "color": "#FF0000"})
        return {
            "time": timestamp, "addr": f"0x{addr:03X}",
            "sender": sender, "frame_type": "Invalid Frame",
            "bytes": colored_bytes, "protocol": "UDS", "service": ""
        }

    pci         = frame[0]
    payload_len = pci & 0x0F
    colored_bytes.append({"value": f"{pci:02X}", "color": UDS_COLORS["pci"]})

    payload = frame[1 : 1 + payload_len]

    KNOWN_SIDS = [0x10, 0x11, 0x22, 0x27, 0x2E, 0x31, 0x36, 0x3E]
    DID_SIDS   = [0x22, 0x2E]

    req_sid = 0
    if payload:
        sid = payload[0]
        req_sid = sid - POSITIVE_RESPONSE_OFFSET if (
            sid >= POSITIVE_RESPONSE_OFFSET
            and sid != NEGATIVE_RESPONSE_SID
            and (sid - POSITIVE_RESPONSE_OFFSET) in KNOWN_SIDS
        ) else sid

    for i, b in enumerate(payload):
        if i == 0:
            if b == NEGATIVE_RESPONSE_SID:
                color = UDS_COLORS["sid_response"]
            elif b >= POSITIVE_RESPONSE_OFFSET + 0x10:
                color = UDS_COLORS["sid_response"]
            else:
                color = UDS_COLORS["sid_request"]
            colored_bytes.append({"value": f"{b:02X}", "color": color})
        elif i == 1 or i == 2:
            color = UDS_COLORS["did"] if req_sid in DID_SIDS else UDS_COLORS["payload"]
            colored_bytes.append({"value": f"{b:02X}", "color": color})
        else:
            colored_bytes.append({"value": f"{b:02X}", "color": UDS_COLORS["payload"]})

    for b in frame[1 + payload_len:]:
        colored_bytes.append({"value": f"{b:02X}", "color": UDS_COLORS["padding"]})

    protocol = "UDS"
    service  = ""

    if payload:
        sid_names = {
            SID_DIAGNOSTIC_SESSION_CONTROL : "DiagnosticSessionControl",
            SID_ECU_RESET                  : "ECUReset",
            SID_READ_DATA_BY_IDENTIFIER    : "ReadDataByIdentifier",
            SID_SECURITY_ACCESS            : "SecurityAccess",
            NEGATIVE_RESPONSE_SID          : "NegativeResponse",
        }
        protocol = sid_names.get(req_sid, f"0x{req_sid:02X}")

        if len(payload) >= 2:
            sub = payload[1]
            if req_sid == SID_DIAGNOSTIC_SESSION_CONTROL:
                service = SESSION_NAMES.get(sub, f"0x{sub:02X}").split(" (")[0]
            elif req_sid == SID_ECU_RESET:
                service = RESET_NAMES.get(sub, f"0x{sub:02X}").split(" (")[0]
            elif req_sid == SID_SECURITY_ACCESS:
                service = SEC_NAMES.get(sub, f"0x{sub:02X}").split(" (")[0]
            elif req_sid == NEGATIVE_RESPONSE_SID and len(payload) >= 3:
                service = NRC_NAMES.get(payload[2], f"NRC 0x{payload[2]:02X}")
            elif req_sid == SID_READ_DATA_BY_IDENTIFIER:
                did = (payload[1] << 8) | payload[2] if len(payload) >= 3 else 0
                service = f"Sub 0x{did:04X}"
            elif req_sid == SID_SECURITY_ACCESS:
                service = f"Sub 0x{sub:02X}"

    return {
        "time"       : timestamp,
        "addr"       : f"0x{addr:03X}",
        "sender"     : sender,
        "frame_type" : frame_type,
        "protocol"   : protocol,
        "service"    : service,
        "bytes"      : colored_bytes
    }