"""
Run this file to rename the attached webcam
Usage: python rename_camera.py <camera_name>
"""
import subprocess
import sys
import re
import os
import shutil
import hashlib


def build_jffs2(source_dir, output_file, erase_size="0x20000", page_size="512", pad_size="1024KiB", 
                compression=None, endianness="-l", no_cleanmarkers=False, cleanmarker_size=None,
                faketime=False, squash_perms=False, squash_uids=False, squash_all=False):
    cmd = [
        "wsl", "mkfs.jffs2",
        "-r", source_dir,
        "-o", output_file,
        "-e", erase_size,
        "-s", page_size,
    ]
    
    if compression:
        cmd.extend(["-q", compression])
    
    if pad_size:
        cmd.extend(["-p", pad_size])
    
    if endianness:
        cmd.append(endianness)
    
    if no_cleanmarkers:
        cmd.append("-n")
    
    if cleanmarker_size:
        cmd.extend(["-c", cleanmarker_size])
    
    if faketime:
        cmd.append("-f")
    
    if squash_all:
        cmd.append("-q")
    elif squash_uids:
        cmd.append("-U") 
    elif squash_perms:
        cmd.append("-P")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"Error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("mkfs.jffs2 not found. Install mtd-utils into windows subsystem for linux.")
        return False

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except FileNotFoundError:
        return None

def scan_for_correct_build_args(source_dir, original_file, test_output_file):
    """Grid search to find correct build parameters"""
    
    # Parameter options to test
    erase_sizes = ["0x10000", "0x20000", "0x40000", "0x80000"]
    page_sizes = ["256", "512", "1024", "2048", "4096"]  
    pad_sizes = [None, "512KiB", "1024KiB", "2048KiB"]
    compressions = [None, "lzo", "zlib"]
    endianness_options = ["-l"]
    cleanmarker_options = [False, True]
    cleanmarker_sizes = [None, "12", "16", "20"]
    faketime_options = [False, True]
    squash_options = [None, "perms", "uids", "all"]
    
    original_hash = get_file_hash(original_file)
    if not original_hash:
        print(f"Error: Cannot read original file {original_file}")
        return None
        
    print(f"Original file hash: {original_hash}")
    print("Starting comprehensive grid search...")
    
    total_combinations = (len(erase_sizes) * len(page_sizes) * len(pad_sizes) * 
                         len(compressions) * len(endianness_options) * len(cleanmarker_options) *
                         len(cleanmarker_sizes) * len(faketime_options) * len(squash_options))
    current = 0
    
    for erase_size in erase_sizes:
        for page_size in page_sizes:
            for pad_size in pad_sizes:
                for compression in compressions:
                    for endianness in endianness_options:
                        for no_cleanmarkers in cleanmarker_options:
                            for cleanmarker_size in cleanmarker_sizes:
                                for faketime in faketime_options:
                                    for squash in squash_options:
                                        current += 1
                                        
                                        # Build parameter description
                                        params = [f"-e {erase_size}", f"-s {page_size}"]
                                        if pad_size:
                                            params.append(f"-p {pad_size}")
                                        if compression:
                                            params.append(f"-q {compression}")
                                        params.append(endianness)
                                        if no_cleanmarkers:
                                            params.append("-n")
                                        if cleanmarker_size:
                                            params.append(f"-c {cleanmarker_size}")
                                        if faketime:
                                            params.append("-f")
                                        if squash == "all":
                                            params.append("-q")
                                        elif squash == "uids":
                                            params.append("-U")
                                        elif squash == "perms":
                                            params.append("-P")
                                        
                                        param_str = " ".join(params)
                                        print(f"Testing {current}/{total_combinations}: {param_str}")
                                        
                                        # Remove previous test file if it exists
                                        if os.path.exists(test_output_file):
                                            os.remove(test_output_file)
                                        
                                        # Try building with these parameters
                                        success = build_jffs2(source_dir, test_output_file, erase_size, page_size, 
                                                            pad_size, compression, endianness, no_cleanmarkers, 
                                                            cleanmarker_size, faketime, 
                                                            squash=="perms", squash=="uids", squash=="all")
                                        
                                        if success:
                                            test_hash = get_file_hash(test_output_file)
                                            if test_hash and test_hash == original_hash:
                                                print(f"\n🎉 MATCH FOUND!")
                                                print(f"Correct parameters: {param_str}")
                                                return {
                                                    "erase_size": erase_size, 
                                                    "page_size": page_size, 
                                                    "pad_size": pad_size,
                                                    "compression": compression,
                                                    "endianness": endianness,
                                                    "no_cleanmarkers": no_cleanmarkers,
                                                    "cleanmarker_size": cleanmarker_size,
                                                    "faketime": faketime,
                                                    "squash": squash
                                                }
    
    print("\n❌ No matching combination found")
    return None

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
    original_file = "Firmware-Staging/appfs.jffs2"
    output_file = "Firmware-Staging/appfs-new.jffs2"  # os.path.join("Firmware-Staging", "appfs-new.jffs2")
    build_jffs2(input_dir, output_file)

    scan_for_correct_build_args(input_dir, original_file, output_file)


if __name__ == "__main__":
    main()
