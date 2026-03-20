# Crimp

**An AI-native hardware manifest tool for robot builders and makers.**

> ⚠️ Alpha / early-stage. The manifest format and CLI are not yet stable.
> Expect breaking changes between versions.

---

## The Problem

You're building a robot. You have a Pico talking to two AS5600 encoders over
separate I2C buses, eight relay channels, a UART RC receiver, and a pile of
PWM outputs for lights. You know what every wire does — but that knowledge
lives in your head, in scattered notes, and in a pinout diagram you drew at
midnight and haven't updated since you rewired the relay board.

When something goes wrong, you go hunting. When someone else touches your
robot, they're lost. When you come back after three months, you're lost too.

---

## What Crimp Does

Crimp keeps your wiring knowledge in one structured file called the
**manifest**. An AI writes and maintains the manifest. Crimp reads the
manifest and generates everything else:

| Output | What it is |
|---|---|
| **Pinout docs** | Markdown tables showing every pin on every board |
| **Wiring diagram** | Visual connection diagram (WireViz / Mermaid) |
| **Assembly guide** | Step-by-step plain English wire-by-wire instructions |
| **Commissioning tests** | pytest scripts that verify every connection |
| **BOM** | Bill of materials for connectors and wire |

You never read or write the manifest. The AI does that. You follow the
assembly guide like a technician following a diagram, and you run the
commissioning tests to verify your work.

---

## The Workflow

### 1. Describe your project to an AI

Tell your AI assistant what you're building. Describe the boards, the
connections, the wire colors you have on hand, the connector types. The AI
generates a `manifest.json` for you.

```
You: I have a Raspberry Pi Pico connected to two AS5600 magnetic encoders
     over I2C. Encoder 1 is on I2C0 (GP4/GP5), encoder 2 is on I2C1
     (GP6/GP7). Both run on 3.3V. I'm using red for VCC, black for GND,
     blue for SDA, yellow for SCL. JST-PH 4-pin connectors on the encoder
     side, bare wire to Pico pin headers.

AI:  [generates manifest.json]
```

### 2. Run Crimp to generate your docs

```bash
crimp build manifest.json
```

Crimp writes to `crimp-output/`:

```
crimp-output/
  pinouts/
    pico.md
    as5600_encoder1.md
    as5600_encoder2.md
  wiring-diagram.svg
  assembly-guide.md
  commissioning/
    test_wiring.py
  bom.md
```

### 3. Build from the assembly guide

Open `assembly-guide.md`. Follow it wire by wire:

```
Step 1 of 14 — AS5600 Encoder 1, VCC
  Run red 26AWG from Pico 3V3 OUT (pin 36) to AS5600 #1 VCC pad.
  Connector: bare wire on Pico end, JST-PH pin 1 on encoder end.
  ✓ Verify: 3.3V present at encoder VCC with multimeter before proceeding.

Step 2 of 14 — AS5600 Encoder 1, GND
  Run black 26AWG from Pico GND (pin 8) to AS5600 #1 GND pad.
  Connector: bare wire both ends.
  ...
```

### 4. Commission with the test scripts

Plug everything in. Run the commissioning tests:

```bash
pytest crimp-output/commissioning/test_wiring.py -v
```

Tests are driven directly from the manifest — they know which GPIOs should
respond and what they should see. A failing test tells you exactly which
connection to check.

### 5. When things change, update through the AI

Added a relay board? Tell the AI, it updates the manifest. Run `crimp build`
again. The assembly guide updates to show only the new steps. The commissioning
tests update. The BOM updates.

---

## Key Concepts

**The manifest is the single source of truth.** Everything Crimp generates is
derived from it. If you find an error in the assembly guide, don't fix the
guide — tell the AI to fix the manifest, then regenerate.

**The manifest is designed for AI, not humans.** It is explicit, verbose, and
unambiguous. It contains information you would find tedious to write by hand.
That's intentional. You don't write it; the AI does.

**Crimp is a generator, not a wiki.** Generated files are outputs. Don't
hand-edit them — your changes will be overwritten on the next `crimp build`.

---

## Who This Is For

Crimp is built for makers and robot hobbyists who:

- Crimp JST, Dupont, or XT connectors by hand
- Use a multimeter to verify connections
- Work with development boards (Raspberry Pi, Arduino, ESP32, STM32, etc.)
- Build one-off or small-batch projects, not production runs
- Don't have (or want) industrial wire harness tooling or EE CAD software

Crimp is **not** designed for PCB layout, schematic capture, or professional
harness manufacturing workflows.

---

## Installation

```bash
pip install crimp-manifest
```

Requires Python 3.11+. WireViz must be installed separately for SVG diagram
output:

```bash
pip install wireviz
```

---

## Quick Start

```bash
# Build all outputs from a manifest
crimp build manifest.json

# Validate manifest against schema without building
crimp validate manifest.json

# List what would be generated without writing files
crimp build manifest.json --dry-run

# Print the schema (useful when prompting an AI to generate a manifest)
crimp schema
```

---

## Project Status

Crimp is in early alpha. The manifest schema is in active development and
**will** change in breaking ways before v1.0.

- [ ] Manifest JSON schema
- [ ] CLI (`build`, `validate`, `schema`)
- [ ] Pinout doc generation
- [ ] Assembly guide generation
- [ ] BOM generation
- [ ] WireViz diagram generation
- [ ] Commissioning test generation
- [ ] Scout robot example manifest (dogfood)

Contributions welcome. See `CONTRIBUTING.md`.

---

## Why "Crimp"?

Crimping is the act of mechanically joining a wire to a connector terminal —
the last physical step before a connection is real. The tool is named after
that moment: the point where design becomes hardware.

---

## Real-World Example

Crimp is being dogfooded on [Scout](examples/scout-robot/), a hobby
autonomous robot with a Jetson Orin Nano, Raspberry Pi 4, Raspberry Pi Pico
running micro-ROS, GPS, depth cameras, motor controllers, and a 12V LiFePO4
battery system.
