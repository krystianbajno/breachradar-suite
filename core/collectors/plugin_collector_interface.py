from abc import ABC, abstractmethod

from core.entities.scrap import Scrap

class PluginCollectorInterface(ABC):
    @abstractmethod
    async def collect(self):
        pass
    
    @abstractmethod
    async def postprocess(self, scrap: Scrap):
        pass
