import asyncio
import logging
import json
import os
import platform

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from core.entities.scrap import Scrap
from core.repositories.postgres_repository import PostgresRepository
from core.storage.storage_service import remove_file

class ProcessingSystem:
    def __init__(self, app, processors, repository: PostgresRepository):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.processors = processors
        self.repository = repository
        self.kafka_config = app.configuration.get_kafka_config()
        self.processing_scraps = set()
        self.max_concurrent_scraps = 100

        self.consumer = AIOKafkaConsumer(
            self.kafka_config['topic'],
            bootstrap_servers=self.kafka_config['bootstrap_servers'],
            group_id="processing_group",
            enable_auto_commit=False,
            max_poll_records=100
        )
        
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_config['bootstrap_servers']
        )

        self.semaphore = asyncio.Semaphore(self.max_concurrent_scraps)

    async def run(self):
        await self.consumer.start()
        await self.producer.start()

        try:
            while True:
                msgs = await self.consumer.getmany(timeout_ms=1000)
                tasks = []
                for topic_partition, batch in msgs.items():
                    for msg in batch:
                        scrap_data = json.loads(msg.value.decode('utf-8'))
                        scrap = Scrap.from_json(scrap_data['scrap_data'])

                        if scrap.hash in self.processing_scraps:
                            continue

                        self.processing_scraps.add(scrap.hash)
                        
                        storage_info = scrap_data.get('storage_info')

                        file_path = self.retrieve_file(storage_info)

                        scrap.file_path = file_path
                        
                        tasks.append(self.process_with_semaphore(scrap, storage_info))

                await asyncio.gather(*tasks)
                await self.consumer.commit()
        finally:
            await self.consumer.stop()
            await self.producer.stop()

    def retrieve_file(self, storage_info):
        storage_provider = self.app.configuration.get('storage_provider', 'smb')
        if storage_provider.lower() == 'smb':
            if platform.system() == 'Windows':
                return storage_info.get('unc_path')
            else:
                return storage_info.get('mounted_path')
        elif storage_provider.lower() == 'minio':
            bucket_name = storage_info.get('bucket_name')
            object_name = storage_info.get('object_name')
            temp_file_path = os.path.join('/tmp', object_name)
            from core.storage.minio_service import download_file_from_minio
            download_file_from_minio(bucket_name, object_name, temp_file_path, self.app.configuration.get_minio_config())
            return temp_file_path
        else:
            self.logger.error(f"Unsupported storage provider: {storage_provider}")
            return None

    async def process_with_semaphore(self, scrap, storage_info):
        async with self.semaphore:
            await self.process_scrap(scrap)
            self.processing_scraps.remove(scrap.hash)
            remove_file(storage_info, self.app.configuration)

    async def process_scrap(self, scrap: Scrap):
        applicable_processors = [p for p in self.processors if p.can_process(scrap)]
        tasks = [processor.process(scrap) for processor in applicable_processors]
        await asyncio.gather(*tasks)

        await self.notify_producer_scrap_processed(scrap)

    async def notify_producer_scrap_processed(self, scrap: Scrap):
        try:
            message = {
                "scrap_id": scrap.id,
                "hash": scrap.hash,
                "status": "PROCESSED"
            }
            message_data = json.dumps(message).encode('utf-8')
            await self.producer.send_and_wait(self.kafka_config['notification_topic'], message_data)
            self.logger.info(f"Notified producer that scrap {scrap.id} has been processed.")
        except Exception as e:
            self.logger.exception(f"Error notifying producer for scrap {scrap.id}: {e}")
