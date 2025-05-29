from unittest import TestCase

from amqc.client import MQTTClient, client_id, config


class TestClient(TestCase):
    def test_client_id(self):
        cid = client_id()
        self.assertIsInstance(cid, bytes)
        self.assertEqual(len(cid), 12)

    def test_client_initialization(self):
        client = MQTTClient(config)
        self.assertIsInstance(client, MQTTClient)
