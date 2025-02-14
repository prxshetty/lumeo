import asyncio
import io
import ssl
import sys
import signal
import chainlit as cl
import pyaudio
from uuid import uuid4
import wave

from speechmatics_flow.client import WebsocketClient
from speechmatics_flow.models import (
    ConnectionSettings,
    Interaction,
    AudioSettings,
    ConversationConfig,
    ServerMessageType,
)

import os
from dotenv import load_dotenv
load_dotenv()

CHUNK_SIZE = 800  
SEE_TRANSCRIPTS = True
AUTH_TOKEN = os.getenv("SPEECHMATICS_AUTH_TOKEN")
BUFFER_SIZE = 2400
SAMPLE_RATE = 16000
CHANNELS = 1

async def message_handler(msg: dict):
    if isinstance(msg, dict):
        message_type = msg.get("message", "")
        if message_type == "AddTranscript":
            transcript = msg.get("metadata", {}).get("transcript", "")
            if transcript.strip():
                stream = cl.user_session.get("transcript_stream")
                if not stream:
                    stream = cl.Message(author="You", content="")
                    await stream.stream_token("")  
                    cl.user_session.set("transcript_stream", stream)                
                await stream.stream_token(transcript + " ")

        elif message_type == "ResponseCompleted":
            if content := msg.get("content", ""):
                await cl.Message(
                    author="Lumeo",
                    content=content
                ).send()

        elif message_type == "ResponseInterrupted":
            if content := msg.get("content", ""):
                if stream := cl.user_session.get("transcript_stream"):
                    await stream.update()
                    cl.user_session.remove("transcript_stream")
                
                await cl.Message(
                    author="Lumeo",
                    content=f"[Interrupted] {content}"
                ).send()

class AudioBuffer:
    def __init__(self, buffer_size):
        self.buffer = bytearray()
        self.buffer_size = buffer_size
        self.min_buffer_size = buffer_size * 3
        self.sent_initial = False

    async def add_chunk(self, chunk: bytes, emitter, track_id):
        self.buffer.extend(chunk)        
        if len(self.buffer) >= self.min_buffer_size:
            while len(self.buffer) >= self.buffer_size:
                output_chunk = bytes(self.buffer[:self.buffer_size])
                self.buffer = self.buffer[self.buffer_size:]
                
                await emitter.send_audio_chunk(
                    cl.OutputAudioChunk(
                        mimeType="pcm16",
                        data=output_chunk,
                        track=track_id,
                        sample_rate=SAMPLE_RATE,
                        channels=CHANNELS
                    )
                )

    async def flush(self, emitter, track_id):
        if self.buffer:
            await emitter.send_audio_chunk(
                cl.OutputAudioChunk(
                    mimeType="pcm16",
                    data=bytes(self.buffer),
                    track=track_id,
                    sample_rate=SAMPLE_RATE,
                    channels=CHANNELS
                )
            )
        self.buffer = bytearray()

async def binary_msg_handler(msg: bytes):
    track_id = cl.user_session.get("track_id")
    
    audio_buffer = cl.user_session.get("audio_buffer")
    if audio_buffer is None:
        audio_buffer = AudioBuffer(BUFFER_SIZE)
        cl.user_session.set("audio_buffer", audio_buffer)
    
    await audio_buffer.add_chunk(msg, cl.context.emitter, track_id)

async def setup_client():
    client = WebsocketClient(
        ConnectionSettings(
            url="wss://flow.api.speechmatics.com/v1/flow",
            auth_token=AUTH_TOKEN,
        )
    )
    
    client.add_event_handler(ServerMessageType.AddAudio, binary_msg_handler)
    client.add_event_handler(ServerMessageType.AddTranscript, message_handler)
    client.add_event_handler(ServerMessageType.ResponseCompleted, message_handler)
    client.add_event_handler(ServerMessageType.ResponseInterrupted, message_handler)
    
    return client

async def async_generator(queue):
    while True:
        chunk = await queue.get()
        if chunk is None: 
            break
        yield chunk

class AsyncGeneratorIO:
    def __init__(self, generator):
        self.generator = generator
        self.buffer = b''
        self.eof = False

    async def read(self, size=-1):
        while len(self.buffer) < size or size == -1:
            try:
                chunk = await self.generator.__anext__()
                if chunk is None:  
                    self.eof = True
                    break
                self.buffer += chunk
            except StopAsyncIteration:
                self.eof = True
                break
        
        if size == -1:
            result = self.buffer
            self.buffer = b''
            return result
        else:
            result = self.buffer[:size]
            self.buffer = self.buffer[size:]
            return result

@cl.on_chat_start
async def start():
    """Initialize the chat session"""
    cl.user_session.set("track_id", str(uuid4()))
    cl.user_session.set("audio_chunks", asyncio.Queue())
    
    client = await setup_client()
    cl.user_session.set("client", client)
    
    await cl.Message("Welcome to Lumeo! Press the microphone button to start speaking.").send()

@cl.on_audio_start
async def on_audio_start():
    """Handle start of audio input"""
    client = cl.user_session.get("client")
    if not client:
        return False
        
    audio_queue = cl.user_session.get("audio_chunks")
    generator = async_generator(audio_queue)
    audio_stream = AsyncGeneratorIO(generator)
    
    task = asyncio.create_task(
        client.run(
            interactions=[Interaction(
                stream=audio_stream 
            )],
            audio_settings=AudioSettings(),
            conversation_config=ConversationConfig(
                template_id="flow-service-assistant-humphrey",
                template_variables={
                    "persona": "Your name is Lumeo...",
                    "style": "Your tone makes people feel at ease and comfortable.",
                    "context": "You are having a conversation. You want to please and assist the person you are speaking with."
                },
            ),
        )
    )
    cl.user_session.set("client_task", task)
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handle incoming audio chunks"""
    audio_queue = cl.user_session.get("audio_chunks")
    if audio_queue:
        await audio_queue.put(chunk.data)

@cl.on_audio_end
async def on_audio_end():
    """Handle end of audio input"""
    audio_queue = cl.user_session.get("audio_chunks")
    if audio_queue:
        await audio_queue.put(None)  

@cl.on_stop
async def on_stop():
    """Cleanup when the chat ends"""
    client_task = cl.user_session.get("client_task")
    if client_task:
        client_task.cancel()
        try:
            await client_task
        except asyncio.CancelledError:
            pass
    audio_buffer = cl.user_session.get("audio_buffer")
    if audio_buffer:
        track_id = cl.user_session.get("track_id")
        await audio_buffer.flush(cl.context.emitter, track_id)