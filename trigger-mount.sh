#!/usr/bin/env bash

# Use udev to run this script when you insert your usb key. The usb 
# key is expected to contain the key needed to unlock an encrypted 
# partition on your system, which this script will automatically do.
#
# In addition to the environment provided by udev, this script 
# expects the cryptmount name of the encrypted partition that  should
# be unlocked, as configured in cmtab, as an argument.
# 
# We are opting to use cryptmount rather than cryptsetup to mount 
# the disk. While this introduces a dependency on a configured 
# cmtab, we do on occasion need to do manual mounts as well, for 
# which we prefer cryptmount (unlocking + mounting just takes to 
# much time for data accessed  reasonably often), and when combining
# cryptmount + automatic cryptsetup mounts we are risking to run
# into conflicts, multiple mappers or mounts etc.
#
# Thus, you need to define the partition in cmtab for this to work,
# and you need to set the "nofsck" flag (see 
# http://sourceforge.net/tracker/index.php?func=detail&aid=2937347&group_id=154099&atid=790423)
#

# Run all in background, so to not hold up udev.
{

to_unlock=$1
if [ ! $to_unlock ]; then
    echo "Needs name of encrypted partition" >&2
    exit 1
fi

# In addition, we use some variables from the udev environment
if [ ! $ACTION ] || [ ! $DEVNAME ]; then
    echo "udev environment is incomplete" >&2
    exit 1
fi

lockfile=/var/lock/automount-${to_unlock}.lock

# Ensure we don't start multiple mount/unmount attempts at 
# the same time - a user might remove his stick pretty quickly.
lockfile-create -r 0 $lockfile
if [ ! $? -eq 0 ]; then
    echo "Got action $ACTION, but still busy (lockfile exists)" >&2 
    exit 2
else
    trap "lockfile-remove $lockfile; exit" INT TERM EXIT
fi


# Needed to make zenity work in udev context 
export DISPLAY=:0.0


if [ "$ACTION" = "add" ]; then  
    # Get the key   
    key=$(dd ibs=1c obs=1c skip=42 count=256 if=$DEVNAME)
    if [ ! $? -eq 0 ]; then exit; fi
    # Decrypt and mount
    echo $key | cryptmount -w 0 $to_unlock    
    if [ $? -eq 0 ]; then
        zenity --notification --window-icon="info" --text="Mounted!" --timeout 5
    else
        exit $?
    fi

elif [ "$ACTION" = "remove" ]; then     
    # Unmount the volume
    cryptmount -u $to_unlock
    if [ $? -eq 0 ]; then
        zenity --notification --window-icon="info" --text="Unmounted!" --timeout 5
    else
        exit $?
    fi    
fi

lockfile-remove $lockfile
trap - INT TERM EXIT


} &