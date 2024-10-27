import logging
import shutil
import subprocess
import os
import platform

def is_mounted(mount_point):
    system = platform.system()

    check_mount_commands = {
        'Linux': lambda: subprocess.run(['mountpoint', '-q', mount_point], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0,
        'Darwin': lambda: mount_point in subprocess.run(['df', '-h'], stdout=subprocess.PIPE).stdout.decode(),
        'Windows': lambda: mount_point.lower() in subprocess.run(['net', 'use'], stdout=subprocess.PIPE).stdout.decode().lower(),
    }

    if system in check_mount_commands:
        return check_mount_commands[system]()
    else:
        raise NotImplementedError(f"Mount check not supported on {system}")

def mount_downstream_smb(config):
    logging.info("Mounting downstream SMB servers...")
    mount_smb_servers(config.get_smb_servers_config())

def mount_upstream_smb(config):
    logging.info("Mounting upstream SMB server...")
    mount_smb_servers([config.get_upstream_smb_config()])

def mount_smb_servers(smb_servers):
    if not smb_servers:
        logging.warning("No SMB servers configured.")
        return

    system = platform.system()
    logging.info(f"Detected platform: {system}")

    mount_commands = {
        'Linux': lambda share, mount_point, username, password, anonymous: [
            'mount', '-t', 'cifs', share, mount_point, '-o', 
            'guest' if anonymous else f'username={username},password={password}'
        ],
        'Darwin': lambda share, mount_point, username, password, anonymous: [
            'mount_smbfs', f'//{username}:{password}@{share}', f'{mount_point}'
        ],
        'Windows': lambda share, mount_point, username, password, anonymous: [
            'net', 'use', mount_point, share if anonymous else f'/user:{username}', password
        ],
    }

    for smb_server in smb_servers:
        share = smb_server.get('share')
        username = smb_server.get('username', '')
        password = smb_server.get('password', '')
        mount_point = smb_server.get('mount_point')
        anonymous = smb_server.get('anonymous', False)
        
        try:
            os.makedirs(mount_point, exist_ok=True)
        except:
            continue

        if is_mounted(mount_point):
            logging.info(f"Mount point {mount_point} is already mounted.")
            continue

        try:
            if system in mount_commands:
                command = mount_commands[system](share, mount_point, username, password, anonymous)
                logging.debug(f"Mount command: {' '.join(command)}")
                subprocess.run(command, check=True)
                logging.info(f"Mounted SMB share {share} at {mount_point}.")
            else:
                raise NotImplementedError(f"Mounting not supported on {system}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to mount SMB share {share} at {mount_point}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while mounting SMB share {share}: {e}")

def move_file_to_upstream_smb(filepath, filename, upstream_smb_config):
    try:
        smb_mount_point = upstream_smb_config.get('mount_point')
        smb_share_path = upstream_smb_config.get('share_path')

        mounted_path = os.path.join(smb_mount_point, filename)
        unc_path = f"{smb_share_path}\\{filename}"

        os.makedirs(smb_mount_point, exist_ok=True)
        shutil.move(filepath, mounted_path)

        logging.info(f"Moved file {filepath} to {mounted_path} (UNC path: {unc_path})")
        return {"mounted_path": mounted_path, "unc_path": unc_path}
    except Exception as e:
        logging.error(f"Failed to move file {filepath} to SMB upstream: {e}")
        return None
    
def remove_file_from_smb(filepath):
    try:
        os.remove(filepath)
        logging.info(f"File {filepath} deleted from SMB share.")
    except Exception as e:
        logging.error(f"Error deleting file {filepath}: {e}")
