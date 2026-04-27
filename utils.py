# =============================================================================
# utils.py
# UDS Simulator — Utility / Helper Functions
# =============================================================================
# This file contains shared helper functions.
# It does not implement UDS business logic directly, but is used by ECU, client, and GUI.
# =============================================================================

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from common.type_defs import UDSLogByte, UDSLogEntry


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# -----------------------------------------------------------------------------
# 1. resource_path — PyInstaller compatibility
# -----------------------------------------------------------------------------
# When the application is packaged with PyInstaller (binary/.exe),
# bundled files (JSON, images, etc.) are available in the temporary "_MEIPASS" folder.
# resource_path() returns the correct path in both development and packaged modes.
# -----------------------------------------------------------------------------


def resource_path(relative_path: str) -> str:
    """Return an absolute path compatible with both PyInstaller and development mode.

    Development mode: resolve relative to this script directory.
    Packaged mode: resolve relative to PyInstaller's temporary _MEIPASS folder.
    """
    if hasattr(sys, "_MEIPASS"):
        # Packaged mode: files are extracted in a temporary folder.
        base_path = Path(sys._MEIPASS)
    else:
        # Development mode: files live next to the project code.
        base_path = Path().cwd()

    return str(base_path / relative_path)


# -----------------------------------------------------------------------------
# 2. build_uds_frame — Build full UDS frame (8 bytes)
# -----------------------------------------------------------------------------
# At this layer, each message is exactly 8 bytes.
# The UDS payload starts after the PCI byte.
# Remaining bytes are padded with UDS_PADDING_BYTE (0xAA).
#
# Example:
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
    """Build complete 8-byte UDS frame from payload.

    - payload : list of bytes (UDS payload without PCI)
    - returns : list of 8 bytes (PCI + payload + padding)

    Rules:
    - Single Frame only (max 7 bytes payload)
    - If payload > 7 → ValueError
    """
    if len(payload) > UDS_FRAME_SIZE - 1:
        # Too long for single frame → should trigger NRC upstream
        raise ValueError(
            f"Payload too long for Single Frame: {len(payload)} bytes (max 7).",
        )

    # PCI byte: High nibble = 0 (SF), Low nibble = payload length
    pci_byte = len(payload) & 0x0F

    # Frame = PCI + payload + padding
    frame = [pci_byte, *payload]
    frame += [UDS_PADDING_BYTE] * (UDS_FRAME_SIZE - len(frame))

    return frame


