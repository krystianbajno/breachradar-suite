import logging
import os

from dotenv import load_dotenv
import yaml

class Config:
    def __init__(self, env_file='.env', config_file='config.yaml'):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)

        load_dotenv(env_file)
        self.config_data = self._load_config_file(config_file)
        self._override_with_env_variables()

    def _load_config_file(self, config_file):
        if not os.path.exists(config_file):
            self.logger.warning(
                f"Config file {config_file} not found, using environment variables only."
            )
            return {}

        try:
            with open(config_file, 'r') as file:
                self.logger.info(f"Loading config from {config_file}")
                return yaml.safe_load(file) or {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML config: {e}")
            return {}
        
    def _override_with_env_variables(self):
        for key, value in os.environ.items():
            if '__' in key:
                keys = key.lower().replace('__', '.').split('.')
                config_section = self.config_data

                for subkey in keys[:-1]:
                    if subkey.isdigit():
                        subkey = int(subkey)
                        if not isinstance(config_section, list):
                            config_section = []
                            self.config_data[keys[0]] = config_section
                        while len(config_section) <= subkey:
                            config_section.append({})
                        config_section = config_section[subkey]
                    else:
                        config_section = config_section.setdefault(subkey, {})

                if keys[-1].isdigit():
                    index = int(keys[-1])
                    if not isinstance(config_section, list):
                        config_section = []
                    while len(config_section) <= index:
                        config_section.append({})
                    config_section[index] = value
                else:
                    config_section[keys[-1]] = value
            else:
                self.config_data[key.lower()] = value

    def get(self, key, default=None):
        keys = key.split('.')
        config_value = self.config_data
        try:
            for k in keys:
                config_value = config_value[k]
            return config_value
        except KeyError:
            self.logger.warning(
                f"Key {key} not found in config, using default {default}"
            )
            return default

    def set(self, key, value):
        keys = key.split('.')
        config_section = self.config_data
        for k in keys[:-1]:
            config_section = config_section.setdefault(k, {})
        config_section[keys[-1]] = value

    def get_postgres_config(self):
        return {
            "database": self.get('postgres.database', 'cti_breach_hunter'),
            "user": self.get('postgres.user', 'cti_user'),
            "password": self.get('postgres.password', 'cti_password'),
            "host": self.get('postgres.host', 'localhost'),
            "port": self.get('postgres.port', '5432'),
        }

    def get_elasticsearch_config(self):
        return {
            "host": self.get('elasticsearch.host', 'localhost'),
            "port": int(self.get('elasticsearch.port', 9200)),
            "scheme": self.get('elasticsearch.scheme', 'http'),
            "user": self.get('elasticsearch.user', 'elastic'),
            "password": self.get('elasticsearch.password', 'password'),
        }

    def get_kafka_config(self):
        return {
            "bootstrap_servers": self.get('kafka.bootstrap_servers', 'localhost:9092'),
            "topic": self.get('kafka.topic', 'scrap_topic'),
            "notification_topic": self.get('kafka.processed_topic', 'processed_topic')
        }
        
    def get_smb_servers_config(self):
        smb_servers = self.config_data.get("smb_servers", [])

        if not smb_servers:
            self.logger.warning("No SMB servers configured.")
            return smb_servers
        
        formatted_smb_servers = []
        for index, smb_server in enumerate(smb_servers):
            formatted_smb_servers.append({
                "enabled": smb_server.get("enabled", False),
                "share": smb_server.get("share", f'//smb-server{index}/scraps'),
                "username": smb_server.get("username", f'smbuser{index}'),
                "password": smb_server.get("password", f'smbpassword{index}'),
                "anonymous": smb_server.get("anonymous", False),
                "mount_point": smb_server.get("mount_point", f'/mnt/smb_scraps{index}'),
            })

        return formatted_smb_servers

    def get_upstream_smb_config(self):
            config = {
                "share": self.get('upstream_smb.share', '//upstream-server/scraps'),
                "username": self.get('upstream_smb.username', 'upstream_user'),
                "password": self.get('upstream_smb.password', 'upstream_password'),
                "mount_point": self.get('upstream_smb.mount_point', '/mnt/upstream_scraps'),
                "anonymous": self.get('upstream_smb.anonymous', False),
            }
                        
            return config
        
    def get_minio_config(self):
        return {
            "endpoint": self.get('minio.endpoint', 'localhost:9000'),
            "access_key": self.get('minio.access_key', 'minioadmin'),
            "secret_key": self.get('minio.secret_key', 'minioadmin'),
            "secure": self.get('minio.secure', False),
            "bucket_name": self.get('minio.bucket_name', 'scrapes'),
            "region": self.get('minio.region', 'us-east-1'),
        }