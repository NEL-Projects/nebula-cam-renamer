# Nebula Camera Renaming Utility

---

## Warning Before Use
This is a tool for renaming the Creality Nebula Camera.

This tool has the potential to brick your camera and/or void your warranty.

The authors have no relation to the manufacturer of the camera, and are not responsible for anything this tool does to 
any of your devices.

---

## How to use this tool

### Install Dependencies

Ensure you have Windows Subsystem for Linux (WSL) and python 3.13+ installed on your Windows system.

In A Windows Subsystem for Linux terminal install mtd-utils if it is not already installed:

```
sudo apt update
sudo apt install mtd-utils
```

### Rename the Camera
Connect *only one camera* then run:
```
python rename_camera.py NEWCAMERANAMEHERE
```

`NEWCAMERANAMEHERE` should only have characters in A-Z or 0-9.

USBDownloadTool should then open. Press *FW Version*, you should see the line with the current time followed by 
`UVC-UnionImage-CCX2F3298-240103V020`. If you don't this means that the system cannot find your camera.

After seeing that message press *Upgrade Firmware*. The entire process should take about a minute. Do not disconnect 
the camera until you see the message `Upgrade done, reboot now.`

You may need to uninstall the camera in device manager and disconnect it before you see the new name.

### Further Usage (Advanced)
**Grid Search:** A grid search can also be performed if trying to find new image parameters with the `-g` flag. You will
need to uncomment the relevant lines.

**Increase Maximum Name Length:** You can specify the `-l` flag to allow names for the camera to be more than 9 
characters. This hasn't been tested, hence why this limitation is there by default.

```
usage: rename_camera.py [-h] [-g] [-l] camera_name

Rename camera firmware

positional arguments:
  camera_name          Camera name (alphanumeric only)

options:
  -h, --help           show this help message and exit
  -g, --grid-search    Perform grid search to find correct JFFS2 build parameters
  -l, --length-ignore  Allow a camera name to be more than 9 characters (NOT RECOMMENDED)
```
