#!/bin/sh
PING_FAILED=0

check_camera_run(){
	if ps  | grep ucamera | grep -v grep > /dev/null; then
	sleep 1
	else
	let PING_FAILED++
	fi

}
#insmod /system/lib/modules/videobuf2-vmalloc.ko
#insmod /system/lib/modules/libcomposite.ko
#insmod /system/lib/modules/usbcamera.ko

cd /system/bin/
#anticopy ucamera
sleep 0.1
ucamera &

#insmod /system/lib/modules/audio.ko
#insmod /system/lib/modules/avpu.ko
#insmod /system/lib/modules/tx-isp-t31.ko isp_clk=200000000
#insmod /system/lib/modules/sensor_gc2083_t31.ko data_interface=1
sleep 0.1
killall -USR1 ucamera
#hid_update &

# sleep 3

while true
do	
	check_camera_run
	sleep 1
	if [ $PING_FAILED -gt 2 ]; then
	    reboot
	fi
done
# adbd &
