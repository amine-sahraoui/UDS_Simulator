# =============================================================================
# common/uds_constants.py
# UDS Simulator — Constants & Definitions (ISO 14229-1)
# =============================================================================
# This file is the central dictionary for the simulator.
# It defines services, sessions, error codes, and shared constants
# imported by other modules.
# =============================================================================


# -----------------------------------------------------------------------------
# 1. UDS data
# -----------------------------------------------------------------------------
# In classic CAN, data payload is 8 bytes.
# Client (tester) sends from address 0x7E0.
# ECU responds from address 0x7E8.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Client key example: [0xED, 0xCB]
# Computed with: ECU key XOR 0xFFFF
# Example: 0x1234 XOR 0xFFFF = 0xEDCB
#
# -----------------------------------------------------------------------------

CLIENT_ADDR = 0x7E0  # Tester → ECU  (request)
ECU_ADDR = 0x7E8  # ECU → Tester  (response)

UDS_FRAME_SIZE = 8  # CAN frame size is always 8 bytes (ISO 11898)
UDS_PADDING_BYTE = 0xAA  # Padding byte to fill frame to 8 bytes
UDS_MAX_PAYLOAD = 7  # Max UDS payload bytes in single frame (8 - 1 PCI byte)


# -----------------------------------------------------------------------------
# 2. UDS Service Identifiers (SID) — 1 byte
# -----------------------------------------------------------------------------
# SID is the first byte in UDS payload (after PCI).
# Each service has its own SID.
# Response SID = SID + 0x40 (e.g. 0x10 request -> 0x50 response)
# -----------------------------------------------------------------------------

SID_DIAGNOSTIC_SESSION_CONTROL = (
    0x10  # Change session (Default / Extended / Programming)
)
SID_ECU_RESET = 0x11  # Reset ECU
SID_SECURITY_ACCESS = 0x27  # Unlock ECU (seed/key mechanism)
SID_READ_DATA_BY_IDENTIFIER = 0x22  # Read DID (e.g. vehicle speed)

# Positive response offset added to request SID so that the ECU returns a positive response.
POSITIVE_RESPONSE_OFFSET = 0x40
# Example: request SID 0x22 → response SID 0x62 (0x22 + 0x40)


# -----------------------------------------------------------------------------
# 3. Diagnostic Sessions — Sub-function byte for 0x10
# -----------------------------------------------------------------------------
# In a DSC request, second byte selects session type.
# Each session has different access rights.
# -----------------------------------------------------------------------------

SESSION_DEFAULT = 0x01  # Initial session - not all services enabled
SESSION_PROGRAMMING = 0x02  # Flash/update firmware - requires special conditions
SESSION_EXTENDED = 0x03  # Full diagnostics - more services enabled


# -----------------------------------------------------------------------------
# 4. ECU Reset Types — Sub-function byte for 0x11
# -----------------------------------------------------------------------------

RESET_HARD = 0x01  # Hard reset
RESET_KEY_OFF = 0x02  # Key off/on reset
RESET_SOFT = 0x03  # Soft reset (software reset)

# -----------------------------------------------------------------------------
# 5. Security Access — Sub-function byte for 0x27
# -----------------------------------------------------------------------------

REQUEST_SEED = 0x01  # Request Seed — first security step
SEND_KEY = 0x02  # Send Key — second security step

# -----------------------------------------------------------------------------
# 6. Negative Response Codes (NRC) — ISO 14229-1 Table A.1
# -----------------------------------------------------------------------------
# If ECU cannot process request, it returns a Negative Response.
# Format: [0x7F, SID_li_fshel, NRC_code]
# Example: [0x7F, 0x22, 0x31] = ReadDID failed (requestOutOfRange)
# -----------------------------------------------------------------------------

NRC_GENERAL_REJECT = 0x10  # General reject
NRC_SERVICE_NOT_SUPPORTED = 0x11  # Service not supported
NRC_SUBFUNCTION_NOT_SUPPORTED = 0x12  # Sub-function not supported
NRC_INCORRECT_MESSAGE_LENGTH = 0x13  # Incorrect message length
NRC_CONDITIONS_NOT_CORRECT = 0x22  # Conditions not correct
NRC_REQUEST_OUT_OF_RANGE = 0x31  # DID out of range/unknown
NRC_SECURITY_ACCESS_DENIED = 0x33  # Security access denied
NRC_INVALID_KEY = 0x35  # Invalid security key
NRC_SERVICE_NOT_SUPPORTED_IN_SESSION = 0x7F  # Service not available in session
NRC_REQUEST_SEQUENCE_ERROR = 0x24  # Key sent before seed
NRC_REQUEST_TOO_LONG = 0x14  # Request too long (e.g. multiple DIDs)
NRC_EXCEEDED_NUMBER_OF_ATTEMPTS = 0x36  # Too many wrong keys


NEGATIVE_RESPONSE_SID = 0x7F  # First byte of all negative responses


# -----------------------------------------------------------------------------
# 7. Read / Write Data — Sub-functions & helpers
# -----------------------------------------------------------------------------
# SID 0x22 (ReadDataByIdentifier) and 0x2E (WriteDataByIdentifier)
# do not use a sub-function byte like DSC.
# Payload format: [SID, DID_high, DID_low, (data bytes for write)]
#
# Examples:
#   Read  request:  [0x22, 0xF4, 0x0D]              → read DID 0xF40D
#   Read  response: [0x62, 0xF4, 0x0D, <value>]     → 0x62 = 0x22 + 0x40
#   Write request:  [0x2E, 0xF1, 0x90, <data...>]   → write DID 0xF190
#   Write response: [0x6E, 0xF1, 0x90]              → 0x6E = 0x2E + 0x40
# -----------------------------------------------------------------------------

