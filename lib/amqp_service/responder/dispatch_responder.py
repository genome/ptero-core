import json
import logging

from . import base

LOG = logging.getLogger(__name__)


class DispatchResponder(base.Responder):
    def __init__(self, dispatcher, *args, **kwargs):
        self.dispatcher = dispatcher

        base.Responder.__init__(self, *args, **kwargs)

    def on_message(self, channel, basic_deliver, properties, input_data):
        LOG.debug("Got input_data %s", input_data)

        command = _get_required(input_data, 'command')
        return_identifier = _get_required(input_data, 'return_identifier')
        success_routing_key = _get_required(input_data, 'success_routing_key')
        failure_routing_key = _get_required(input_data, 'failure_routing_key')

        arguments = input_data.get('arguments', [])
        wrapper = input_data.get('wrapper')
        wrapper_arguments = input_data.get('wrapper_arguments', [])
        dispatcher_options = input_data.get('dispatcher_options', {})

        success, dispatch_result = self.dispatcher.launch_job(
                command, arguments=arguments,
                wrapper=wrapper, wrapper_arguments=wrapper_arguments,
                **dispatcher_options)

        if success:
            routing_key = success_routing_key
        else:
            routing_key = failure_routing_key

        result = {'return_identifier': return_identifier,
                  'dispatch_result': dispatch_result}

        return routing_key, result

def _get_required(input_data, name):
    try:
        return input_data[name]
    except KeyError:
        LOG.error("required message key '%s' not specified", name)
        raise