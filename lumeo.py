import asyncio
import io
import ssl
import sys
import os
from typing import Optional, Dict, Any
from uuid import uuid4
import chainlit as cl
import pyaudio
from dotenv import load_dotenv
import traceback

from speechmatics_flow.client import WebsocketClient
from speechmatics_flow.models import (
    ConnectionSettings,
    Interaction,
    AudioSettings,
    ConversationConfig,
    ServerMessageType,
)

from utils.common import logger

# Load environment variables
load_dotenv()

# Get auth token from environment variable
AUTH_TOKEN = os.getenv("SPEECHMATICS_AUTH_TOKEN")

if not AUTH_TOKEN:
    raise ValueError("Please set SPEECHMATICS_AUTH_TOKEN in your .env file")

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SIZE = 1024

class AudioState:
    def __init__(self):
        self.input_queue = asyncio.Queue()
        self.output_buffer = io.BytesIO()
        self.is_processing = False
        self.audio_session = None
        self.playback_task = None
        self.client = None
        # Initialize PyAudio
        self.pyaudio = pyaudio.PyAudio()
        # Find input and output devices
        self.input_device = self.get_input_device()
        self.output_device = self.get_output_device()
        self.current_message = None  # Add this to track current message
        
    def get_input_device(self):
        """Get the default input device index"""
        return self.pyaudio.get_default_input_device_info()['index']
    
    def get_output_device(self):
        """Find headphones/earphones device"""
        for i in range(self.pyaudio.get_device_count()):
            device_info = self.pyaudio.get_device_info_by_index(i)
            device_name = device_info['name'].lower()
            # Look for headphones or earphones in device name
            if ('headphone' in device_name or 'earphone' in device_name) and device_info['maxOutputChannels'] > 0:
                return i
        # Fallback to default output device
        return self.pyaudio.get_default_output_device_info()['index']

    def cleanup(self):
        """Cleanup PyAudio resources"""
        if self.pyaudio:
            self.pyaudio.terminate()

audio_state = AudioState()

# Create a buffer to store binary messages sent from the server
audio_buffer = io.BytesIO()

# Create a websocket client
client = WebsocketClient(
    ConnectionSettings(
        url="wss://flow.api.speechmatics.com/v1/flow",
        auth_token=AUTH_TOKEN,
    )
)

# Create callback function which adds binary messages to audio buffer
def binary_msg_handler(msg: bytes):
    if isinstance(msg, (bytes, bytearray)):
        audio_state.output_buffer.write(msg)

# Register the callback
client.add_event_handler(ServerMessageType.AddAudio, binary_msg_handler)

# Handle transcriptions for UI updates
async def transcription_handler(msg: Dict[str, Any]):
    """Handle transcriptions with real-time UI updates"""
    if "transcript" in msg:
        transcript = msg["transcript"].strip()
        if transcript:
            if audio_state.current_message:
                # Update existing message
                await audio_state.current_message.update(content=transcript)
            else:
                # Create new message
                audio_state.current_message = cl.Message(
                    content=transcript,
                    author="You",
                    metadata={
                        "style": {
                            "background": "#f0f0f0",
                            "borderRadius": "8px",
                            "padding": "10px",
                            "margin": "5px 0"
                        }
                    }
                )
                await audio_state.current_message.send()

client.add_event_handler(ServerMessageType.AddTranscript, transcription_handler)

async def audio_playback():
    """Play audio from output buffer with state management"""
    try:
        stream = audio_state.pyaudio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            output_device_index=audio_state.output_device,
            frames_per_buffer=CHUNK_SIZE
        )
        
        while True:
            if audio_state.output_buffer.tell() > 0:
                audio_state.is_processing = True
                audio_data = audio_state.output_buffer.getvalue()
                stream.write(audio_data)
                audio_state.output_buffer.seek(0)
                audio_state.output_buffer.truncate()
                audio_state.is_processing = False
            await asyncio.sleep(0.01)
    finally:
        if stream:
            stream.stop_stream()
            stream.close()

async def process_input():
    """Process input audio chunks from queue"""
    while True:
        chunk = await audio_state.input_queue.get()
        if chunk is None:
            break
        if audio_state.client and audio_state.audio_session:
            await audio_state.client.send_audio(chunk)

def print_audio_devices():
    """Debug function to list all audio devices"""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        logger.info(f"Device {i}: {dev['name']}")
    p.terminate()

# Chainlit event handlers
@cl.on_chat_start
async def start():
    print_audio_devices()
    await cl.Message(content="Hello! I'm here. Press `P` to talk!").send()
    
    # Log audio devices
    logger.info(f"Using output device: {audio_state.pyaudio.get_device_info_by_index(audio_state.output_device)['name']}")
    logger.info(f"Using input device: {audio_state.pyaudio.get_device_info_by_index(audio_state.input_device)['name']}")
    
    audio_state.client = WebsocketClient(
        ConnectionSettings(
            url="wss://flow.api.speechmatics.com/v1/flow",
            auth_token=AUTH_TOKEN,
        )
    )
    audio_state.client.add_event_handler(ServerMessageType.AddAudio, binary_msg_handler)
    audio_state.client.add_event_handler(ServerMessageType.AddTranscript, transcription_handler)
    audio_state.playback_task = asyncio.create_task(audio_playback())

@cl.on_audio_start
async def on_audio_start():
    """Handle start of audio input"""
    try:
        if not audio_state.is_processing:
            # Reset current message at start of new audio
            audio_state.current_message = None
            
            audio_state.audio_session = asyncio.create_task(
                audio_state.client.run(
                    interactions=[Interaction(sys.stdin.buffer)],
                    audio_settings=AudioSettings(),
                    conversation_config=ConversationConfig(),
                )
            )
            logger.info("Started audio session")
            return True
    except Exception as e:
        logger.error(f"Error starting audio: {str(e)}")
        await cl.ErrorMessage(content=f"Audio error: {str(e)}").send()
        return False

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handle incoming audio chunks with processing check"""
    if not audio_state.is_processing and chunk.data:
        await audio_state.input_queue.put(chunk.data)

@cl.on_audio_end
async def on_audio_end():
    """Handle end of audio input"""
    # Finalize current message
    audio_state.current_message = None
    
    if audio_state.audio_session and not audio_state.audio_session.done():
        audio_state.audio_session.cancel()
        try:
            await audio_state.audio_session
        except asyncio.CancelledError:
            pass
        audio_state.audio_session = None

@cl.on_chat_end
@cl.on_stop
async def on_end():
    """Cleanup resources"""
    # Cancel playback task
    if audio_state.playback_task:
        audio_state.playback_task.cancel()
        try:
            await audio_state.playback_task
        except asyncio.CancelledError:
            pass
        audio_state.playback_task = None
    
    # Cancel audio session if running
    if audio_state.audio_session:
        audio_state.audio_session.cancel()
        try:
            await audio_state.audio_session
        except asyncio.CancelledError:
            pass
        audio_state.audio_session = None
    
    # Clear buffers
    audio_state.output_buffer.seek(0)
    audio_state.output_buffer.truncate()
    
    # Reset state
    audio_state.is_processing = False
    audio_state.client = None
    
    # Cleanup PyAudio
    audio_state.cleanup()

if __name__ == "__main__":
    cl.run()
