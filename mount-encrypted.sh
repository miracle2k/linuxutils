#!/usr/bin/env bash
# Mount and unmounts an encrypted volume (in a toggle-fashion). This is necessary because
# at least in Karmic, the dialog provided by gnome-mount/gnome-volume-manager does not 
# allow the user to specify a keyfile.
#
# Currently makes a number of assumptions:
#    * LUKS volume with keyfile
#    * Uses cryptmount; partition needs to be configured in cmtab.
#

# TODO: Those should probably be passed as command line arguments.
# Name of the volume as defined in cmtab
cm_name="encrypted"
# Device mapper of the volume
mapper="/dev/mapper/encrypted"
# Default location of the keyfile
keyfile='/home/michael/Desktop/keyfile2'

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
    cat $keyfile | { echo ""; cryptmount -w 0 $cm_name 2>${errcapture} ;} | \
             zenity --progress --pulsate --auto-close --title "Please wait" --text "Mouting ${cm_name}..."
    if [ ${PIPESTATUS[1]} -eq 0 ]; then
        echo `cat /proc/mounts | grep "^${mapper}" | awk '{print $2}'`
        nautilus `cat /proc/mounts | grep "^${mapper}" | awk '{print $2}'`
    else
        zenity --error --text="An error occured: `cat ${errcapture}`"
    fi
fi
