# Heating Controller

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/jozef-moravcik-homeassistant/heating-controller)](https://github.com/jozef-moravcik-homeassistant/heating-controller/releases)

The heating controller is a Home Assistant integration for advanced control of the primary part of the heating system (control of heat sources and storage tanks) which is "heat source". In the scope of this controller is not the secondary part of the heating system (controller for floor heating, radiators, fan-coils, etc.)

## Features

- Automatic control of heat pump output direction (ACC/DHW)
- Intelligent management of two accumulation tanks
- Heat transfer from ACC to DHW
- Multiple operating modes
- Valve and pump control with safety mechanisms
- Configurable parameters via UI

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/jozef-moravcik-homeassistant/heating-controller`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Heating Controller" and install it
9. Restart Home Assistant
10. Go to Settings → Devices & Services → Add Integration → Heating Controller

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/heating_controller` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Add Integration → Heating Controller

## Configuration

The integration is configured via the UI. You will need to provide:

- Temperature sensors (ACC1, ACC2, DHW)
- Valve entities
- Pump entities
- Thermostat state entities

## Operating Modes

| Mode | Description |
|------|-------------|
| Manual | Manual control without automatic switching |
| DHW Only | Heat pump heats only DHW |
| P-DHW > DHW | First pump from ACC, then direct DHW heating |
| ACC Only | Heat pump heats only ACC |
| ACC + P-DHW | Heat ACC + automatic pumping to DHW |
| DHW > ACC | Priority DHW, then ACC |
| P-DHW > DHW > ACC | Complete cycle with maximum efficiency |

## Author

Jozef Moravčík (jozef.moravcik@moravcik.eu)

## License

-