# Minimum payload lengths
READ_DID_REQUEST_MIN_LEN = 3  # [0x22, DID_H, DID_L]
# DID range limits (2 bytes: 0x0000 to 0xFFFF)
DID_MIN = 0x0000
DID_MAX = 0xFFFF

# Standard ISO DIDs used in this simulator
DID_VEHICLE_SPEED = 0xF40D  # Vehicle Speed (km/h)
DID_ENGINE_TEMP = 0xF405  # Engine Coolant Temperature (°C)
DID_VIN = 0xF190  # Vehicle Identification Number (17 chars)
DID_ECU_SERIAL = 0xF18C  # ECU Serial Number
DID_ACTIVE_SESSION = 0xF186  # Active Diagnostic Session (read-only)


# -----------------------------------------------------------------------------
# 8. User Roles (RBAC — Role Based Access Control)
# -----------------------------------------------------------------------------
# Each user has a role that defines allowed services.
# Example: READER can read DIDs but cannot write.
# -----------------------------------------------------------------------------

ROLE_ADMIN = "admin"  # Full access: read + write + sessions + reset
ROLE_TECHNICIAN = "technician"  # Read + write + sessions, no security access
ROLE_READER = "reader"  # Read-only DID access


# -----------------------------------------------------------------------------
# 9. Session Access Matrix
# -----------------------------------------------------------------------------
# Matrix that defines allowed services per session.
# -----------------------------------------------------------------------------

SESSION_SERVICE_MATRIX = {
    SESSION_DEFAULT: {
        "allowed_services": [
            SID_DIAGNOSTIC_SESSION_CONTROL,
            SID_SECURITY_ACCESS,
            SID_READ_DATA_BY_IDENTIFIER,
            SID_ECU_RESET,
        ],
        "description": "Default Session — baseline services",
    },
    SESSION_EXTENDED: {
        "allowed_services": [
            SID_DIAGNOSTIC_SESSION_CONTROL,
            SID_ECU_RESET,
            SID_READ_DATA_BY_IDENTIFIER,
            SID_SECURITY_ACCESS,
        ],
        "description": "Extended Session — more services enabled",
    },
    SESSION_PROGRAMMING: {
        "allowed_services": [
            SID_DIAGNOSTIC_SESSION_CONTROL,
            SID_ECU_RESET,
            SID_READ_DATA_BY_IDENTIFIER,
            SID_SECURITY_ACCESS,
        ],
        "description": "Programming Session — programming and security focused",
    },
}


# -----------------------------------------------------------------------------
# 10. Role Service Permissions
# -----------------------------------------------------------------------------
# Role check is applied after session check.
# Admin has full access, technician can write, reader is read-only.
# -----------------------------------------------------------------------------

ROLE_PERMISSIONS = {
    ROLE_ADMIN: {
        "can_read": True,
        "can_reset": True,
        "can_change_session": True,
        "can_security_access": True,
    },
    ROLE_TECHNICIAN: {
        "can_read": True,
        "can_reset": True,
        "can_change_session": True,
        "can_security_access": False,
    },
    ROLE_READER: {
        "can_read": True,
        "can_reset": False,
        "can_change_session": False,
        "can_security_access": False,
    },
}


# -----------------------------------------------------------------------------
# 11. Human-readable name maps for GUI display
# -----------------------------------------------------------------------------

SESSION_NAMES = {
    SESSION_DEFAULT: "Default Session (0x01)",
    SESSION_PROGRAMMING: "Programming Session (0x02)",
    SESSION_EXTENDED: "Extended Session (0x03)",
}

RESET_NAMES = {
    RESET_HARD: "Hard Reset (0x01)",
    RESET_KEY_OFF: "Key Off/On Reset (0x02)",
    RESET_SOFT: "Soft Reset (0x03)",
}

SEC_NAMES = {
    REQUEST_SEED: "Request Seed (0x01)",
    SEND_KEY: "Send Key (0x02)",
}

NRC_NAMES = {
    NRC_GENERAL_REJECT: "generalReject",
    NRC_SERVICE_NOT_SUPPORTED: "serviceNotSupported",
    NRC_SUBFUNCTION_NOT_SUPPORTED: "subFunctionNotSupported",
    NRC_INCORRECT_MESSAGE_LENGTH: "incorrectMessageLength",
    NRC_CONDITIONS_NOT_CORRECT: "conditionsNotCorrect",
    NRC_REQUEST_OUT_OF_RANGE: "requestOutOfRange",
    NRC_SECURITY_ACCESS_DENIED: "securityAccessDenied",
    NRC_INVALID_KEY: "invalidKey",
    NRC_SERVICE_NOT_SUPPORTED_IN_SESSION: "serviceNotSupportedInActiveSession",
    NRC_REQUEST_SEQUENCE_ERROR: "requestSequenceError",
    NRC_INVALID_KEY: "invalidKey",
    NRC_REQUEST_TOO_LONG: "requestTooLong",
    NRC_EXCEEDED_NUMBER_OF_ATTEMPTS: "exceededNumberOfAttempts",
}
