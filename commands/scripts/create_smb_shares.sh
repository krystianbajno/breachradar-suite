#!/bin/bash

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Use sudo to run it."
    exit 1
fi

OS=$(uname)

create_shared_directory() {
    local dir_path=$1
    echo "Creating shared directory: $dir_path"
    mkdir -p "$dir_path"
    chmod 777 "$dir_path"
}

add_samba_share() {
    local share_name=$1
    local path=$2
    echo "Adding SMB share to Samba configuration."

    cat >> /etc/samba/smb.conf <<EOL

[$share_name]
   path = $path
   available = yes
   valid users = nobody
   read only = no
   browsable = yes
   public = yes
   writable = yes
EOL

    echo "Restarting Samba services..."
    systemctl restart smbd
    systemctl restart nmbd
}

add_macos_share() {
    local share_name=$1
    local path=$2
    echo "Adding SMB share to macOS configuration."

    cat >> /etc/smb.conf <<EOL

[$share_name]
   path = $path
   available = yes
   public = yes
   writable = yes
   guest ok = yes
EOL

    echo "Restarting SMB services..."
    sudo launchctl unload /System/Library/LaunchDaemons/com.apple.smbd.plist
    sudo launchctl load /System/Library/LaunchDaemons/com.apple.smbd.plist
}

create_smb_share() {
    local share_name=$1
    local path=$2

    create_shared_directory "$path"

    if [ "$OS" == "Darwin" ]; then
        add_macos_share "$share_name" "$path"
    elif [ "$OS" == "Linux" ]; then
        add_samba_share "$share_name" "$path"
    else
        echo "Unsupported operating system: $OS"
        exit 1
    fi
}

read -p "Enter the name of the SMB share: " SHARE_NAME
read -p "Enter the path to the directory you want to share: " SHARE_PATH

create_smb_share "$SHARE_NAME" "$SHARE_PATH"

echo "SMB share $SHARE_NAME has been created and configured."