# -------------------------------------------------------------------------
# 2. parse_uds_frame — Extract payload from UDS frame
# -------------------------------------------------------------------------
def parse_uds_frame(frame: list[int]) -> list[int]:
    """Parse UDS frame → extract payload (no PCI, no padding).

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
    payload_len = pci_byte & 0x0F  # Low nibble = payload length

    if frame_type != 0x0:
        raise ValueError(f"Only Single Frame supported. PCI type=0x{frame_type:X}")

    # Extract real payload (ignore padding)
    payload = frame[1 : 1 + payload_len]

    # Extra check: payload length cannot exceed 7
    if payload_len > UDS_FRAME_SIZE - 1:
        raise ValueError(
            f"Invalid payload length {payload_len}, exceeds Single Frame limit",
        )

    return payload


# -----------------------------------------------------------------------------
# 5. did_str_to_int — Convert DID string → int
# -----------------------------------------------------------------------------
# JSON keys are strings ("0xF40D").
# Convert them to integers so they can be compared with bytes from UDS frames.
# -----------------------------------------------------------------------------


def did_str_to_int(did_str: str) -> int:
    """Convert DID string → int.

    "0xF40D" → 0xF40D (= 62477)
    "F40D"   → 0xF40D  (with or without 0x prefix)
    """
    return int(did_str, 16)


def did_int_to_str(did_int: int) -> str:
    """Convert DID int → formatted string.

    0xF40D → "0xF40D"
    """
    return f"0x{did_int:04X}"


# -----------------------------------------------------------------------------
# 6. encode_value / decode_value — Convert value ↔ bytes
# -----------------------------------------------------------------------------
# Each DID has a type in JSON (uint8, uint16, uint32, string).
# encode_value: Python value → list of bytes (for UDS transmission)
# decode_value: list of bytes → Python value (after reception)
# -----------------------------------------------------------------------------


def encode_value(value: int | str, value_type: str) -> list[int]:
    """Convert Python value → list of bytes for a UDS frame.

    Supported types:
    - uint8   : 1 byte  (e.g. 50  → [0x32])
    - uint16  : 2 bytes (e.g. 3000 → [0x0B, 0xB8], big-endian)
    - uint32  : 4 bytes (e.g. 123456 → [0x00, 0x01, 0xE2, 0x40])
    - string  : ASCII bytes (e.g. "ABC" → [0x41, 0x42, 0x43])
    """
    if value_type == "uint8":
        return [int(value) & 0xFF]

    if value_type == "uint16":
        v = int(value) & 0xFFFF
        return [(v >> 8) & 0xFF, v & 0xFF]  # big-endian

    if value_type == "uint32":
        v = int(value) & 0xFFFFFFFF
        return [(v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF]

    if value_type == "string":
        return list(str(value).encode("ascii"))

    raise ValueError(f"Unknown value type: {value_type}")


def decode_value(raw_bytes: list[int], value_type: str) -> int | str:
    """Convert list of bytes → Python value.

    Inverse of encode_value.
    """
    if value_type == "uint8":
        return raw_bytes[0]

    if value_type == "uint16":
        return (raw_bytes[0] << 8) | raw_bytes[1]

    if value_type == "uint32":
        return (
            (raw_bytes[0] << 24)
            | (raw_bytes[1] << 16)
            | (raw_bytes[2] << 8)
            | raw_bytes[3]
        )

    if value_type == "string":
        return bytes(raw_bytes).decode("ascii", errors="replace")

    raise ValueError(f"Unknown value type: {value_type}")


# -----------------------------------------------------------------------------
# 7. load_json / save_json — JSON file helpers
# -----------------------------------------------------------------------------


def load_json(path: str) -> dict[str, Any]:
    """Load a JSON file and return a dictionary. Return {} if file is missing."""
    full_path = resource_path(path)
    if Path(full_path).exists():
        with Path(full_path).open(encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: str, data: dict[str, Any]) -> None:
    """Save dictionary to a JSON file (indent=2 for readability)."""
    full_path = resource_path(path)
    Path(full_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(full_path).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -----------------------------------------------------------------------------
# 4. build_uds_log_entry — Format UDS frame -> structured dict for GUI log
# -----------------------------------------------------------------------------
# Returns a dictionary with full frame details for GUI rendering.
#
# Colors:
#   PCI field       → #FF4444  (red)
#   SID request     → #4488FF  (blue)
#   UDS DID         → #44CCCC  (cyan)
#   SID response    → #44AAFF  (light blue)
#   Payload/value   → #44FF88  (green)
#   Padding/unused  → #888888  (gray)
#   Addr            → #FF8800  (orange)
# -----------------------------------------------------------------------------

# Colors imported directly by the GUI.
UDS_COLORS = {
    "pci": "#FF4444",
    "sid_request": "#4488FF",
    "did": "#44CCCC",
    "sid_response": "#44AAFF",
    "payload": "#1FB155",
    "padding": "#888888",
    "addr": "#FF8800",
}


def build_uds_log_entry(
    addr: int,
    frame: list[int],
    sender: str,
    frame_type: str = "Single Frame (SF)",
) -> UDSLogEntry:
    """Return a structured frame dictionary for GUI visualization.

    - addr       : int   (e.g. 0x7E0)
    - frame      : list  (8 bytes total: PCI + payload + padding)
    - sender     : str   ("Client" or "ECU")
    - frame_type : str   (default: "Single Frame (SF)")
    """
    import time

    from common.uds_constants import (
        NEGATIVE_RESPONSE_SID,
        NRC_NAMES,
        POSITIVE_RESPONSE_OFFSET,
        RESET_NAMES,
        SEC_NAMES,
        SESSION_NAMES,
        SID_DIAGNOSTIC_SESSION_CONTROL,
        SID_ECU_RESET,
        SID_READ_DATA_BY_IDENTIFIER,
        SID_SECURITY_ACCESS,
        UDS_FRAME_SIZE,
        UDS_PADDING_BYTE,
    )

    timestamp = f"{time.time() % 10:.3f}"

    colored_bytes: list[UDSLogByte] = []

    if len(frame) != UDS_FRAME_SIZE:
        colored_bytes.extend({"value": f"{b:02X}", "color": "#FF0000"} for b in frame)
        return {
            "time": timestamp,
            "addr": f"0x{addr:03X}",
            "sender": sender,
            "frame_type": "Invalid Frame",
            "bytes": colored_bytes,
            "protocol": "UDS",
            "service": "",
        }

    pci = frame[0]
    payload_len = pci & 0x0F
    colored_bytes.append({"value": f"{pci:02X}", "color": UDS_COLORS["pci"]})

    payload = frame[1 : 1 + payload_len]

    KNOWN_SIDS = [0x10, 0x11, 0x22, 0x27, 0x2E, 0x31, 0x36, 0x3E]
    DID_SIDS = [0x22, 0x2E]

    req_sid = 0
    if payload:
        sid = payload[0]
        req_sid = (
            sid - POSITIVE_RESPONSE_OFFSET
            if (
                sid >= POSITIVE_RESPONSE_OFFSET
                and sid != NEGATIVE_RESPONSE_SID
                and (sid - POSITIVE_RESPONSE_OFFSET) in KNOWN_SIDS
            )
            else sid
        )

    for i, b in enumerate(payload):
        if i == 0:
            if b == NEGATIVE_RESPONSE_SID or b >= POSITIVE_RESPONSE_OFFSET + 0x10:
                color = UDS_COLORS["sid_response"]
            else:
                color = UDS_COLORS["sid_request"]
            colored_bytes.append({"value": f"{b:02X}", "color": color})
        elif i in {1, 2}:
            color = UDS_COLORS["did"] if req_sid in DID_SIDS else UDS_COLORS["payload"]
            colored_bytes.append({"value": f"{b:02X}", "color": color})
        else:
            colored_bytes.append({"value": f"{b:02X}", "color": UDS_COLORS["payload"]})

    colored_bytes.extend(
        {"value": f"{b:02X}", "color": UDS_COLORS["padding"]}
        for b in frame[1 + payload_len :]
    )

    protocol = "UDS"
    service = ""

    if payload:
        sid_names = {
            SID_DIAGNOSTIC_SESSION_CONTROL: "DiagnosticSessionControl",
            SID_ECU_RESET: "ECUReset",
            SID_READ_DATA_BY_IDENTIFIER: "ReadDataByIdentifier",
            SID_SECURITY_ACCESS: "SecurityAccess",
            NEGATIVE_RESPONSE_SID: "NegativeResponse",
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
        "time": timestamp,
        "addr": f"0x{addr:03X}",
        "sender": sender,
        "frame_type": frame_type,
        "protocol": protocol,
        "service": service,
        "bytes": colored_bytes,
    }
