from flow.configuration.settings.injector import setting
from flow.util import stats
from injector import inject
from pika.adapters import twisted_connection
from twisted.internet import reactor, protocol, defer
from twisted.internet.error import ReactorNotRunning
from pika.spec import Basic

import flow.interfaces
import blist
import logging
import pika
import os

LOG = logging.getLogger(__name__)

@inject(
    connection_attempts=setting('amqp.connection_attempts'),
    hostname=setting('amqp.hostname'),
    port=setting('amqp.port'),
    retry_delay=setting('amqp.retry_delay'),
    socket_timeout=setting('amqp.socket_timeout'),
    virtual_host=setting('amqp.vhost'),
)
class AmqpConnectionParameters(object): pass

@inject(connection_params=AmqpConnectionParameters,
        prefetch_count=setting('amqp.prefetch_count'))
class AmqpBroker(flow.interfaces.IBroker):
    def __init__(self):
        self._publish_properties = pika.BasicProperties(delivery_mode=2)

        self._connection = None
        self.channel = None

        self.connect_deferred = None
        self._connect_deferred = None

        self._confirm_tags = blist.sortedlist()
        self._confirm_deferreds = {}
        self._handlers = []

        self._last_publish_tag = 0

    def register_handler(self, handler):
        self._handlers.append(handler)

    def publish(self, exchange_name, routing_key, message):
        """
        Returns a deferred that will callback once the message has been
        confirmed.  If the AMQP server rejects the message then the deferred
        will not callback (nor errback) and the program will exit.
        """
        LOG.debug("Publishing to exchange (%s) with routing_key (%s) "
                "the message (%s)", exchange_name, routing_key, message)

        confirm_deferred = defer.Deferred()
        deferred = self._connect()
        deferred.addCallback(self._publish, exchange_name, routing_key, message,
                confirm_deferred)
        return confirm_deferred

    def _publish(self, _, exchange_name, routing_key, message, confirm_deferred):
        timer = stats.create_timer('messages.publish.%s' %
                message.__class__.__name__)
        timer.start()

        encoded_message = message.encode()
        timer.split('encode')

        deferred = self.raw_publish(exchange_name, routing_key, encoded_message)
        timer.split('publish')
        timer.stop()
        deferred.chainDeferred(confirm_deferred)

    def raw_publish(self, exchange_name, routing_key, encoded_message):
        self._last_publish_tag += 1
        publish_tag = self._last_publish_tag
        LOG.debug("Publishing message (%d) to routing key (%s): %s",
                publish_tag, routing_key, encoded_message)

        self.channel.basic_publish(exchange=exchange_name,
                routing_key=routing_key, body=encoded_message,
                properties=self._publish_properties)

        deferred = defer.Deferred()
        self.add_confirm_deferred(publish_tag, deferred)
        return deferred

    def connect(self):
        # only allow one attempt to connect at a time.
        if self.connect_deferred is None:
            self.connect_deferred = defer.Deferred()
            deferred = self._connect()
            deferred.chainDeferred(self.connect_deferred)
        return self.connect_deferred

    def _connect(self):
        if self._connect_deferred is None:
            self._connect_deferred = defer.Deferred()
            LOG.debug('Connecting to AMQP')

            params = pika.ConnectionParameters(
                    host=self.connection_params.hostname,
                    port=self.connection_params.port,
                    virtual_host=self.connection_params.virtual_host)

            connection = protocol.ClientCreator(reactor,
                    twisted_connection.TwistedProtocolConnection,
                    params)

            LOG.debug('Attempting to establish connection to host: %s on port: %s',
                    params.host, params.port)
            deferred = connection.connectTCP(params.host, params.port)
            deferred.addCallback(self._on_connected)

            reactor.addSystemEventTrigger('before', 'shutdown', self.disconnect)
        else:
            LOG.debug('Already Connected to AMQP (or connection in progress)')
        return self._connect_deferred

    def _on_connected(self, connection):
        LOG.debug('Established connection to AMQP')
        connection.ready.addCallback(self._on_ready)
        self._connection = connection

    def disconnect(self):
        LOG.info("Closing AMQP connection.")
        if hasattr(self._connection, 'transport'):
            self._connection.transport.loseConnection()
        self._connection = None
        self._connect_deferred = None
        self.connect_defered = None

    @defer.inlineCallbacks
    def _on_ready(self, connection):
        LOG.debug('AMQP connection is ready.')
        self.channel = yield connection.channel()
        LOG.debug('Channel is open')

        if self.prefetch_count:
            yield self.channel.basic_qos(prefetch_count=self.prefetch_count)

        self._setup_publisher_confirms(self.channel)

        for handler in self._handlers:
            self.start_handler(handler)

        LOG.debug("Firing callbacks on the _connect deferred")
        self._connect_deferred.callback(None)
        LOG.debug("_on_ready completed.")

    @defer.inlineCallbacks
    def start_handler(self, handler):
        queue_name = handler.queue_name
        (queue, consumer_tag) = yield self.channel.basic_consume(
                queue=queue_name)
        LOG.debug('Beginning consumption on queue (%s)', queue_name)

        self._get_message_from_queue(queue, handler)

    def _setup_publisher_confirms(self, channel):
        LOG.debug('Enabling publisher confirms.')
        channel.confirm_delivery()
        channel.callbacks.add(channel.channel_number, Basic.Ack,
                self._on_publisher_confirm_ack, one_shot=False)
        channel.callbacks.add(channel.channel_number, Basic.Nack,
                self._on_publisher_confirm_nack, one_shot=False)

    def _on_publisher_confirm_ack(self, method_frame):
        publish_tag = method_frame.method.delivery_tag
        multiple = method_frame.method.multiple
        LOG.debug('Got publisher confirm for message (%d), multiple = %s',
                publish_tag, multiple)

        self._fire_confirm_deferreds(publish_tag, multiple)

    def _on_publisher_confirm_nack(self, method_frame):
        """
        This indicates very bad situations, we'll just die if this happens.
        """
        publish_tag = method_frame.method.delivery_tag
        multiple = method_frame.method.multiple
        LOG.critical('Got publisher rejection for message (%d), multiple = %s',
                publish_tag, multiple)
        os._exit(exit_codes.EXECUTE_SYSTEM_FAILURE)

    def _get_message_from_queue(self, queue, handler):
        deferred = queue.get()
        deferred.addCallbacks(self._on_get, self._on_connection_lost,
                callbackArgs=(queue, handler))

    def _on_get(self, payload, queue, handler):
        (channel, basic_deliver, properties, encoded_message) = payload

        message_class = handler.message_class
        timer = stats.create_timer("messages.receive.%s" %
                message_class.__name__)
        timer.start()

        encoded_message = message_class.decode(encoded_message)
        timer.split('decode')

        deferred = handler(encoded_message)
        timer.split('handle')

        receive_tag = basic_deliver.delivery_tag
        deferred.addCallbacks(self._ack, self._reject,
                callbackArgs=(receive_tag,),
                errbackArgs=(receive_tag,))

        self._get_message_from_queue(queue, handler)

    def _ack(self, _, receive_tag):
        LOG.debug('Acking message (%d)', receive_tag)
        self.channel.basic_ack(receive_tag)

    def _reject(self, _, receive_tag):
        LOG.debug('Rejecting message (%d)', receive_tag)
        self.channel.basic_reject(receive_tag, requeue=False)


    @staticmethod
    def _on_connection_lost(reason):
        LOG.warning("Queue on was closed (reason: %s)", reason)
        try:
            reactor.stop()
            LOG.critical('Stopped twisted reactor')
        except ReactorNotRunning:
            pass

    def _fire_confirm_deferreds(self, publish_tag, multiple):
        confirm_deferreds = self.get_confirm_deferreds(publish_tag, multiple)
        for deferred, tag in confirm_deferreds:
            deferred.callback(tag)
            self.remove_confirm_deferred(tag)

    def get_confirm_deferreds(self, publish_tag, multiple):
        if multiple:
            index = self._confirm_tags.bisect(publish_tag)
            tags = self._confirm_tags[:index]
            deferreds = [(self._confirm_deferreds[tag], tag) for tag in tags]
            return deferreds
        else:
            return [(self._confirm_deferreds[publish_tag], publish_tag)]

    def add_confirm_deferred(self, publish_tag, deferred):
        self._confirm_tags.add(publish_tag)
        self._confirm_deferreds[publish_tag] = deferred

    def remove_confirm_deferred(self, publish_tag):
        self._confirm_tags.remove(publish_tag)
        del self._confirm_deferreds[publish_tag]
