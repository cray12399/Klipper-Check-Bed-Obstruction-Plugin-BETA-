# Klipper Check Bed Obstruction Plugin BETA
A Klipper plugin that checks for obstructions in the bed using Ollama cloud AI models. This plugin is in the public beta stage and therefore may have some bugs.

# Installation

**1. Install the plugin.**
```
curl -sfL https://raw.githubusercontent.com/cray12399/Klipper-Check-Bed-Obstruction-Plugin-BETA-/main/install.sh | bash
```

**2. Add the config section to printer.cfg**
```
[check_bed_obstruction]
# MANDATORY. Your Ollama API key. How to get one:
# https://simplai.ai/docs/API_Keys/LLM_model/oolama-llm-model
api_key: 

# MANDATORY. Urls for the model to obtain snapshots of the current bed. Urls should be full urls including http:// / https://
# Specify multiple camera urls by separating with commas.
# Ex. http://localhost:1984/api/frame.jpeg?src=cam1,http://localhost:1984/api/frame.jpeg?src=cam1,http://localhost:1984/api/frame.jpeg?src=cam2
camera_snapshot_urls: 

# The gcode macro command to turn on your chamber LED to ensure the bed is properly lit for the AI to analyze it.
# Ex. SET_LED LED=chamber_leds RED=1 GREEN=1 BLUE=1 WHITE=1
# chamber_led_command: 

# Specify a different model than the default, qwen3-vl:235b-instruct-cloud.
# List of models: https://ollama.com/search?c=vision&c=cloud
# model:

# Specifies whether obstructions should have a detailed reason for denials. Default is False.
# provide_reason: 

# POTENTIALLY DANGEROUS. Extension to prompt for more flexibility and control. 
# For ex. "My print bed is black. The toolhead has a red cpap duct that is fed with a black umbilical cpap tube.
# prompt_extension:

```

# Usage

**Primary Usage: **
Add `CHECK_BED_OBSTRUCTION` gcode to whatever macro in which you need the bed to be checked for obstructions. 

To override homing, for example:
```
[gcode_macro G28]
rename_existing: G28.1
gcode:

  CHECK_BED_OBSTRUCTION

  {% if params.X is defined or params.Y is defined or params.Z is defined %}
    G28.1 {rawparams}
  {% else %}
    G28.1
  {% endif %}
```

**Providing Reference Images to the AI: **
You can also optionally provide reference images for a clear bed to the AI. To do so, take clear empty bed reference images using the command `TAKE_REFERENCE_IMAGES`. Running the command on your printer will save snapshots from `camera_snapshot_urls` in `printer.cfg` to `~/printer_data/config/bed_images/`
