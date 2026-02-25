import os
import uuid
import asyncio
import tempfile
import time
from typing import AsyncGenerator, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import logging

from elevenlabs.client import ElevenLabs
from elevenlabs import stream
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioStreamingService:
    def __init__(self):
        self.eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY", ""))
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.audio_dir = os.path.join(tempfile.gettempdir(), "stateira_audio")
        os.makedirs(self.audio_dir, exist_ok=True)

        # Redis for caching (optional, falls back gracefully)
        self.redis_client = None
        self._init_redis()

        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Pre-cached common responses - now with natural, conversational tone
        import random
        self.common_responses = {
            "greeting": random.choice([
                "Hey! This is Tommy from Stateira Labs. What's up?",
                "Hi there! Tommy here from Stateira Labs. How can I help?",
                "Hey! It's Tommy at Stateira Labs. What brings you by today?",
                "Oh hey! Tommy from Stateira Labs. How's it going?"
            ]),
            "thinking": random.choice([
                "Hmm, let me see...",
                "Oh, let me check on that real quick.",
                "Yeah, let me look that up for you.",
                "Give me just a sec..."
            ]),
            "error": random.choice([
                "Oof, sorry - I'm having some tech issues. Can you try again?",
                "Ah man, something's not working right. Give me another shot?",
                "Oops, I'm having some trouble. Mind trying that again?",
                "Sorry about that - technical hiccup. Can we try again?"
            ]),
            "goodbye": random.choice([
                "Alright, take care! Thanks for calling!",
                "See ya! Have an awesome day!",
                "Later! Thanks for reaching out to Stateira Labs!",
                "Bye! Talk to you soon!"
            ]),
            "repeat": random.choice([
                "Sorry, I didn't catch that. What'd you say?",
                "Oh, I missed that. Can you say it again?",
                "Sorry, what was that? Didn't quite hear you.",
                "My bad - can you repeat that?"
            ]),
            "hold": random.choice([
                "Give me just a quick second...",
                "Hold on, let me grab that info...",
                "One sec while I check on this...",
                "Just a moment - looking that up now..."
            ]),
            "confused": random.choice([
                "Hmm, I'm not sure I follow. Can you explain that a bit more?",
                "Sorry, I'm a bit confused. What exactly are you looking for?",
                "I'm not quite getting it. Could you help me understand?",
                "Hmm, can you break that down for me?"
            ]),
            "excited": random.choice([
                "Oh that's awesome!",
                "Nice! That sounds great!",
                "Oh cool! I love that!",
                "That's so cool!"
            ])
        }

        # Pre-generate cached audio files
        asyncio.create_task(self._preload_common_responses())

    async def _init_redis(self):
        """Initialize Redis connection with graceful fallback"""
        try:
            self.redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"),
                decode_responses=False
            )
            await self.redis_client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis cache not available, using memory cache: {e}")
            self.redis_client = None

    async def _preload_common_responses(self):
        """Pre-generate and cache common response audio files"""
        logger.info("Pre-loading common responses...")

        for response_type, text in self.common_responses.items():
            try:
                filename = f"cached_{response_type}_{uuid.uuid4()}.mp3"
                filepath = os.path.join(self.audio_dir, filename)

                # Generate audio using faster model
                audio_generator = self.eleven_client.text_to_speech.convert(
                    text=text,
                    voice_id=self.voice_id,
                    model_id="eleven_flash_v2_5"  # Fastest model
                )

                with open(filepath, "wb") as f:
                    for chunk in audio_generator:
                        f.write(chunk)

                # Cache the filename for quick retrieval
                if self.redis_client:
                    await self.redis_client.set(f"cached_audio:{response_type}", filename, ex=3600)

                logger.info(f"Pre-cached {response_type} response: {filename}")

            except Exception as e:
                logger.error(f"Failed to pre-cache {response_type}: {e}")

    async def get_cached_audio_url(self, response_type: str, base_url: str) -> Optional[str]:
        """Get URL for pre-cached audio response"""
        try:
            if self.redis_client:
                filename = await self.redis_client.get(f"cached_audio:{response_type}")
                if filename:
                    filename = filename.decode() if isinstance(filename, bytes) else filename
                    return f"{base_url}/audio/{filename}"
        except Exception as e:
            logger.error(f"Error retrieving cached audio: {e}")

        return None

    async def stream_text_to_speech(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream audio generation from text using ElevenLabs streaming API"""
        try:
            logger.info(f"Starting streaming TTS for text: {text[:50]}...")

            # Use the streaming API for real-time generation
            audio_stream = self.eleven_client.text_to_speech.convert_as_stream(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_flash_v2_5"  # Fastest model for streaming
            )

            chunk_count = 0
            for audio_chunk in audio_stream:
                chunk_count += 1
                yield audio_chunk

                # Small delay to prevent overwhelming the connection
                if chunk_count % 10 == 0:
                    await asyncio.sleep(0.01)

            logger.info(f"Completed streaming TTS, generated {chunk_count} chunks")

        except Exception as e:
            logger.error(f"Error in streaming TTS: {e}")
            # Fallback to non-streaming if streaming fails
            try:
                audio_generator = self.eleven_client.text_to_speech.convert(
                    text=text,
                    voice_id=self.voice_id,
                    model_id="eleven_flash_v2_5"
                )
                for chunk in audio_generator:
                    yield chunk
            except Exception as fallback_error:
                logger.error(f"Fallback TTS also failed: {fallback_error}")
                raise

    async def generate_audio_file_streaming(self, text: str, base_url: str) -> str:
        """Generate audio file using streaming API and return URL"""
        filename = f"stream_{uuid.uuid4()}.mp3"
        filepath = os.path.join(self.audio_dir, filename)

        try:
            with open(filepath, "wb") as f:
                async for chunk in self.stream_text_to_speech(text):
                    f.write(chunk)

            # Ensure HTTPS for Render deployment
            if "onrender.com" in base_url and base_url.startswith("http://"):
                base_url = base_url.replace("http://", "https://")

            audio_url = f"{base_url}/audio/{filename}"
            logger.info(f"Generated streaming audio: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"Failed to generate streaming audio: {e}")
            # Clean up failed file
            if os.path.exists(filepath):
                os.remove(filepath)
            raise

    async def parallel_llm_tts_generation(self, text_generator, base_url: str) -> str:
        """Generate TTS in parallel as LLM text is being generated"""
        accumulated_text = ""
        sentences = []
        audio_files = []

        try:
            # Collect text and split into sentences for parallel processing
            async for text_chunk in text_generator:
                accumulated_text += text_chunk

                # Split into sentences when we have enough text
                if any(punct in accumulated_text for punct in ['.', '!', '?', '\n']):
                    # Split and process complete sentences
                    import re
                    current_sentences = re.split(r'[.!?\n]+', accumulated_text)

                    # Process complete sentences (not the last incomplete one)
                    for sentence in current_sentences[:-1]:
                        if sentence.strip():
                            sentences.append(sentence.strip())

                    # Keep the last incomplete sentence
                    accumulated_text = current_sentences[-1] if current_sentences else ""

            # Add any remaining text
            if accumulated_text.strip():
                sentences.append(accumulated_text.strip())

            # Generate audio for all sentences in parallel
            if sentences:
                full_text = ". ".join(sentences)
                audio_url = await self.generate_audio_file_streaming(full_text, base_url)
                return audio_url

        except Exception as e:
            logger.error(f"Error in parallel LLM-TTS generation: {e}")
            raise

    def cleanup_old_files(self, max_age_hours: int = 2):
        """Clean up old audio files to prevent disk space issues"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.audio_dir):
                if filename.endswith('.mp3'):
                    filepath = os.path.join(self.audio_dir, filename)
                    file_age = current_time - os.path.getctime(filepath)

                    if file_age > (max_age_hours * 3600):
                        os.remove(filepath)
                        logger.debug(f"Cleaned up old audio file: {filename}")

        except Exception as e:
            logger.error(f"Error cleaning up audio files: {e}")

# Global instance
audio_service = AudioStreamingService()