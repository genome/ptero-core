from flow.commands.base import CommandBase
from flow.configuration.inject.broker import BlockingBrokerConfiguration
from flow.configuration.inject.redis_conf import RedisConfiguration
from injector import inject, Injector

import flow.interfaces
import logging

LOG = logging.getLogger(__name__)


@inject(storage=flow.interfaces.IStorage, broker=flow.interfaces.IBroker,
        injector=Injector)
class ServiceCommand(CommandBase):
    # XXX This should be removed
    @staticmethod
    def annotate_parser(parser):
        pass

    def __call__(self, parsed_arguments):
        for handler in self.handlers:
            self.broker.register_handler(handler)

        self.broker.connect_and_listen()

        return 0
