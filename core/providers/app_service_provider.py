from core.events.event_system import EventSystem
from core.processors.core_processor import CoreProcessor
from core.repositories.elastic_repository import ElasticRepository
from core.repositories.postgres_repository import PostgresRepository
from core.services.migration_service import MigrationService


class AppServiceProvider:
    def __init__(self, app):
        self.app = app

    async def register(self):
        config = self.app.make('config')

        postgres_config = config.get_postgres_config()
        self.app.bind('PostgresRepository', lambda: PostgresRepository(postgres_config))

        elasticsearch_config = config.get_elasticsearch_config()
        self.app.bind('ElasticRepository', lambda: ElasticRepository(
            elasticsearch_config,
            self.app.make('PostgresRepository')
        ))

        self.app.bind('MigrationService', lambda: MigrationService(
            self.app.make('PostgresRepository'),
            "core/migrations"
        ))
        
        self.app.bind('CoreProcessor', lambda: CoreProcessor(
            self.app.make('PostgresRepository'),
            self.app.make('ElasticRepository')
        ))

    async def boot(self):
        postgres_service = self.app.make('PostgresRepository')
        await postgres_service.connect()
        
        migration_service = self.app.make('MigrationService')
        await migration_service.run_migrations_if_needed()

