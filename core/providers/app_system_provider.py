from core.events.event_system import EventSystem
from core.plugins.plugin_loader import PluginLoader
from core.storage.smb_service import mount_downstream_smb, mount_upstream_smb
from core.systems.collector_system import CollectorSystem
from core.systems.processing_system import ProcessingSystem


class AppSystemProvider:
    def __init__(self, app):
        self.app = app
        self.plugin_loader = PluginLoader(app)

    async def register(self):
        self.app.bind('EventSystem', lambda: EventSystem())

    async def boot(self):
        mount_upstream_smb(self.app.configuration)
        mount_downstream_smb(self.app.configuration)
        
        self.plugin_loader.load_plugins()

        collectors = self.plugin_loader.get_plugins('collector')
        processors = self.plugin_loader.get_plugins('processor')

        collector_system = CollectorSystem(self.app, collectors)
        
        postgres_repository = self.app.make('PostgresRepository')
        
        processing_system = ProcessingSystem(
            self.app,
            processors,
            postgres_repository
        )

        self.app.add_system(lambda app: collector_system)
        self.app.add_system(lambda app: processing_system)


