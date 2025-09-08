"""
Run this file to rename the attached webcam
Usage: python rename_camera.py <camera_name>
"""

import sys
import re
import os
import shutil

def main():
    if len(sys.argv) != 2:
        print("Usage: python rename_camera.py <camera_name>")
        print("Example: python rename_camera.py MYNAME")
        print("Please note: Only capital letters and numbers can be used for the name")
        sys.exit(1)
    
    camera_name = sys.argv[1]
    
    # Convert to uppercase and keep only alphanumeric characters
    formatted_name = re.sub(r'[^A-Z0-9]', '', camera_name.upper())
    
    if not formatted_name:
        print("Error: Camera name must contain at least one alphanumeric character")
        sys.exit(1)
    
    print(f"Original name: {camera_name}")
    print(f"Formatted name: {formatted_name}")
    
    # Check if Firmware directory exists
    if not os.path.exists("Firmware"):
        print("Error: Firmware directory not found")
        sys.exit(1)
    
    # Remove existing Firmware-Staging if it exists
    if os.path.exists("Firmware-Staging"):
        print("Removing existing Firmware-Staging...")
        shutil.rmtree("Firmware-Staging")
    
    # Copy Firmware to Firmware-Staging
    print("Copying Firmware to Firmware-Staging...")
    shutil.copytree("Firmware", "Firmware-Staging")
    
    # Path to the uvc.config file in staging
    config_path = os.path.join("Firmware-Staging", "appfs.dir", "config", "uvc.config")
    
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    
    # Read the current config
    with open(config_path, 'r') as f:
        lines = f.readlines()
    
    # Update product_lab and video_name values
    updated_lines = []
    for line in lines:
        if line.startswith('product_lab'):
            updated_lines.append(f"product_lab     :{formatted_name}\n")
        elif line.startswith('video_name'):
            updated_lines.append(f"video_name      :{formatted_name}\n")
        else:
            updated_lines.append(line)
    
    # Write the updated config
    with open(config_path, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"Successfully updated {config_path}")
    print(f"product_lab and video_name set to: {formatted_name}")

if __name__ == "__main__":
    main()
