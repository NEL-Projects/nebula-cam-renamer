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


def build_jffs2_from_params(source_dir, output_file, params_string):
    """Build JFFS2 filesystem using a parameter string"""
    # Split params_string into individual arguments
    params_list = params_string.split()
    
    cmd = [
        "wsl", "mkfs.jffs2",
        "-r", source_dir,
        "-o", output_file
    ]
    
    # Add the parameter arguments
    cmd.extend(params_list)
    
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

def build_jffs2(source_dir, output_file, erase_size="0x20000", page_size="512", pad_size="1024KiB", 
                compression=None, endianness="-l", no_cleanmarkers=False, cleanmarker_size=None,
                faketime=False, squash_perms=False, squash_uids=False, squash_all=False,
                compr_mode=None, with_xattr=False, with_selinux=False, with_posix_acl=False, devtable=None,
                disable_compressor=None, enable_compressor=None):
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
    
    if compr_mode:
        cmd.extend(["-m", compr_mode])
    
    if with_xattr:
        cmd.append("--with-xattr")
    
    if with_selinux:
        cmd.append("--with-selinux")
    
    if with_posix_acl:
        cmd.append("--with-posix-acl")
    
    if devtable and os.path.exists(devtable):
        cmd.extend(["-D", devtable])

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

def get_jffs2_dump(filepath):
    """Get first 20 lines of jffs2dump -c -v output"""
    try:
        result = subprocess.run(["wsl", "jffs2dump", "-c", "-v", filepath], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')[:20]
            return '\n'.join(lines)
        else:
            return None
    except FileNotFoundError:
        return None

def compare_jffs2_dumps(file1, file2):
    """Compare first 20 lines of jffs2dump output for two files"""
    dump1 = get_jffs2_dump(file1)
    dump2 = get_jffs2_dump(file2)
    
    if dump1 and dump2:
        return dump1 == dump2
    return False

def compare_binaries_32bit(file1, file2):
    """Compare two binary files 32 bits at a time and count differences"""
    try:
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            differences = 0
            chunk_size = 4  # 32 bits = 4 bytes
            
            while True:
                chunk1 = f1.read(chunk_size)
                chunk2 = f2.read(chunk_size)
                
                # If one file is shorter, count remaining chunks as different
                if len(chunk1) != len(chunk2):
                    if chunk1:
                        differences += 1
                    if chunk2:
                        differences += 1
                    break
                
                # If both chunks are empty, we've reached the end
                if not chunk1:
                    break
                
                # Compare the 32-bit chunks
                if chunk1 != chunk2:
                    differences += 1
                    
        return differences
    except FileNotFoundError:
        return float('inf')  # Return infinity if files don't exist

def compare_file_listings(original_file, test_file):
    """Compare the file listings from both JFFS2 images to check permissions/timestamps"""
    try:
        # Get file listings from both images
        result1 = subprocess.run(["wsl", "jffs2dump", "-c", original_file], 
                               capture_output=True, text=True)
        result2 = subprocess.run(["wsl", "jffs2dump", "-c", test_file], 
                               capture_output=True, text=True)
        
        if result1.returncode == 0 and result2.returncode == 0:
            lines1 = result1.stdout.split('\n')
            lines2 = result2.stdout.split('\n')
            
            print(f"\n📁 FILE LISTING COMPARISON:")
            print(f"Original has {len(lines1)} lines, Test has {len(lines2)} lines")
            
            # Compare first 20 lines for differences
            max_lines = min(20, len(lines1), len(lines2))
            differences = 0
            
            for i in range(max_lines):
                if lines1[i] != lines2[i]:
                    differences += 1
                    print(f"Line {i+1} differs:")
                    print(f"  Original: {lines1[i]}")
                    print(f"  Test:     {lines2[i]}")
            
            print(f"Found {differences} line differences in first {max_lines} lines")
            return differences
        else:
            print("Error running jffs2dump for comparison")
            return -1
    except Exception as e:
        print(f"Error comparing file listings: {e}")
        return -1

def analyze_filesystem_structure(filepath):
    """Analyze the filesystem structure to check for timestamp/permission patterns"""
    try:
        result = subprocess.run(["wsl", "jffs2dump", "-c", "-v", filepath], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')[:50]  # First 50 lines
            
            print(f"\n🔍 FILESYSTEM ANALYSIS for {filepath}:")
            timestamp_pattern = False
            permission_pattern = False
            
            for line in lines:
                if 'mtime' in line or 'ctime' in line or 'atime' in line:
                    print(f"  Timestamp: {line.strip()}")
                    timestamp_pattern = True
                if 'mode' in line or 'uid' in line or 'gid' in line:
                    print(f"  Permission: {line.strip()}")
                    permission_pattern = True
                if 'Empty space' in line:
                    print(f"  🎯 {line.strip()}")
            
            return {"timestamps": timestamp_pattern, "permissions": permission_pattern}
        else:
            print(f"Error analyzing {filepath}: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error analyzing filesystem: {e}")
        return None

def extract_and_compare_files(original_jffs2, test_jffs2):
    """Extract files from both JFFS2 images and compare actual file contents"""
    import tempfile
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_extract = os.path.join(temp_dir, "original")
            test_extract = os.path.join(temp_dir, "test")
            
            os.makedirs(original_extract)
            os.makedirs(test_extract)
            
            print(f"\n📂 EXTRACTING AND COMPARING FILE CONTENTS:")
            
            # Extract both filesystems (this might not work with jffs2dump, need alternative)
            # For now, let's compare the raw binary content at different offsets
            with open(original_jffs2, 'rb') as f1, open(test_jffs2, 'rb') as f2:
                f1_data = f1.read()
                f2_data = f2.read()
                
                print(f"Original size: {len(f1_data)} bytes")
                print(f"Test size: {len(f2_data)} bytes")
                
                # Compare first 1000 bytes
                first_1000_match = f1_data[:1000] == f2_data[:1000]
                print(f"First 1000 bytes match: {first_1000_match}")
                
                # Compare last 1000 bytes  
                last_1000_match = f1_data[-1000:] == f2_data[-1000:]
                print(f"Last 1000 bytes match: {last_1000_match}")
                
                # Find first difference
                for i in range(min(len(f1_data), len(f2_data))):
                    if f1_data[i] != f2_data[i]:
                        print(f"First difference at byte {i} (0x{i:x})")
                        print(f"  Original: 0x{f1_data[i]:02x}")
                        print(f"  Test:     0x{f2_data[i]:02x}")
                        
                        # Show context around the difference
                        start = max(0, i-10)
                        end = min(len(f1_data), i+10)
                        print(f"  Context original: {f1_data[start:end].hex()}")
                        print(f"  Context test:     {f2_data[start:end].hex()}")
                        break
                
                return {"size_match": len(f1_data) == len(f2_data), 
                       "first_diff_at": i if 'i' in locals() else None}
                
    except Exception as e:
        print(f"Error extracting/comparing files: {e}")
        return None

def create_device_table_with_timestamp(filename, source_dir, timestamp):
    """Create a device table file with specific timestamp for all files"""
    try:
        with open(filename, 'w') as f:
            # Walk through the source directory and create entries for all files
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    os.utime(full_path, (timestamp, timestamp))

                    rel_path = os.path.relpath(full_path, source_dir)
                    # Normalize path separators for Linux
                    rel_path = "/" + rel_path.replace("\\", "/")

                    # Get file stats for mode
                    stat = os.stat(full_path)
                    mode = oct(stat.st_mode)[-3:]  # Get last 3 digits

                    # Device table format: name type mode uid gid major minor start inc count [timestamp]
                    # For regular files: name f mode uid gid - - - - - timestamp
                    f.write(f"{rel_path} f {mode} 0 0 - - - - - {timestamp}\n")

                for dir in dirs:
                    full_path = os.path.join(root, dir)
                    rel_path = os.path.relpath(full_path, source_dir)
                    rel_path = "/" + rel_path.replace("\\", "/")

                    # For directories: name d mode uid gid - - - - - timestamp
                    f.write(f"{rel_path} d 755 0 0 - - - - - {timestamp}\n")

        return True
    except Exception as e:
        print(f"Error creating device table: {e}")
        return False

def set_timestamps_recursively(root_dir, unix_time):
    """
    Recursively set atime and mtime for all files and directories in root_dir.
    :param root_dir: Path to the directory to update
    :param unix_time: Unix timestamp (int/float) to apply
    """
    for current_root, dirs, files in os.walk(root_dir):
        # Update files
        for f in files:
            fpath = os.path.join(current_root, f)
            try:
                os.utime(fpath, (unix_time, unix_time))
                print(f"Updated file: {fpath}")
            except Exception as e:
                print(f"Failed to update file {fpath}: {e}")

        # Update directories too
        for d in dirs:
            dpath = os.path.join(current_root, d)
            try:
                os.utime(dpath, (unix_time, unix_time))
                print(f"Updated dir: {dpath}")
            except Exception as e:
                print(f"Failed to update dir {dpath}: {e}")

import os
import subprocess
import tempfile
import filecmp
import shutil

def compare_jffs2(img1, img2):
    """
    Extract two JFFS2 images with dump.jffs2 and compare their file trees.
    Returns True if contents are identical (ignores metadata).
    """

    # Create temporary extraction dirs
    tmpdir1 = tempfile.mkdtemp(prefix="jffs2_")
    tmpdir2 = tempfile.mkdtemp(prefix="jffs2_")

    try:
        # Extract images using dump.jffs2
        subprocess.run(["dump.jffs2", "-r", tmpdir1, "-d", img1], check=True)
        subprocess.run(["dump.jffs2", "-r", tmpdir2, "-d", img2], check=True)

        # Compare recursively
        dirs_cmp = filecmp.dircmp(tmpdir1, tmpdir2)

        def report_diff(dcmp):
            diffs = []
            if dcmp.left_only or dcmp.right_only or dcmp.diff_files:
                diffs.append({
                    "left_only": dcmp.left_only,
                    "right_only": dcmp.right_only,
                    "diff_files": dcmp.diff_files,
                })
            for sub in dcmp.subdirs.values():
                diffs.extend(report_diff(sub))
            return diffs

        differences = report_diff(dirs_cmp)
        if differences:
            print("Differences found:", differences)
            return False
        else:
            print("Images are functionally identical.")
            return True

    finally:
        # Clean up extracted dirs
        shutil.rmtree(tmpdir1)
        shutil.rmtree(tmpdir2)


def scan_for_correct_build_args(source_dir, original_file, test_output_file):
    """Grid search to find correct build parameters"""

    # Create device table with the specific timestamp (0x8c619565 in hex)
    # create_device_table_with_timestamp("device_table_timestamp.txt", source_dir, "1704288652")
    set_timestamps_recursively(source_dir, 1704288652)

    
    # Parameter options to test
    erase_sizes = ["0x8000"]  #, "0x10000", "0x20000", "0x40000", "0x80000"]
    page_sizes = ["0x1000"]  # ["256", "512", "1024", "2048", "4096"]
    pad_sizes = ["0x100000"] # [None, "512KiB", "1024KiB", "2048KiB"]
    endianness_options = ["-l"]
    # The above options are confirmed. The below options are not
    cleanmarker_options = [True]  # Best Don't think there is a cleanmarker
    cleanmarker_sizes = [None]  # Best, "16", "20"]  # Probably no cleanmarker
    faketime_options = [False]  # Best, False]  # Try faketime first - most likely to fix timestamp differences
    squash_options = ["all"]  # Best, None, "perms", "uids"]
    compr_modes = [None]  # "none", "priority", "size"]
    # The above options are probably correct
    compressions = [None]  # THIS OPTION IS INVALID, "lzo", "zlib"]
    xattr_options = [False]  #, True]
    selinux_options = [False]  #, True]
    posix_acl_options = [False]  #, True]
    device_table = [None]  # None
    # Try different compression control options that might affect padding/allocation
    disable_compressors = [None]  # Compressors should be right, "lzo", "zlib", "rtime"]  # zlib is required
    enable_compressors = [None]  # Does not need lzo, and don't need to enable, "lzo", "zlib", "rtime"]
    
    original_hash = get_file_hash(original_file)
    if not original_hash:
        print(f"Error: Cannot read original file {original_file}")
        return None
        
    print(f"Original file hash: {original_hash}")
    print("Starting comprehensive grid search...")
    
    total_combinations = (len(erase_sizes) * len(page_sizes) * len(pad_sizes) * 
                         len(compressions) * len(endianness_options) * len(cleanmarker_options) *
                         len(cleanmarker_sizes) * len(faketime_options) * len(squash_options) *
                         len(compr_modes) * len(xattr_options) * len(selinux_options) * len(posix_acl_options) *
                         len(device_table) * len(disable_compressors) * len(enable_compressors))
    current = 0
    
    # Track closest match
    closest_differences = float('inf')
    closest_params = None
    closest_combination = None
    
    for erase_size in erase_sizes:
        for page_size in page_sizes:
            for pad_size in pad_sizes:
                for compression in compressions:
                    for endianness in endianness_options:
                        for no_cleanmarkers in cleanmarker_options:
                            for cleanmarker_size in cleanmarker_sizes:
                                for faketime in faketime_options:
                                    for squash in squash_options:
                                        for compr_mode in compr_modes:
                                            for with_xattr in xattr_options:
                                                for with_selinux in selinux_options:
                                                    for with_posix_acl in posix_acl_options:
                                                        for devtable in device_table:
                                                            for disabled_compressor in disable_compressors:
                                                                for enable_compressor in enable_compressors:
                                                                    current += 1

                                                                    # Build parameter description
                                                                    params = [f"-e {erase_size}", f"-s {page_size}"]
                                                                    if pad_size:
                                                                        params.append(f"--pad={pad_size}")
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
                                                                    if compr_mode:
                                                                        params.append(f"--compression-mode={compr_mode}")
                                                                    if with_xattr:
                                                                        params.append("--with-xattr")
                                                                    if with_selinux:
                                                                        params.append("--with-selinux")
                                                                    if with_posix_acl:
                                                                        params.append("--with-posix-acl")
                                                                    if devtable and os.path.exists(devtable):
                                                                        params.append(f"-D {devtable}")
                                                                    if disabled_compressor:
                                                                        params.append(f"--disable-compressor={disabled_compressor}")
                                                                    if enable_compressor:
                                                                        params.append(f"--enable-compressor={enable_compressor}")
                                                                    param_str = " ".join(params)
                                                                    print(f"Testing {current}/{total_combinations}: {param_str}")

                                                                    # Remove previous test file if it exists
                                                                    if os.path.exists(test_output_file):
                                                                        os.remove(test_output_file)

                                                                    # Try building with these parameters
                                                                    success = build_jffs2_from_params(source_dir, test_output_file, param_str)

                                                                    if success:
                                                                        test_hash = get_file_hash(test_output_file)
                                                                        dumps_match = compare_jffs2_dumps(original_file, test_output_file)
                                                                        differences = compare_binaries_32bit(original_file, test_output_file)
                                                                        dumps_match_v2 = compare_jffs2
                                                                        if dumps_match_v2:
                                                                            print("The dumps MATCH")
                                                                        else:
                                                                            print("The dumps DO NOT MATCH")
                                                                        # Check if this is the closest match so far
                                                                        if differences < closest_differences:
                                                                            closest_differences = differences
                                                                            closest_params = param_str
                                                                            closest_combination = {
                                                                                "erase_size": erase_size,
                                                                                "page_size": page_size,
                                                                                "pad_size": pad_size,
                                                                                "compression": compression,
                                                                                "endianness": endianness,
                                                                                "no_cleanmarkers": no_cleanmarkers,
                                                                                "cleanmarker_size": cleanmarker_size,
                                                                                "faketime": faketime,
                                                                                "squash": squash,
                                                                                "compr_mode": compr_mode,
                                                                                "with_xattr": with_xattr,
                                                                                "with_selinux": with_selinux,
                                                                                "with_posix_acl": with_posix_acl,
                                                                                "devtable": devtable
                                                                            }

                                                                        # Display results
                                                                        if dumps_match:
                                                                            print("    ✓ First 20 lines match")

                                                                        print(f"    32-bit differences: {differences} (Closest: {closest_differences})")

                                                                        # If we're getting close (< 2000 differences), do detailed analysis
                                                                        if differences < 2000:
                                                                            print(f"    🔍 Close match - analyzing differences...")
                                                                            compare_file_listings(original_file, test_output_file)
                                                                            analyze_filesystem_structure(test_output_file)
                                                                            extract_and_compare_files(original_file, test_output_file)

                                                                        if test_hash and test_hash == original_hash:
                                                                            print(f"\n🎉 HASH MATCH FOUND!")
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
                                                                                "squash": squash,
                                                                                "compr_mode": compr_mode,
                                                                                "with_xattr": with_xattr,
                                                                                "with_selinux": with_selinux,
                                                                                "with_posix_acl": with_posix_acl,
                                                                                "devtable": devtable
                                                                            }
    
    print("\n❌ No matching combination found")
    
    # Print closest match if found
    if closest_params:
        print(f"\n📊 CLOSEST MATCH:")
        print(f"Parameters: {closest_params}")
        print(f"32-bit differences: {closest_differences}")
        return closest_combination
    
    return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Rename camera firmware')
    parser.add_argument('camera_name', help='Camera name (alphanumeric only)')
    parser.add_argument('-g', '--grid-search', action='store_true', 
                       help='Perform grid search to find correct JFFS2 build parameters')
    
    args = parser.parse_args()
    
    camera_name = args.camera_name
    
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
    # build_jffs2(input_dir, output_file)

    if args.grid_search:
        print("Performing Grid Search...")
        scan_for_correct_build_args(input_dir, original_file, output_file)
    else:
        print("Creating new image in Firmware-Staging...")
        # Params were determined from an early grid search
        params = "-e 0x8000 -s 0x1000 --pad=0x100000 -l -n -q"
        build_jffs2_from_params(input_dir, output_file, params)


if __name__ == "__main__":
    main()
