import logging
import os
from datetime import datetime
from core.collectors.plugin_collector_interface import PluginCollectorInterface
from core.entities.scrap import Scrap
from core.repositories.postgres_repository import PostgresRepository
from plugins.local_plugin.services.local_service import LocalService
from rust_bindings import calculate_file_hash

class LocalCollector(PluginCollectorInterface):
    def __init__(self, app):
        self.logger = logging.getLogger(__name__)
        self.local_service: LocalService = app.make('LocalService')
        self.repository: PostgresRepository = app.make('PostgresRepository')
        
    async def postprocess(self, scrap):
        self.local_service.move_file_to_processed(scrap.file_path)
        
    async def collect(self):
        scrape_files = await self.local_service.fetch_scrape_files()
        new_scraps = []
        if not scrape_files:
            self.logger.info("No new files to process.")
            return new_scraps

        for file_info in scrape_files:
            filename = file_info['filename']
            file_path = file_info['file_path']
            
            if filename in await self.repository.get_processing_filenames():
                return

            try:
                file_hash = calculate_file_hash(file_path)
            except Exception as e:
                self.logger.exception(f"Error processing file {file_path}: {e}")
                continue

            occurrence_time = self._get_file_modification_time(file_path)
            creation_time = self._get_file_creation_time(file_path)

            scrap = self.create_scrap(
                file_hash,
                filename,
                file_path,
                creation_time,
                occurrence_time
            )

            new_scraps.append(scrap)
                        
        return new_scraps

    def create_scrap(self, file_hash, filename, file_path, creation_time, occurrence_time):
        return Scrap(
            hash=file_hash,
            source='local',
            filename=filename,
            file_path=file_path,
            timestamp=creation_time,
            occurrence_time=occurrence_time
        )

    def _get_file_creation_time(self, file_path):
        try:
            return datetime.fromtimestamp(os.path.getctime(file_path))
        except Exception:
            return None

    def _get_file_modification_time(self, file_path):
        try:
            return datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception:
            return None
