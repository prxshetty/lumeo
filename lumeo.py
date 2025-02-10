import os
import json
import asyncio
import io
import pyaudio
from contextlib import asynccontextmanager

import chainlit as cl
from uuid import uuid4
from chainlit.logger import logger
from tools import tools
from speechmatics_flow.client import WebsocketClient
from speechmatics_flow.models import (
    ConnectionSettings,
    Interaction,
    AudioSettings,
    ConversationConfig,
    ServerMessageType,
)

class FlowSession:
    def __init__(self):
        self.client = None
        self.audio_buffer = io.BytesIO()
        self.active = False
        self.playback_task = None
        self._lock = asyncio.Lock()
        self._retry_count = 0
        self._max_retries = 3
        self._retry_delay = 2

    async def reset(self):
        """Reset session state"""
        self.active = False
        self._retry_count = 0
        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()
            try:
                await self.playback_task
            except asyncio.CancelledError:
                pass
        self.audio_buffer = io.BytesIO()

    @asynccontextmanager
    async def start_session(self):
        if self.active:
            await self.reset()  # Reset if already active
        
        while self._retry_count < self._max_retries:
            try:
                self.active = True
                yield self
                break
            except Exception as e:
                self._retry_count += 1
                if "Concurrent Quota Exceeded" in str(e):
                    logger.warning(f"Quota exceeded, attempt {self._retry_count}/{self._max_retries}. Waiting {self._retry_delay}s...")
                    await asyncio.sleep(self._retry_delay)
                    self._retry_delay *= 2
                else:
                    logger.error(f"Session error: {str(e)}")
                    await self.reset()
                    raise

async def audio_playback(buffer):
    """Read from buffer and play audio back to the user"""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
    try:
        while True:
            audio_to_play = buffer.getvalue()
            if audio_to_play:
                stream.write(audio_to_play)
                buffer.seek(0)
                buffer.truncate(0)
            await asyncio.sleep(0.05)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

async def setup_flow_realtime():
    """Initialize Speechmatics Flow connection"""
    auth_token = os.getenv("SPEECHMATICS_AUTH_TOKEN")
    if not auth_token:
        logger.error("❌ SPEECHMATICS_AUTH_TOKEN not found in environment variables")
        return None
        
    settings = ConnectionSettings(
        url="wss://flow.api.speechmatics.com/v1/flow",
        auth_token=auth_token
    )
    
    try:
        session = FlowSession()
        session.client = WebsocketClient(settings)

        def binary_msg_handler(msg: bytes):
            if isinstance(msg, (bytes, bytearray)):
                session.audio_buffer.write(msg)

        session.client.add_event_handler(ServerMessageType.AddAudio, binary_msg_handler)
        cl.user_session.set("flow_session", session)
        logger.info("✅ Successfully initialized Speechmatics Flow connection")
        return session
    except Exception as e:
        logger.error(f"❌ Error initializing Speechmatics Flow: {str(e)}")
        return None

@cl.on_chat_start
async def start():
    session = await setup_flow_realtime()
    if session:
        await cl.Message(content="Hello! I'm here. Press `P` to talk!").send()
    else:
        await cl.Message(
            content="Error: Could not initialize Speechmatics connection. Please check your API key and try again."
        ).send()

@cl.on_message
async def on_message(message: cl.Message):
    session = cl.user_session.get("flow_session")
    if session and session.active:
        async with session._lock:
            try:
                await session.client.run(
                    interactions=[Interaction(text=message.content)],
                    audio_settings=AudioSettings(),
                    conversation_config=ConversationConfig(),
                )
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await cl.Message(content=f"Error: {str(e)}").send()
    else:
        await cl.Message(content="Please activate voice mode first!").send()

@cl.on_audio_start
async def on_audio_start():
    try:
        session = cl.user_session.get("flow_session")
        if not session:
            return False

        async with session.start_session():
            if session._retry_count >= session._max_retries:
                await cl.Message(content="Could not establish connection after multiple attempts. Please try again later.").send()
                return False

            await session.client.run(
                interactions=[],
                audio_settings=AudioSettings(),
                conversation_config=ConversationConfig(),
            )
            
            session.playback_task = asyncio.create_task(audio_playback(session.audio_buffer))
            return True
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        await cl.ErrorMessage(content=f"Connection failed: {str(e)}").send()
        return False

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    session = cl.user_session.get("flow_session")
    if session and session.active:
        async with session._lock:
            try:
                # Ensure we have valid audio data
                if not chunk.data or len(chunk.data) == 0:
                    logger.warning("Received empty audio chunk")
                    return

                await session.client.run(
                    interactions=[],
                    audio_settings=AudioSettings(
                        sample_rate=16000,
                        chunk_size=1024
                    ),
                    audio_data=chunk.data
                )
            except Exception as e:
                logger.error(f"Error sending audio: {str(e)}")
                await session.reset()

@cl.on_audio_end
@cl.on_chat_end
@cl.on_stop
async def on_end():
    try:
        session = cl.user_session.get("flow_session")
        if session:
            async with session._lock:
                if session.active:
                    await session.client.run(
                        interactions=[],
                        audio_settings=AudioSettings(),
                        conversation_config=ConversationConfig(),
                        close=True
                    )
                await session.reset()
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

                

