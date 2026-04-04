# =============================================================================
# common/uds_constants.py
# UDS Simulator — Constants & Definitions (ISO 14229-1)
# =============================================================================
# Fichier hada huwa "dictionnaire" d kol simulator —
# kol service, kol session, kol error code — kolshi mdéfinit hna
# w les autres fichiers kayimportaw mno.
# =============================================================================


# -----------------------------------------------------------------------------
# 1. UDS data 
# -----------------------------------------------------------------------------
# F CAN Classic 3andna data 8bytes had 8b katqssem b UDS kiwali 3andha ma3na
# Client (tester dyalna) kaysift mn add 0x7E0
# ECU (simulator) kayrd mn add 0x7E8
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Key of clien  [0xED, 0xCB]
# key kit7ssab bhad algo Key dayal ECU XOR 0xFFFF
# hadi huya result 0x1234 XOR 0xFffF = 0xEDCB
# 
# -----------------------------------------------------------------------------

CLIENT_ADDR = 0x7E0  # Tester → ECU  (request)
ECU_ADDR    = 0x7E8  # ECU → Tester  (response)

UDS_FRAME_SIZE      = 8      # CAN frame dayma 8 bytes (ISO 11898)
UDS_PADDING_BYTE    = 0xAA   # Byte li kaytml CAN frame l 8 bytes (bhal image: AA AA AA AA)
UDS_MAX_PAYLOAD     = 7      # Max bytes d UDS payload f frame wahda (8 - 1 byte PCI)


# -----------------------------------------------------------------------------
# 2. UDS Service Identifiers (SID) — 1 byte
# -----------------------------------------------------------------------------
# SID = awel byte f UDS payload (men b3d PCI).
# Kol service 3ndu SID khas bih.
# Response SID = SID + 0x40  (ex: 0x10 request → 0x50 response)
# -----------------------------------------------------------------------------

SID_DIAGNOSTIC_SESSION_CONTROL  = 0x10  # Bddel session (Default / Extended / Programming)
SID_ECU_RESET                   = 0x11  # Reset ECU
SID_SECURITY_ACCESS             = 0x27  # Unlock ECU (seed/key mechanism)
SID_READ_DATA_BY_IDENTIFIER     = 0x22  # Qra DID (ex: vehicle speed)

# Positive response offset — kaytzad l SID bach ECU yrd b positive response
POSITIVE_RESPONSE_OFFSET = 0x40
# Ex: Request SID 0x22 → Response SID 0x62 (0x22 + 0x40)


# -----------------------------------------------------------------------------
# 3. Diagnostic Sessions — Sub-function byte dial 0x10
# -----------------------------------------------------------------------------
# Waqtash tdir request DSC, tzid byte thani = type dial session li bghitiha.
# Kol session 3ndha droits mkhtalfa.
# -----------------------------------------------------------------------------

SESSION_DEFAULT     = 0x01  # Session initiale — mashi kol services mftuhin
SESSION_PROGRAMMING = 0x02  # Flash/update firmware — khassha conditions spéciales
SESSION_EXTENDED    = 0x03  # Diagnostic complet — kthar services mftuhin


# -----------------------------------------------------------------------------
# 4. ECU Reset Types — Sub-function byte dial 0x11
# -----------------------------------------------------------------------------

RESET_HARD      = 0x01  # Hard reset — bhal tqtl courant
RESET_KEY_OFF   = 0x02  # Key off/on reset
RESET_SOFT      = 0x03  # Soft reset — software reset bla HW

# -----------------------------------------------------------------------------
# 5. Security Access — Sub-function byte dial 0x27
# -----------------------------------------------------------------------------

REQUEST_SEED = 0x01  # Request Seed — awel step f security access
SEND_KEY     = 0x02  # Send Key — tanya step f security access

