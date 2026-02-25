import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional

import uuid

from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from dotenv import load_dotenv

from twilio.twiml.voice_response import VoiceResponse, Gather
from elevenlabs.client import ElevenLabs
from elevenlabs import save

# Import our optimized modules
from agent import run_agent
from streaming_agent import streaming_agent
from audio_streaming import audio_service
from voice_handler import call_flow_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI(title="Stateira Labs Voice Agent - Optimized")
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY", ""))

import tempfile

ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
AUDIO_DIR = os.path.join(tempfile.gettempdir(), "stateira_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Global session storage (in production, use Redis)
active_sessions: Dict[str, str] = {}

@app.get("/")
async def root():
    return {"status": "ok", "service": "Stateira Labs Voice Agent"}

@app.get("/debug")
async def debug():
    """Enhanced debug endpoint with optimization status"""
    try:
        # Check cache status
        cache_status = "unknown"
        try:
            if audio_service.redis_client:
                await audio_service.redis_client.ping()
                cache_status = "redis_connected"
            else:
                cache_status = "memory_only"
        except Exception:
            cache_status = "redis_failed"

        # Check audio service status
        audio_service_status = {
            "initialized": audio_service is not None,
            "common_responses_count": len(audio_service.common_responses) if audio_service else 0,
            "audio_dir_exists": os.path.exists(audio_service.audio_dir) if audio_service else False,
            "cache_status": cache_status
        }

        # Check streaming agent status
        agent_status = {
            "initialized": streaming_agent is not None,
            "llm_configured": hasattr(streaming_agent, 'llm') if streaming_agent else False,
            "system_prompt_length": len(streaming_agent.system_prompt) if streaming_agent else 0
        }

        # Check call flow manager status
        call_flow_status = {
            "initialized": call_flow_manager is not None,
            "active_sessions": len(call_flow_manager.vad.active_sessions) if call_flow_manager else 0
        }

        return {
            "service": "Stateira Labs Voice Agent - Optimized",
            "timestamp": time.time(),
            "environment": {
                "elevenlabs_api_key_exists": bool(os.getenv("ELEVENLABS_API_KEY")),
                "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", "NOT_SET"),
                "openai_api_key_exists": bool(os.getenv("OPENAI_API_KEY")),
                "redis_url_configured": bool(os.getenv("REDIS_URL"))
            },
            "optimizations": {
                "audio_streaming": audio_service_status,
                "streaming_agent": agent_status,
                "call_flow_manager": call_flow_status
            },
            "performance_features": {
                "streaming_tts": True,
                "cached_responses": True,
                "parallel_processing": True,
                "interrupt_handling": True,
                "voice_activity_detection": True
            }
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return {
            "error": f"Debug endpoint failed: {e}",
            "basic_info": {
                "elevenlabs_api_key_exists": bool(os.getenv("ELEVENLABS_API_KEY")),
                "openai_api_key_exists": bool(os.getenv("OPENAI_API_KEY"))
            }
        }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/incoming_call")
async def incoming_call(request: Request, From: str = Form(None)):
    """
    Optimized endpoint for incoming Twilio Voice Webhooks with faster greeting.
    """
    phone_number = From or "unknown"
    logger.info(f"Incoming call from {phone_number}")

    # Create call session for VAD and interrupt handling
    session_id = await call_flow_manager.start_call(phone_number)

    response = VoiceResponse()
    base_url = str(request.base_url).rstrip('/')
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")

    try:
        # Try to use pre-cached greeting for instant response
        cached_greeting_url = await audio_service.get_cached_audio_url("greeting", base_url)

        if cached_greeting_url:
            response.play(cached_greeting_url)
            logger.info(f"Using cached greeting: {cached_greeting_url}")
        else:
            # Fallback: generate greeting quickly
            greeting_text = "Hello, I'm Tommy from Stateira Labs. How can I help you?"
            audio_url = await audio_service.generate_audio_file_streaming(greeting_text, base_url)
            response.play(audio_url)
            logger.info(f"Generated greeting: {audio_url}")

    except Exception as tts_err:
        logger.error(f"Greeting generation failed: {tts_err}")
        response.say("Hello, I'm Tommy from Stateira Labs. How can I help you?")

    # Enhanced speech gathering with interrupt detection
    gather = Gather(
        input="speech",
        action=f"/process_speech?session_id={session_id}",
        method="POST",
        speechTimeout="auto",
        language="en-US",
        partialResultCallback=f"/speech_events?session_id={session_id}",
        partialResultCallbackMethod="POST"
    )
    response.append(gather)

    response.hangup()
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.post("/process_speech")
async def process_speech(request: Request, SpeechResult: str = Form(None), session_id: str = None):
    """
    Optimized speech processing with streaming, parallel processing, and interrupt handling.
    """
    logger.info(f"Processing speech for session {session_id}: {SpeechResult}")

    response = VoiceResponse()
    base_url = str(request.base_url).rstrip('/')
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")

    if not SpeechResult:
        # Use cached "repeat" response
        cached_url = await audio_service.get_cached_audio_url("repeat", base_url)
        if cached_url:
            response.play(cached_url)
        else:
            response.say("I didn't quite catch that. Could you please repeat?")

        gather = Gather(
            input="speech",
            action=f"/process_speech?session_id={session_id}",
            method="POST",
            speechTimeout="auto",
            partialResultCallback=f"/speech_events?session_id={session_id}",
            partialResultCallbackMethod="POST"
        )
        response.append(gather)
        return HTMLResponse(content=str(response), media_type="application/xml")

    try:
        # First, check topic compliance before processing
        if session_id:
            topic_result = await call_flow_manager.check_topic_compliance(session_id, SpeechResult)

            # Handle topic violations
            if topic_result["action"] in ["hangup_polite", "hangup_immediate"]:
                logger.warning(f"Hanging up session {session_id}: {topic_result['reason']}")
                response.say(topic_result["response"])
                response.hangup()
                await call_flow_manager.end_call(session_id)
                return HTMLResponse(content=str(response), media_type="application/xml")

            elif topic_result["action"] in ["warn_gentle", "warn_firm"]:
                logger.info(f"Topic warning for session {session_id}: {topic_result['relevance']}")
                # Play warning response and continue listening
                try:
                    warning_audio = await audio_service.generate_audio_file_streaming(
                        topic_result["response"], base_url
                    )
                    response.play(warning_audio)
                except Exception as audio_err:
                    response.say(topic_result["response"])

                gather = Gather(
                    input="speech",
                    action=f"/process_speech?session_id={session_id}",
                    method="POST",
                    speechTimeout="auto",
                    partialResultCallback=f"/speech_events?session_id={session_id}",
                    partialResultCallbackMethod="POST"
                )
                response.append(gather)
                return HTMLResponse(content=str(response), media_type="application/xml")

        # Check if we can start response (not interrupted)
        response_id = await call_flow_manager.start_response(session_id) if session_id else None

        if not response_id:
            logger.warning(f"Cannot start response for session {session_id}")
            response.say("Please try again.")
            return HTMLResponse(content=str(response), media_type="application/xml")

        # Use parallel LLM + TTS processing for ultra-low latency
        start_time = time.time()

        try:
            # Get agent response using streaming agent
            agent_reply = await streaming_agent.get_response(SpeechResult)
            logger.info(f"Agent response time: {time.time() - start_time:.2f}s")

            # Generate audio with streaming API
            audio_start_time = time.time()
            audio_url = await audio_service.generate_audio_file_streaming(agent_reply, base_url)
            logger.info(f"Audio generation time: {time.time() - audio_start_time:.2f}s")

            # Check if response is still valid (not interrupted)
            if session_id and not call_flow_manager.interrupt_handler.vad.is_response_valid(session_id, response_id):
                logger.info(f"Response {response_id} was interrupted, not playing")
                # Return interrupt handling response
                cached_url = await audio_service.get_cached_audio_url("thinking", base_url)
                if cached_url:
                    response.play(cached_url)
                else:
                    response.say("Go ahead.")
            else:
                # Play the generated response
                response.play(audio_url)
                logger.info(f"Total response time: {time.time() - start_time:.2f}s")

        except Exception as agent_err:
            logger.error(f"Agent processing failed: {agent_err}")
            # Use cached error response
            cached_url = await audio_service.get_cached_audio_url("error", base_url)
            if cached_url:
                response.play(cached_url)
            else:
                response.say("I'm sorry, I encountered an error. Please try again.")

        # End agent response in call flow
        if session_id:
            await call_flow_manager.end_response(session_id)

    except Exception as e:
        logger.error(f"Critical error processing speech: {e}")
        response.say("I'm experiencing technical difficulties. Please try again.")

    # Continue conversation with enhanced gathering
    gather = Gather(
        input="speech",
        action=f"/process_speech?session_id={session_id}",
        method="POST",
        speechTimeout="auto",
        partialResultCallback=f"/speech_events?session_id={session_id}",
        partialResultCallbackMethod="POST"
    )
    response.append(gather)

    return HTMLResponse(content=str(response), media_type="application/xml")

@app.post("/speech_events")
async def handle_speech_events(
    request: Request,
    session_id: str = None,
    SpeechResult: str = Form(None),
    PartialSpeechResult: str = Form(None)
):
    """Handle real-time speech events for interrupt detection"""
    if not session_id:
        return {"status": "no_session"}

    # Detect speech start/end for interrupt handling
    if PartialSpeechResult:
        # Speech is actively happening
        event_result = await call_flow_manager.process_speech_event(
            session_id, "speech_start", PartialSpeechResult
        )

        if event_result.get("action") == "interrupt_response":
            logger.info(f"Interrupt detected in session {session_id}")
            # Generate quick interrupt response
            base_url = str(request.base_url).rstrip('/')
            if "onrender.com" in base_url and base_url.startswith("http://"):
                base_url = base_url.replace("http://", "https://")

            interrupt_url = await call_flow_manager.interrupt_handler.generate_interrupt_response(
                session_id, audio_service
            )

            return {"action": "interrupt", "audio_url": interrupt_url}

    elif SpeechResult:
        # Speech ended
        await call_flow_manager.process_speech_event(session_id, "speech_end", SpeechResult)

    return {"status": "processed"}


@app.post("/end_call")
async def end_call(session_id: str = Form(None)):
    """Clean up call session"""
    if session_id:
        await call_flow_manager.end_call(session_id)
        logger.info(f"Call session {session_id} ended")
    return {"status": "ended"}


@app.get("/session_info/{session_id}")
async def get_session_info(session_id: str):
    """Get session information for debugging"""
    info = call_flow_manager.vad.get_session_info(session_id)
    if info:
        return info
    return {"error": "Session not found"}


@app.post("/cleanup")
async def cleanup_audio_files():
    """Clean up old audio files"""
    audio_service.cleanup_old_files()
    return {"status": "cleaned"}


@app.get("/debug/performance")
async def debug_performance():
    """Performance monitoring endpoint"""
    try:
        audio_files = []
        if os.path.exists(AUDIO_DIR):
            audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]

        return {
            "audio_files": {
                "count": len(audio_files),
                "directory": AUDIO_DIR,
                "disk_usage_mb": sum(
                    os.path.getsize(os.path.join(AUDIO_DIR, f))
                    for f in audio_files
                ) / 1024 / 1024
            },
            "active_sessions": len(call_flow_manager.vad.active_sessions) if call_flow_manager else 0,
            "cached_responses": list(audio_service.common_responses.keys()) if audio_service else [],
            "system_info": {
                "temp_dir": AUDIO_DIR,
                "timestamp": time.time()
            }
        }
    except Exception as e:
        return {"error": f"Performance debug failed: {e}"}


