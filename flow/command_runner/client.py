import logging
from flow.command_runner.messages import CommandLineSubmitMessage

LOG = logging.getLogger(__name__)

class CommandLineClient(object):
    def __init__(self, broker=None, submit_routing_key=None):
        self.broker = broker

    def submit(self, command_line, net_key=None, response_places=None,
            **executor_options):
        message = CommandLineSubmitMessage(
                command_line=command_line,
                net_key=net_key,
                response_places=response_places
                executor_options=executor_options)

        self.broker.publish(self.submit_routing_key, message)
