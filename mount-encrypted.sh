#!/usr/bin/env bash
# Mount and unmounts an encrypted volume (in a toggle-fashion). This is necessary because
# at least in Karmic, the dialog provided by gnome-mount/gnome-volume-manager does not 
# allow the user to specify a keyfile (see https://bugs.launchpad.net/gnome-mount/+bug/133520)
#
# Currently makes a number of assumptions:
#    * LUKS volume with keyfile
#    * Uses cryptmount; partition needs to be configured in cmtab.
#

usage()
{
cat << EOF
usage: $0 CRYPT_MOUNT_NAME MAPPER KEYFILE

Will mount or unmount the volume CRYPT_MOUNT_NAME configured in
cryptmount's cmtab using the contents of KEYFILE as a password.
MAPPER is used to check if the volumen is already mounted.
EOF
}


# Name of the volume as defined in cmtab
cm_name=$1
# Device mapper of the volume
mapper=$2
# Default location of the keyfile
keyfile=$3


if [ ! $1 ] || [ ! $2 ] || [ ! $3 ]
then
    usage
  	exit 1
fi

if mount | grep "^${mapper} on" > /dev/null
then
    echo "Umounting..."
    # Empty echo to make zentiy progress bar pulsate; artificial delay, or it won't be much to quick.
    { echo ""; cryptmount -u $cm_name; sleep 2 ;} | zenity --progress --pulsate --auto-close --title "Please wait" --text "Umounting..."
else    
    echo "Mounting..."
    if [ ! -f $keyfile ]
    then
        keyfile=`zenity --file-selection --title="$keyfile not found; select one:"`
        if [ ! $? -eq 0 ]; then 
            print "No keyfile, halting."
            exit 1;  
        fi
    fi

    # The empty "echo" makes zenity "pulsate" work, since cryptmount doesn't write to stdout.
    # Also, the challenge here is to both get the error code, as well as capture stderr. This
    # is hard because we need to get the code of a subcommand of the pipe (PIPESTATUS), but 
    # variable assignment is apparently a command of it's own and clears out PIPESTATUS.
    # For now, we use a temporary file.
    # TODO: Maybe there is a better solution. Some ideas may be here:
    # http://ask.metafilter.com/76984/Pipe-command-output-but-keep-the-error-code
    errcapture="/tmp/cryptmount.stderr.${cm_name}"
    { echo ""; cryptmount -w 5 $cm_name 2>${errcapture} 5< $keyfile ;} | \
             zenity --progress --pulsate --auto-close --title "Please wait" --text "Mouting ${cm_name}..."
    if [ ${PIPESTATUS[1]} -eq 0 ]; then
        nautilus `cat /proc/mounts | grep "^${mapper}" | awk '{print $2}'`
    else
        zenity --error --text="An error occured: `cat ${errcapture}`"
    fi
fi
