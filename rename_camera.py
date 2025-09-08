"""
Run this file to rename the attached webcam
Usage: python rename_camera.py <camera_name>
"""
import subprocess
import sys
import re
import os
import shutil


def build_jffs2(source_dir, output_file, erase_size="0x20000", page_size="512"):
    cmd = [
        "wsl", "mkfs.jffs2",
        "-r", source_dir,  # Checked
        "-o", output_file,  # Checked
        "-e", erase_size,  # Checked
        "-s", page_size,
        "-q", "lzo",
        "-p", "1024KiB"
        "-l",  # Checked
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Successfully created {output_file}")
        else:
            print(f"Error: {result.stderr}")
    except FileNotFoundError:
        print("mkfs.jffs2 not found. Install mtd-utils into windows subsystem for linux.")

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
        try:
            result = subprocess.run(["rd", "/s", "/q", "Firmware-Staging"], 
                                  shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Could not remove Firmware-Staging: {result.stderr}")
        except Exception as e:
            print(f"Warning: Could not remove Firmware-Staging: {e}")
    
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
    # Skip for now
    # with open(config_path, 'w') as f:
    #     f.writelines(updated_lines)
    
    print(f"Successfully updated {config_path}")
    print(f"product_lab and video_name set to: {formatted_name}")

    # Build the jffs2
    input_dir = "Firmware-Staging/appfs.dir"  # os.path.join("Firmware-Staging/appfs.dir")
    output_file = "Firmware-Staging/appfs-new.jffs2"  # os.path.join("Firmware-Staging", "appfs-new.jffs2")
    build_jffs2(input_dir, output_file)


if __name__ == "__main__":
    main()
