# /edge-node/pc_alert_node.py

#!/usr/bin/env python3
"""
Local Emergency Warning System - Edge Alert Node (PC Version)
This version works WITHOUT Raspberry Pi GPIO pins
Uses standard audio output instead of PA speakers
"""

import asyncio
import paho.mqtt.client as mqtt
import pygame
import json
import time
import os
from datetime import datetime
from typing import Dict, Any
import threading

# Configuration
NODE_ID = "PC_SIMULATION_NODE_01"
LOCATION = "Simulation Test Station (PC)"

MQTT_BROKER = "localhost"  # Change if using Docker
MQTT_PORT = 1883
MQTT_TOPIC_ALERT = "islamabad/alert/critical"
MQTT_TOPIC_STATUS = "islamabad/node/status"

# Audio Files (you'll need to create simple .mp3 or .wav files)
AUDIO_FILES = {
    "default": "audio/alert_default.wav",
    "earthquake": "./audio/alert_earthquake.wav",
    "flood": "./audio/alert_flood.wav",
    "fire": "./audio/alert_fire.wav",
    "test": "./audio/alert_default.wav"
}

class PCAlertNode:
    def __init__(self):
        self.node_id = NODE_ID
        self.location = LOCATION
        self.alert_queue = asyncio.Queue()
        self.is_playing = False
        self.online = True
        
        # Initialize audio
        self._setup_audio()
        
        # Initialize MQTT
        self.client = mqtt.Client(client_id=self.node_id, protocol=mqtt.MQTTv311)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        print(f"🖥️  PC Alert Node Starting...")
        print(f"📍 Location: {self.location}")
    
    def _setup_audio(self):
        """Initialize Pygame mixer for audio playback"""
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.music.set_volume(1)  # Lower volume for PC speakers
            self.audio_available = True
            print("✅ Audio initialized")
        except Exception as e:
            print(f"⚠️  Audio init failed: {e}")
            self.audio_available = False
    
    def _on_connect(self, client, userdata, flags, rc):
        print(f"✅ MQTT Connected with result code {rc}")
        client.subscribe(MQTT_TOPIC_ALERT)
        self._publish_status()
    
    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        print(f"\n📩 Received alert on {msg.topic}:")
        print(f"   {payload}\n")
        
        try:
            data = json.loads(payload)
            
            # Check if simulation mode
            if data.get("SIMULATION") or data.get("audio_override") == "TEST_MODE_ACTIVE":
                print("🧪 SIMULATION MODE DETECTED")
                alert_type = "test"
            else:
                alert_type = data.get("type", "default")
            
            self.alert_queue.put_nowait({
                "type": alert_type,
                "priority": {"critical": 0, "high": 1, "medium": 2}.get(
                    data.get("severity", "low"), 3
                ),
                "data": data
            })
            
            # Log threat info
            if data.get("magnitude"):
                print(f"   🌊 Magnitude: {data['magnitude']}")
            if data.get("severity"):
                print(f"   ⚠️  Severity: {data['severity']}")
                
        except json.JSONDecodeError:
            print("❌ Failed to decode message")
    
    def _on_disconnect(self, client, userdata, rc):
        print(f"❌ MQTT Disconnected with code {rc}")
        self.online = False
    
    def _publish_status(self):
        """Publish node status to MQTT"""
        status = {
            "node_id": self.node_id,
            "location": self.location,
            "status": "online" if self.online else "offline",
            "timestamp": datetime.utcnow().isoformat(),
            "battery_level": 100.0,
            "signal_strength": -30
        }
        self.client.publish(MQTT_TOPIC_STATUS, json.dumps(status))
    
    async def _play_sound_effect(self, alert_type: str):
        """Play sound effect without requiring external files"""
        if not getattr(self, 'audio_available', False):
            return
            
        # Generate simple beep tones based on alert type
        duration_ms = {
            "test": 500,
            "earthquake": 2000,
            "flood": 3000,
            "fire": 2000,
            "default": 1000
        }.get(alert_type, 1000)
        
        # Try to play existing file first
        audio_file = AUDIO_FILES.get(alert_type, AUDIO_FILES["default"])
        
        if os.path.exists(audio_file):
            try:
                self.is_playing = True
                print(f"🔊 Playing: {alert_type} alert ({duration_ms}ms)")
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"⚠️  Could not play {audio_file}, using beep instead")
                await self._play_beep()
        else:
            print(f"⚠️  No audio file found, playing beep tone")
            await self._play_beep()
        
        self.is_playing = False
        print("✓ Alert complete\n")
    
    async def _play_beep(self):
        """Generate a simple beep sound programmatically"""
        import numpy as np
        
        # Create a simple beep tone
        sample_rate = 44100
        duration = 0.5
        frequency = 800  # Hz
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * frequency * t)
        tone = (tone * 32767).astype(np.int16)
        
        # This would require scipy.soundfile in production
        # For now, just log it
        print(f"🔔 BEEP TONE GENERATED [{frequency}Hz]")
    
    async def _process_alerts(self):
        """Process alert queue"""
        while True:
            if self.alert_queue.empty():
                await asyncio.sleep(1)
                continue
            
            alert = await self.alert_queue.get()
            
            if self.is_playing:
                continue
            
            await self._play_sound_effect(alert.get("type", "default"))
            self.alert_queue.task_done()
    
    async def _heartbeat(self):
        """Periodic status heartbeat"""
        while True:
            await asyncio.sleep(60)
            self._publish_status()
    
    async def run(self):
        """Main entry point"""
        print(f"\n{'='*60}")
        print(f"🚨 LOCAL EMERGENCY WARNING SYSTEM - EDGE NODE (PC)")
        print(f"{'='*60}\n")
        print(f"📡 Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
        print(f"💬 Subscribed to: {MQTT_TOPIC_ALERT}")
        print(f"Type 'quit' to exit\n")
        
        try:
            # Connect to MQTT
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            await asyncio.sleep(2)
            
            print("✅ Ready! Waiting for alerts...\n")
            
            # Run concurrent tasks
            await asyncio.gather(
                self._process_alerts(),
                self._heartbeat()
            )
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down by user request...")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            pygame.mixer.quit()
            print("💤 Goodbye!")

async def main():
    node = PCAlertNode()
    await node.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nNode stopped by user")