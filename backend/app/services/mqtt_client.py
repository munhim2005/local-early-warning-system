import asyncio
import paho.mqtt.client as mqtt
import json
from typing import Dict, Any
from ..config import settings

class MQTTPublisher:
    def __init__(self, broker: str = None, port: int = None):
        self.broker = broker or settings.MQTT_BROKER
        self.port = port or settings.MQTT_PORT
        self.client = mqtt.Client(client_id="islamabad_ews_core", protocol=mqtt.MQTTv311)
        self.connected = False
        
    async def connect(self):
        loop = asyncio.get_event_loop()
        
        def mqtt_connect_wrapper():
            try:
                self.client.connect(self.broker, self.port, keepalive=60)
                self.client.loop_start()
                self.connected = True
                print(f"[SUCCESS] MQTT Connected to {self.broker}:{self.port}")
            except Exception as e:
                print(f"[FAILED] MQTT Connection failed: {e}")
                self.connected = False
        
        await loop.run_in_executor(None, mqtt_connect_wrapper)
        
    async def publish(self, topic: str, payload: Dict[str, Any]):
        if not self.connected:
            raise Exception("MQTT client not connected")
        
        loop = asyncio.get_event_loop()
        
        def publish_wrapper():
            result = self.client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=1
            )
            return result.wait_for_publish(timeout=5)
        
        await loop.run_in_executor(None, publish_wrapper)
        
    async def subscribe(self, topic: str, callback=None):
        if callback:
            self.client.on_message = callback
        self.client.subscribe(topic)
        
    async def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False

async def get_mqtt_publisher():
    """Get MQTT publisher safely"""
    from ..main import app
    if not hasattr(app.state, "mqtt"):
        raise RuntimeError("MQTT publisher not initialized in app.state")
    return app.state.mqtt