# -----------------------------------------------------------------------------
# 6. Negative Response Codes (NRC) — ISO 14229-1 Table A.1
# -----------------------------------------------------------------------------
# Ila ECU mqdarch ykhdem request → yrj3 Negative Response.
# Format: [0x7F, SID_li_fshel, NRC_code]
# Ex:  [0x7F, 0x22, 0x31] = ReadDID failed — requestOutOfRange
# -----------------------------------------------------------------------------

NRC_GENERAL_REJECT                         = 0x10  # Rejet général
NRC_SERVICE_NOT_SUPPORTED                  = 0x11  # Service mashi supported
NRC_SUBFUNCTION_NOT_SUPPORTED              = 0x12  # Sub-function mashi supported
NRC_INCORRECT_MESSAGE_LENGTH               = 0x13  # Toul message ghalat
NRC_CONDITIONS_NOT_CORRECT                 = 0x22  # Conditions machi mzyana (ex: ghalat session)
NRC_REQUEST_OUT_OF_RANGE                   = 0x31  # DID mashi ma3rof
NRC_SECURITY_ACCESS_DENIED                 = 0x33  # Mashi mkhwwl (need unlock)
NRC_INVALID_KEY                            = 0x35  # Clé ghalat f security access
NRC_SERVICE_NOT_SUPPORTED_IN_SESSION       = 0x7F  # Service mashi dispo f had session
NRC_REQUEST_SEQUENCE_ERROR                 = 0x24  # Key sftiti qbel seed
NRC_REQUEST_TOO_LONG                       = 0x14  # Request tawla — kthar mn DID wahd
NRC_EXCEEDED_NUMBER_OF_ATTEMPTS = 0x36  # Too many wrong keys


NEGATIVE_RESPONSE_SID = 0x7F  # Awel byte dial kol negative response


# -----------------------------------------------------------------------------
# 7. Read / Write Data — Sub-functions & helpers
# -----------------------------------------------------------------------------
# SID 0x22 (ReadDataByIdentifier) w 0x2E (WriteDataByIdentifier)
# ma3ndhomch sub-function byte bhal DSC —
# payload kaykun: [SID, DID_high, DID_low, (data bytes pour write)]
#
# Exemples:
#   Read  request:  [0x22, 0xF4, 0x0D]              → qra DID 0xF40D
#   Read  response: [0x62, 0xF4, 0x0D, <value>]     → 0x62 = 0x22 + 0x40
#   Write request:  [0x2E, 0xF1, 0x90, <data...>]   → ktb DID 0xF190
#   Write response: [0x6E, 0xF1, 0x90]              → 0x6E = 0x2E + 0x40
# -----------------------------------------------------------------------------

# Minimum payload lengths
READ_DID_REQUEST_MIN_LEN  = 3   # [0x22, DID_H, DID_L]
# DID range limits (2 bytes → 0x0000 à 0xFFFF)
DID_MIN = 0x0000
DID_MAX = 0xFFFF

# DIDs standards ISO — quelques exemples utilisés f simulator
DID_VEHICLE_SPEED       = 0xF40D  # Vehicle Speed (km/h)
DID_ENGINE_TEMP         = 0xF405  # Engine Coolant Temperature (°C)
DID_VIN                 = 0xF190  # Vehicle Identification Number (17 chars)
DID_ECU_SERIAL          = 0xF18C  # ECU Serial Number
DID_ACTIVE_SESSION      = 0xF186  # Active Diagnostic Session (read-only)


# -----------------------------------------------------------------------------
# 8. User Roles (RBAC — Role Based Access Control)
# -----------------------------------------------------------------------------
# Kol user 3ndu role — role kayhdrd shi services yqdr ykhdem.
# Ex: READER yqdr ghir yqra DIDs — mashi yktb
# -----------------------------------------------------------------------------

ROLE_ADMIN      = "admin"       # Kol shi msmoh — read + write + sessions + reset
ROLE_TECHNICIAN = "technician"  # Read + write + sessions — mashi security access
ROLE_READER     = "reader"      # Ghir read DIDs — mashi write mashi reset


