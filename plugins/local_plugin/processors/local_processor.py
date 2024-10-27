import asyncio
import logging
from core.entities.scrap import Scrap
from core.processors.plugin_processor_interface import PluginProcessorInterface
from plugins.local_plugin.services.local_service import LocalService
from core.processors.core_processor import CoreProcessor

class LocalProcessor(PluginProcessorInterface):
    def __init__(self, app):
        self.logger = logging.getLogger(__name__)
        self.local_service: LocalService = app.make('LocalService')
        self.core_processor: CoreProcessor = app.make('CoreProcessor')

    def can_process(self, scrap: Scrap) -> bool:
        return scrap.source == 'local'

    async def process(self, scrap: Scrap):
        self.logger.info(f"Processing scrap: {scrap.filename}")

        await self.core_processor.process_scrap(scrap)

        self.logger.info(f"File {scrap.filename} processed.")
