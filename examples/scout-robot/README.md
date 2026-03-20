# Scout Robot — Crimp Example

Scout is a hobby autonomous robot being used to dogfood Crimp during development.

## Hardware

- Jetson Orin Nano 8GB (main compute)
- Raspberry Pi 4 8GB (ROS2 bridge, GPS)
- Raspberry Pi Pico running micro-ROS (low-level I/O)
- Pololu Simple High-Power Motor Controller 24v12 (drive)
- Pololu Jrk G2 21v3 (steering, closed-loop)
- 12V 100Ah LiFePO4 battery with Victron BMS/protection
- OAK-D depth camera, AS5600 encoders, simpleRTK2B GPS

The `manifest.json` in this directory is the single source of truth for Scout's wiring.
All pinout docs, assembly guides, and commissioning tests are generated from it.