@app.get("/debug/sessions")
async def debug_sessions():
    """Debug all active sessions"""
    try:
        if not call_flow_manager:
            return {"error": "Call flow manager not initialized"}

        sessions = {}
        for session_id in call_flow_manager.vad.active_sessions:
            session_info = call_flow_manager.vad.get_session_info(session_id)
            if session_info:
                sessions[session_id] = session_info

        return {
            "active_sessions": len(sessions),
            "sessions": sessions,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": f"Session debug failed: {e}"}


@app.post("/debug/test_response")
async def test_response_generation(text: str = "Hello, this is a test"):
    """Test response generation pipeline"""
    try:
        base_url = "https://test-domain.com"  # Mock base URL
        start_time = time.time()

        # Test streaming agent
        agent_start = time.time()
        agent_response = await streaming_agent.get_response(text)
        agent_time = time.time() - agent_start

        # Test quick responses
        quick_start = time.time()
        quick_response = streaming_agent._get_quick_response(text)
        quick_time = time.time() - quick_start

        # Test cached audio lookup
        cache_start = time.time()
        cached_url = await audio_service.get_cached_audio_url("greeting", base_url)
        cache_time = time.time() - cache_start

        total_time = time.time() - start_time

        return {
            "test_input": text,
            "results": {
                "agent_response": {
                    "text": agent_response,
                    "duration": agent_time,
                    "length": len(agent_response)
                },
                "quick_response": {
                    "text": quick_response,
                    "duration": quick_time,
                    "found": quick_response is not None
                },
                "cached_audio": {
                    "url": cached_url,
                    "duration": cache_time,
                    "found": cached_url is not None
                }
            },
            "performance": {
                "total_duration": total_time,
                "agent_time_ratio": agent_time / total_time,
                "cache_time_ratio": cache_time / total_time
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": f"Response test failed: {e}"}


@app.post("/debug/simulate_call")
async def simulate_call_flow(
    phone_number: str = "+1234567890",
    test_phrases: list = None
):
    """Simulate a complete call flow for testing"""
    if test_phrases is None:
        test_phrases = ["Hello", "What products do you offer?", "Thank you", "Goodbye"]

    try:
        simulation_start = time.time()
        results = []

        # Start call session
        session_id = await call_flow_manager.start_call(phone_number)
        results.append({"action": "start_call", "session_id": session_id, "success": True})

        # Simulate conversation
        for i, phrase in enumerate(test_phrases):
            step_start = time.time()

            # Simulate speech processing
            response_id = await call_flow_manager.start_response(session_id)
            agent_response = await streaming_agent.get_response(phrase)
            await call_flow_manager.end_response(session_id)

            step_time = time.time() - step_start
            results.append({
                "step": i + 1,
                "user_input": phrase,
                "agent_response": agent_response,
                "response_id": response_id,
                "duration": step_time,
                "success": True
            })

        # End call
        await call_flow_manager.end_call(session_id)
        total_time = time.time() - simulation_start

        results.append({"action": "end_call", "success": True})

        return {
            "simulation": "complete",
            "session_id": session_id,
            "total_duration": total_time,
            "steps": len(test_phrases),
            "average_response_time": total_time / len(test_phrases),
            "results": results,
            "timestamp": time.time()
        }

    except Exception as e:
        return {"error": f"Call simulation failed: {e}"}


@app.get("/debug/health_detailed")
async def detailed_health_check():
    """Comprehensive health check for all components"""
    health_report = {
        "timestamp": time.time(),
        "overall_status": "healthy",
        "components": {}
    }

    # Check each component
    components = [
        ("audio_service", audio_service),
        ("streaming_agent", streaming_agent),
        ("call_flow_manager", call_flow_manager)
    ]

    for name, component in components:
        try:
            if component is None:
                health_report["components"][name] = {
                    "status": "error",
                    "message": "Component not initialized"
                }
                health_report["overall_status"] = "unhealthy"
            else:
                health_report["components"][name] = {
                    "status": "healthy",
                    "message": "Component operational"
                }
        except Exception as e:
            health_report["components"][name] = {
                "status": "error",
                "message": f"Component check failed: {e}"
            }
            health_report["overall_status"] = "unhealthy"

    # Check API keys
    required_keys = ["ELEVENLABS_API_KEY", "OPENAI_API_KEY"]
    for key in required_keys:
        if not os.getenv(key):
            health_report["components"][f"env_{key}"] = {
                "status": "error",
                "message": "Required environment variable missing"
            }
            health_report["overall_status"] = "unhealthy"
        else:
            health_report["components"][f"env_{key}"] = {
                "status": "healthy",
                "message": "Environment variable set"
            }

    return health_report


@app.get("/debug/topic_stats/{session_id}")
async def get_topic_stats(session_id: str):
    """Get topic compliance statistics for a session"""
    try:
        stats = await call_flow_manager.get_session_topic_stats(session_id)
        return stats
    except Exception as e:
        return {"error": f"Failed to get topic stats: {e}"}


@app.post("/debug/test_topic_analysis")
async def test_topic_analysis(
    query: str = "What's your favorite movie?",
    session_id: str = "test-session"
):
    """Test topic analysis system"""
    try:
        from topic_guard import topic_guard

        # Analyze the query
        analysis = topic_guard.analyze_query(query, session_id)

        # Get escalated response
        response_text, suggested_action = topic_guard.get_escalated_response(session_id, analysis)

        return {
            "input_query": query,
            "analysis": {
                "relevance": analysis.relevance.value,
                "confidence": analysis.confidence,
                "reason": analysis.reason,
                "suggested_action": analysis.suggested_action.value
            },
            "escalated_response": {
                "text": response_text,
                "action": suggested_action.value
            },
            "should_hangup": topic_guard.should_hangup(session_id),
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": f"Topic analysis test failed: {e}"}


@app.post("/debug/force_hangup/{session_id}")
async def debug_force_hangup(session_id: str, reason: str = "Admin test"):
    """Force hangup a session (for testing)"""
    try:
        result = await call_flow_manager.force_hangup(session_id, reason)
        return result
    except Exception as e:
        return {"error": f"Force hangup failed: {e}"}


@app.get("/debug/topic_examples")
async def show_topic_examples():
    """Show examples of how topic analysis works"""
    examples = [
        # Business relevant
        ("I want to learn about Stateira Labs", "HIGHLY_RELEVANT", "Should proceed normally"),
        ("Can I schedule a meeting?", "HIGHLY_RELEVANT", "Should proceed normally"),
        ("What crypto services do you offer?", "HIGHLY_RELEVANT", "Should proceed normally"),

        # Off-topic but harmless
        ("How's the weather today?", "OFF_TOPIC", "Gentle warning: redirect to business"),
        ("What's your favorite movie?", "OFF_TOPIC", "Gentle warning: redirect to business"),

        # Time wasting
        ("Just calling to see what happens", "TIME_WASTING", "Warning: ask for specific help"),
        ("I'm bored and wondering about random stuff", "TIME_WASTING", "Warning: ask for specific help"),

        # Inappropriate/Spam
        ("CONGRATULATIONS YOU WON!!!", "INAPPROPRIATE", "Firm warning or hangup"),
        ("test test test hello", "INAPPROPRIATE", "Firm warning or hangup"),
        ("aaaaaaaaaaaa", "INAPPROPRIATE", "Immediate hangup"),
    ]

    return {
        "topic_analysis_examples": [
            {
                "query": query,
                "expected_classification": classification,
                "expected_action": action
            }
            for query, classification, action in examples
        ],
        "escalation_policy": {
            "first_off_topic": "Gentle redirect to business topics",
            "second_off_topic": "Firm warning about call purpose",
            "third_off_topic": "Polite hangup",
            "immediate_hangup": "Spam, abuse, or excessive nonsense"
        },
        "business_keywords": [
            "stateira", "labs", "software", "crypto", "trading", "finance",
            "meeting", "demo", "consultation", "product", "service", "help"
        ]
    }


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
