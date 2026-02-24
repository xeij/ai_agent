import os
import json
import logging
from typing import Dict, Any

import uuid

from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from dotenv import load_dotenv

from twilio.twiml.voice_response import VoiceResponse, Gather
from elevenlabs.client import ElevenLabs
from elevenlabs import save

from agent import run_agent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI(title="Stateira Labs Voice Agent")
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY", ""))

import tempfile

ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Example: Rachel

AUDIO_DIR = os.path.join(tempfile.gettempdir(), "stateira_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {"status": "ok", "service": "Stateira Labs Voice Agent"}

@app.get("/debug")
async def debug():
    return {
        "elevenlabs_api_key_exists": bool(os.getenv("ELEVENLABS_API_KEY")),
        "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", "NOT_SET"),
        "openai_api_key_exists": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.post("/incoming_call")
async def incoming_call(request: Request):
    """
    Endpoint for incoming Twilio Voice Webhooks.
    Responds with TwiML to gather speech from the caller.
    """
    logger.info("Incoming call received from Twilio")
    
    response = VoiceResponse()
    greeting = "Hello, I'm Tommy. How can I help you?"
    
    # Generate the greeting using ElevenLabs
    try:
        if not os.getenv("ELEVENLABS_API_KEY"):
            raise ValueError("ELEVENLABS_API_KEY not set")
            
        # Note: In elevenlabs v1+, client.generate is replaced with client.text_to_speech.convert
        audio_generator = eleven_client.text_to_speech.convert(
            text=greeting,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id="eleven_turbo_v2"
        )
        
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Save by writing the bytes
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
        
        base_url = str(request.base_url).rstrip('/')
        if "onrender.com" in base_url and base_url.startswith("http://"):
            base_url = base_url.replace("http://", "https://")
            
        audio_url = f"{base_url}/audio/{filename}"
        response.play(audio_url)
        logger.info(f"Generated ElevenLabs greeting: {audio_url}")
        
    except Exception as tts_err:
        logger.error(f"ElevenLabs TTS failed: {tts_err}. No fallback - call will end.")
        response.say("Sorry, I'm having technical difficulties. Please try again later.")
        response.hangup()
        return HTMLResponse(content=str(response), media_type="application/xml")
    
    # Start gathering speech
    gather = Gather(
        input="speech",
        action="/process_speech",
        method="POST",
        speechTimeout="auto",
        language="en-US"
    )
    response.append(gather)
    
    # If they don't say anything, hang up
    response.hangup()
    
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.post("/process_speech")
async def process_speech(request: Request, SpeechResult: str = Form(None)):
    """
    Receives transcribed speech from Twilio, runs it through LangGraph Agent,
    and returns TwiML with the AI response.
    Note: For ultra-realistic responses, returning <Play> with an audio URL of ElevenLabs output is ideal.
    For this implementation, we will mock the ElevenLabs logic and use Twilio <Say> as a fallback if ElevenLabs fails.
    """
    logger.info(f"Received speech from Twilio: {SpeechResult}")
    
    response = VoiceResponse()
    
    if not SpeechResult:
        response.say("I didn't quite catch that. Could you please repeat?")
        gather = Gather(input="speech", action="/process_speech", method="POST", speechTimeout="auto")
        response.append(gather)
        return HTMLResponse(content=str(response), media_type="application/xml")
    
    try:
        # Run the query through our LangGraph Agent
        # Note: In a production voice app, streaming is preferred to reduce latency.
        agent_reply = run_agent(query=SpeechResult)
        logger.info(f"Agent reply: {agent_reply}")
        
        # Generate ElevenLabs audio
        try:
            if not os.getenv("ELEVENLABS_API_KEY"):
                raise ValueError("ELEVENLABS_API_KEY not set")
                
            audio_generator = eleven_client.text_to_speech.convert(
                text=agent_reply,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_turbo_v2", # Fast model suitable for conversational AI
            )
            
            # Save audio to a unique file
            filename = f"{uuid.uuid4()}.mp3"
            filepath = os.path.join(AUDIO_DIR, filename)
            
            with open(filepath, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            # Use <Play> to stream the generated audio url
            base_url = str(request.base_url).rstrip('/')
            if "onrender.com" in base_url and base_url.startswith("http://"):
                base_url = base_url.replace("http://", "https://")
                
            audio_url = f"{base_url}/audio/{filename}"
            response.play(audio_url)
            logger.info(f"Generated ElevenLabs audio: {audio_url}")
            
        except Exception as tts_err:
            logger.error(f"ElevenLabs TTS failed: {tts_err}. No fallback - ending call.")
            response.say("I'm experiencing technical difficulties. Goodbye.")
            response.hangup()
            return HTMLResponse(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing speech: {e}")
        response.say("I'm sorry, I encountered an error processing your request. Please try again.")
    
    # Continue the conversation
    gather = Gather(input="speech", action="/process_speech", method="POST", speechTimeout="auto")
    response.append(gather)
    
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve the generated audio files to Twilio."""
    file_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    return HTMLResponse(status_code=404, content="File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
