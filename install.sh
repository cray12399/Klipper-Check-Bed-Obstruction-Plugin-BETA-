#!/bin/bash

# --- Configuration ---
TARGET_DIR=~/klipper/klippy/plugins/
KLIPPER_ENV=~/klippy-env

# Download the Plugin
echo "--- Starting Plugin Download ---"

# Create the directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Navigate to the directory
cd "$TARGET_DIR"

# Download the file using wget (converting URL to raw)
echo "Downloading check_bed_obstruction.py to $TARGET_DIR..."
wget -q --show-progress -O check_bed_obstruction.py https://raw.githubusercontent.com/cray12399/Klipper-Check-Bed-Obstruction-Plugin-BETA-/main/check_bed_obstruction.py

if [ $? -eq 0 ]; then
    echo "Plugin download successful!"
    chmod +x check_bed_obstruction.py
else
    echo "Download failed. Please check your internet connection."
    exit 1
fi

echo ""

# Install Ollama in Klipper Env
echo "--- Installing Ollama Library ---"

# Check if the Klipper virtual environment exists
if [ -d "$KLIPPER_ENV" ]; then
    echo "Found Klipper environment at $KLIPPER_ENV"
    echo "Installing 'ollama' via pip..."

    # Use the absolute path to the virtual environment's pip
    "$KLIPPER_ENV"/bin/pip install ollama

    if [ $? -eq 0 ]; then
        echo "Successfully installed 'ollama' into Klipper environment."
    else
        echo "Failed to install 'ollama'. Check the error logs above."
    fi
else
    echo "ERROR: Klipper virtual environment not found at $KLIPPER_ENV."
    echo "If your environment is in a different location, please edit the 'KLIPPER_ENV' variable in this script."
fi

echo "--- Done ---"
echo "You may need to restart Klipper for changes to take effect."
