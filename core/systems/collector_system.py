import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from core.entities.scrap import Scrap
from core.storage.storage_service import move_file_to_upstream

class CollectorSystem:
    def __init__(self, app, collectors):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.collectors = collectors
        self.kafka_config = app.configuration.get_kafka_config()
        self.loop = asyncio.get_event_loop()

        self.producer = AIOKafkaProducer(
            loop=self.loop,
            bootstrap_servers=self.kafka_config['bootstrap_servers']
        )

        self.notification_consumer = AIOKafkaConsumer(
            self.kafka_config['notification_topic'],
            loop=self.loop,
            bootstrap_servers=self.kafka_config['bootstrap_servers'],
            group_id="notification_group"
        )

        self.topic = self.kafka_config['topic']
        self.processing_scraps = set()
        self.max_concurrent_collectors = 10
        self.semaphore = asyncio.Semaphore(self.max_concurrent_collectors)

    async def run(self):
        await self.producer.start()
        await self.notification_consumer.start()

        try:
            await asyncio.gather(
                self._run_collectors(),
                self._consume_notifications()
            )
        finally:
            await self.producer.stop()
            await self.notification_consumer.stop()

    async def _run_collectors(self):
        tasks = [self._run_collector(collector) for collector in self.collectors]
        await asyncio.gather(*tasks)

    async def _run_collector(self, collector):
        while True:
            await self._collect_scraps(collector)
            await asyncio.sleep(1)

    async def _collect_scraps(self, collector):
        async with self.semaphore:
            try:
                scraps = await collector.collect()
                if not scraps:
                    return

                for scrap in scraps:
                    if scrap.hash in self.processing_scraps:
                        continue

                    self.processing_scraps.add(scrap.hash)
                    storage_info = move_file_to_upstream(scrap.file_path, scrap.filename, self.app.configuration)

                    if storage_info:
                        await self._handle_new_scrap(scrap, storage_info)
                        
                await collector.postprocess(scrap)

            except Exception as e:
                self.logger.exception(f"Error running collector {collector}: {e}")

    async def _handle_new_scrap(self, scrap: Scrap, storage_info: dict):
        try:
            await self._publish_scrap(scrap, storage_info)
        except Exception as e:
            self.logger.exception(f"Error handling new scrap {scrap.filename}: {e}")
        finally:
            self.processing_scraps.remove(scrap.hash)

    async def _publish_scrap(self, scrap: Scrap, storage_info: dict):
        try:
            message = {
                "scrap_data": scrap.to_json(),
                "storage_info": storage_info
            }

            await self.producer.send_and_wait(self.topic, json.dumps(message).encode('utf-8'))
            self.logger.info(f"Published scrap {scrap.filename} to Kafka.")
        except Exception as e:
            self.logger.exception(f"Error publishing scrap {scrap.filename} to Kafka: {e}")

    async def _consume_notifications(self):
        try:
            async for msg in self.notification_consumer:
                notification = json.loads(msg.value.decode('utf-8'))
                scrap_hash = notification.get("hash")
                if notification.get("status") == "PROCESSED" and scrap_hash in self.processing_scraps:
                    self.processing_scraps.remove(scrap_hash)
                    self.logger.info(f"Processed and removed scrap {scrap_hash}")
        except Exception as e:
            self.logger.exception(f"Error consuming notification message: {e}")
