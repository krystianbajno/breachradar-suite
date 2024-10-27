import logging

from core.storage.smb_service import move_file_to_upstream_smb, remove_file_from_smb
from core.storage.minio_service import upload_file_to_minio, remove_file_from_minio

def move_file_to_upstream(filepath, filename, config):
    storage_provider = config.get('storage_provider', 'smb')
    if storage_provider.lower() == 'smb':
        return move_file_to_upstream_smb(filepath, filename, config.get_upstream_smb_config())
    elif storage_provider.lower() == 'minio':
        return upload_file_to_minio(filepath, filename, config.get_minio_config())
    else:
        logging.error(f"Unsupported storage provider: {storage_provider}")
        return None

def remove_file(storage_info, config):
    storage_provider = config.get('storage_provider', 'smb')
    if storage_provider.lower() == 'smb':
        filepath = storage_info.get('mounted_path') or storage_info.get('unc_path')
        return remove_file_from_smb(filepath)
    elif storage_provider.lower() == 'minio':
        bucket_name = storage_info.get('bucket_name')
        object_name = storage_info.get('object_name')
        return remove_file_from_minio(bucket_name, object_name, config.get_minio_config())
    else:
        logging.error(f"Unsupported storage provider: {storage_provider}")
        return None
