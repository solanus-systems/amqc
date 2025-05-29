from unittest import TestCase

from amqc.client import MQTTClient, config


class TestClient(TestCase):
    def test_client_initialization(self):
        client = MQTTClient(config)
        self.assertIsInstance(client, MQTTClient)