# -----------------------------------------------------------------------------
# 9. Session Access Matrix
# -----------------------------------------------------------------------------
# Dict li kayhdrd ayy service msmoh f ayy session + ayy role
# -----------------------------------------------------------------------------

SESSION_SERVICE_MATRIX = {
    SESSION_DEFAULT: {
        "allowed_services": [
            SID_DIAGNOSTIC_SESSION_CONTROL,
            SID_SECURITY_ACCESS,
            SID_READ_DATA_BY_IDENTIFIER,
            SID_ECU_RESET,
        ],
        "description": "Default Session — services de base Sghir"
    },
    SESSION_EXTENDED: {
        "allowed_services": [
            SID_DIAGNOSTIC_SESSION_CONTROL,
            SID_ECU_RESET,
            SID_READ_DATA_BY_IDENTIFIER,
            SID_SECURITY_ACCESS,
        ],
        "description": "Extended Session — kthar services mftuhin"
    },
    SESSION_PROGRAMMING: {
        "allowed_services": [
            SID_DIAGNOSTIC_SESSION_CONTROL,
            SID_ECU_RESET,
            SID_READ_DATA_BY_IDENTIFIER,
            SID_SECURITY_ACCESS,
        ],
        "description": "Programming Session — flash w security ghir"
    },
}


# -----------------------------------------------------------------------------
# 10. Role Service Permissions
# -----------------------------------------------------------------------------
# Men b3d session check, kayjay role check.
# Admin yqdr kol shi, technician htta write, reader ghir read.
# -----------------------------------------------------------------------------

ROLE_PERMISSIONS = {
    ROLE_ADMIN: {
        "can_read":             True,
        "can_reset":            True,
        "can_change_session":   True,
        "can_security_access":  True,
    },
    ROLE_TECHNICIAN: {
        "can_read":             True,
        "can_reset":            True,
        "can_change_session":   True,
        "can_security_access":  False,
    },
    ROLE_READER: {
        "can_read":             True,
        "can_reset":            False,
        "can_change_session":   False,
        "can_security_access":  False,
    },
}


# -----------------------------------------------------------------------------
# 11. Human-readable name maps — pour affichage f GUI
# -----------------------------------------------------------------------------

SESSION_NAMES = {
    SESSION_DEFAULT:     "Default Session (0x01)",
    SESSION_PROGRAMMING: "Programming Session (0x02)",
    SESSION_EXTENDED:    "Extended Session (0x03)",
}

RESET_NAMES = {
    RESET_HARD:    "Hard Reset (0x01)",
    RESET_KEY_OFF: "Key Off/On Reset (0x02)",
    RESET_SOFT:    "Soft Reset (0x03)",
}

SEC_NAMES = {
    REQUEST_SEED:    "Request Seed (0x01)",
    SEND_KEY: "Send Key (0x02)",
}

NRC_NAMES = {
    NRC_GENERAL_REJECT:                        "generalReject",
    NRC_SERVICE_NOT_SUPPORTED:                 "serviceNotSupported",
    NRC_SUBFUNCTION_NOT_SUPPORTED:            "subFunctionNotSupported",
    NRC_INCORRECT_MESSAGE_LENGTH:             "incorrectMessageLength",
    NRC_CONDITIONS_NOT_CORRECT:               "conditionsNotCorrect",
    NRC_REQUEST_OUT_OF_RANGE:                 "requestOutOfRange",
    NRC_SECURITY_ACCESS_DENIED:               "securityAccessDenied",
    NRC_INVALID_KEY:                          "invalidKey",
    NRC_SERVICE_NOT_SUPPORTED_IN_SESSION:     "serviceNotSupportedInActiveSession",
    NRC_REQUEST_SEQUENCE_ERROR:               "requestSequenceError",
    NRC_INVALID_KEY            :              "invalidKey",
    NRC_REQUEST_TOO_LONG :                    "requestTooLong",
    NRC_EXCEEDED_NUMBER_OF_ATTEMPTS: "exceededNumberOfAttempts",
}