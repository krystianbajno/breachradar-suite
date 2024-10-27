import logging
from minio import Minio
from minio.error import S3Error

def initialize_minio_client(minio_config):
    minio_endpoint = minio_config.get('endpoint', 'localhost:9000')
    access_key = minio_config.get('access_key', 'minioadmin')
    secret_key = minio_config.get('secret_key', 'minioadmin')
    secure = minio_config.get('secure', False)
    region = minio_config.get('region', 'us-east-1')
        
    client = Minio(
        minio_endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        region=region
    )
    return client

def upload_file_to_minio(filepath, filename, minio_config):
    try:
        client = initialize_minio_client(minio_config)
        bucket_name = minio_config.get('bucket_name', 'scrapes')
        region = minio_config.get('region', 'us-east-1')
        
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name, location=region)

        client.fput_object(bucket_name, filename, filepath)
        logging.info(f"Uploaded file {filepath} to MinIO bucket {bucket_name} as {filename}.")
        return {"bucket_name": bucket_name, "object_name": filename}
    except S3Error as e:
        logging.error(f"Failed to upload file {filepath} to MinIO: {e}")
        raise e
        return None
    
def download_file_from_minio(bucket_name, object_name, dest_path, minio_config):
    try:
        client = initialize_minio_client(minio_config)
        client.fget_object(bucket_name, object_name, dest_path)
        logging.info(f"Downloaded file {object_name} from MinIO bucket {bucket_name} to {dest_path}.")
    except S3Error as e:
        logging.error(f"Failed to download file {object_name} from MinIO: {e}")

def remove_file_from_minio(bucket_name, object_name, minio_config):
    try:
        client = initialize_minio_client(minio_config)
        client.remove_object(bucket_name, object_name)
        logging.info(f"Removed file {object_name} from MinIO bucket {bucket_name}.")
    except S3Error as e:
        logging.error(f"Failed to remove file {object_name} from MinIO: {e}")
