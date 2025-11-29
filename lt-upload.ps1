# Move liedtekst PDF's to Proton Drive cloud using RCLONE.


# ***  Prerequisites  ***
# - download and unzip rclone (https://rclone.org) to c:\program files\<rclonefolder>
# - add path to PATH (c:\program files\<rclonefolder>)
# - configure rclone from cmdline: rclone config
#     This leads you through connecting to the PDrive (password is stored, securely)
# - first time connecting requires a 2FA token (I guess it's valid for 1 hour or even more)
#     └─ for this use the 'dir' cmd (see below): 
#           `rclone lsd ProtonDrive:` (be sure to include the :)
# ***  -------------  ***



# authenticate and list base directory in Drive
# rclone lsd ProtonDrive: --protondrive-2fa=433461    # OK


#   P R O D U C T I O N:    move all pdf's to PDrive    (use --dry-run to test)
rclone move '../_dist' ProtonDrive:'Creatie/Muziek/Uploads/' --progress --filter-from lt-upload-filter.txt 


#   E X A M P L E:   move single file to PDrive
# rclone moveto 'bla (24) (met gitaargrepen).pdf' ProtonDrive:'Creatie/Muziek/Uploads/bla (24) (met gitaargrepen).pdf'


# docs:
# https://rclone.org/commands/rclone_moveto/