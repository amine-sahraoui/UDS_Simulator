# Welcome to the Sigma Tech Projects Repository!

Hey Sigma Embedded fans! 🎉 We're thrilled to have you here. This repository is the heart of all our exciting tech endeavors. Whether you're here to contribute, learn, or just explore, you've come to the right place.

## About Sigma Tech Projects
The Sigma Tech Projects repository is dedicated to driving innovation and sharing knowledge in the tech community. From cutting-edge projects to insightful discussions, we're all about pushing the boundaries of technology.

## Repository Overview

### What You'll Find Here
- **Project Code:** Access the source code for our latest tech projects.
- **Documentation:** Comprehensive guides and references to help you understand and contribute to our projects.
- **Issues and Discussions:** Engage with the community, report issues, and discuss solutions.

### How to Contribute
We welcome contributions from everyone! Whether it's improving our documentation, adding new features, or reporting bugs, your input is invaluable. Here's how you can get started:
1. **Fork the repository:** Create your own copy of the repository.
2. **Clone the repository:** Download your fork to your local machine.
3. **Submit a pull request:** Send your changes for review.

## Stay Connected
Don't miss out on any updates! Follow us on our social media channels:
- **[LinkedIn/Page](https://www.linkedin.com/company/sigma-embedded)**
- **[LinkedIn/Groupe](https://www.linkedin.com/groups/12842283/)**
- **[Youtube](https://www.youtube.com/@SigmaEmbedded-md4dm)**
- **[Discord](https://discord.gg/RBSbh2MENz)**

# Project : UDS Simulator — ISO 14229

Before starting, please check these videos to know more about the project:
- Playlist of 5 videos : https://www.youtube.com/watch?v=45uOKPl1TC0&list=PLr1rq87x9mAN2R7WaSTrCXa8dwDOryPTM


# Project Description
> Pure software UDS diagnostic simulator built with Python & PyQt5.  
> Simulates an ECU responding to diagnostic requests with real-time frame tracing.

---

## Installation

```bash
pip install PyQt5
```

---

## To generate executable File

```bash
 pyinstaller --onefile --noconsole --icon=logo_icon.ico --add-data "logo_icon.ico;." --add-data "logo;logo" main.py
```

---

## Supported UDS Services

| SID | Service | Description |
|-----|---------|-------------|
| `0x10` | DiagnosticSessionControl | Switch between Default / Extended / Programming |
| `0x11` | ECUReset | Hard / Key Off / Soft reset |
| `0x22` | ReadDataByIdentifier | Read DID value from ECU |
| `0x27` | SecurityAccess | Seed/Key authentication (XOR 0xFF) |

---

## Diagnostic Sessions

| Session | Code | Condition |
|---------|------|-----------|
| Default | `0x01` | No condition |
| Extended | `0x03` | Security must be unlocked |
| Programming | `0x02` | Security unlocked + Engine Stopped |

---

## NRC Codes

| NRC | Name | Trigger |
|-----|------|---------|
| `0x10` | generalReject | Invalid SID (1 hex char) |
| `0x11` | serviceNotSupported | SID not in valid list |
| `0x12` | subFunctionNotSupported | Invalid sub-function |
| `0x13` | incorrectMessageLength | Wrong byte count |
| `0x14` | requestTooLong | Multiple DIDs in one request |
| `0x22` | conditionsNotCorrect | VIN read while speed != 0 |
| `0x24` | requestSequenceError | Key sent before seed |
| `0x31` | requestOutOfRange | DID not in database |
| `0x33` | securityAccessDenied | Security not unlocked |
| `0x35` | invalidKey | Wrong key sent |
| `0x7E` | subFunctionNotSupportedInActiveSession | Sub-function not allowed in session |
| `0x7F` | serviceNotSupportedInActiveSession | Service not allowed in session |

---

## DID Database

| DID | Name | Type | R | W | Roles |
|-----|------|------|---|---|-------|
| `0xF40D` | Vehicle Speed | uint8 | ✓ | ✗ | All |
| `0xF405` | Engine Coolant Temp | uint8 | ✓ | ✗ | All |
| `0xF406` | Engine RPM | uint16 | ✓ | ✗ | All |
| `0xF190` | VIN | string | ✓ | ✓ | Admin |
| `0xF18C` | ECU Serial Number | string | ✓ | ✗ | Admin, Tech |
| `0xF186` | Active Session | uint8 | ✓ | ✗ | All |
| `0xF187` | SW Version | string | ✓ | ✗ | All |
| `0xF193` | HW Version | string | ✓ | ✗ | All |
| `0x0101` | Odometer | uint32 | ✓ | ✗ | All |
| `0x0102` | Fuel Level | uint8 | ✓ | ✗ | All |
| `0x0200` | Max Speed Limit | uint8 | ✓ | ✓ | Admin, Tech |
| `0x0201` | ECU Debug Mode | uint8 | ✓ | ✓ | Admin |

---

## User Roles

| Role | Password | Read | Write | Session | Reset | Security |
|------|----------|------|-------|---------|-------|----------|
| `admin` | admin123 | ✓ | ✓ | ✓ | ✓ | ✓ |
| `technician` | tech456 | ✓ | ✓ | ✓ | ✓ | ✗ |
| `reader` | read789 | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## Security Access Flow

```
1. Send seed request  →  0x2701
2. ECU responds       →  67 01 12 34
3. Calculate key      →  key = seed XOR 0xFF  →  ED CB
4. Send key           →  0x2702EDCB
5. ECU grants access  →  67 02
```

---

## Command Input Examples

| Command | Description |
|---------|-------------|
| `0x1001` | Default Session |
| `0x1003` | Extended Session |
| `0x1002` | Programming Session |
| `0x1101` | Hard Reset |
| `0x1103` | Soft Reset |
| `0x22F40D` | Read Vehicle Speed |
| `0x22F190` | Read VIN |
| `0x2701` | Request Security Seed |
| `0x270200EDCB` | Send Security Key |

---
