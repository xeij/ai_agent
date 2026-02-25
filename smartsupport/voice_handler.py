import asyncio
import time
import uuid
from typing import Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Import topic guard system
from topic_guard import topic_guard, CallAction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CallState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    WARNED = "warned"        # User has been warned about off-topic behavior
    FLAGGED = "flagged"      # Call flagged for termination
    ENDED = "ended"


@dataclass
class CallSession:
    session_id: str
    phone_number: str
    state: CallState
    last_activity: float
    current_response_id: Optional[str] = None
    interrupt_count: int = 0
    total_duration: float = 0
    created_at: float = time.time()
    # Topic monitoring fields
    off_topic_warnings: int = 0
    topic_violations: int = 0
    should_terminate: bool = False


class VoiceActivityDetector:
    """Simulated VAD for interrupt detection and natural turn-taking"""

    def __init__(self):
        self.active_sessions: Dict[str, CallSession] = {}
        self.speech_timeout = 3.0  # Seconds of silence before considering speech ended
        self.interrupt_threshold = 1.5  # Seconds of speech to trigger interrupt
        self.max_response_time = 30.0  # Max time for agent to respond

    def create_session(self, phone_number: str) -> str:
        """Create a new call session"""
        session_id = str(uuid.uuid4())
        session = CallSession(
            session_id=session_id,
            phone_number=phone_number,
            state=CallState.IDLE,
            last_activity=time.time()
        )
        self.active_sessions[session_id] = session
        logger.info(f"Created new call session: {session_id}")
        return session_id

    def update_session_state(self, session_id: str, new_state: CallState) -> bool:
        """Update session state with validation"""
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return False

        session = self.active_sessions[session_id]
        old_state = session.state
        session.state = new_state
        session.last_activity = time.time()

        logger.info(f"Session {session_id}: {old_state.value} -> {new_state.value}")
        return True

    def detect_speech_start(self, session_id: str) -> bool:
        """Called when Twilio detects speech start"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        # If agent is speaking, this might be an interrupt
        if session.state == CallState.SPEAKING:
            session.interrupt_count += 1
            self.update_session_state(session_id, CallState.INTERRUPTED)
            logger.info(f"Interrupt detected in session {session_id} (count: {session.interrupt_count})")
            return True

        # Normal speech start
        self.update_session_state(session_id, CallState.LISTENING)
        return False

    def detect_speech_end(self, session_id: str) -> bool:
        """Called when speech ends (silence detected)"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        if session.state in [CallState.LISTENING, CallState.INTERRUPTED]:
            # Speech has ended, ready for processing
            self.update_session_state(session_id, CallState.PROCESSING)
            return True

        return False

    def can_start_response(self, session_id: str) -> bool:
        """Check if it's safe to start agent response"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        return session.state == CallState.PROCESSING

    def start_agent_response(self, session_id: str) -> Optional[str]:
        """Mark that agent is starting to speak"""
        if session_id not in self.active_sessions:
            return None

        response_id = str(uuid.uuid4())
        session = self.active_sessions[session_id]
        session.current_response_id = response_id

        self.update_session_state(session_id, CallState.SPEAKING)
        return response_id

    def is_response_valid(self, session_id: str, response_id: str) -> bool:
        """Check if this response is still valid (not interrupted)"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        return (session.current_response_id == response_id and
                session.state != CallState.INTERRUPTED)

    def end_agent_response(self, session_id: str):
        """Mark that agent finished speaking"""
        if session_id in self.active_sessions:
            self.update_session_state(session_id, CallState.IDLE)

    def cleanup_session(self, session_id: str):
        """Clean up session when call ends"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.total_duration = time.time() - session.created_at
            logger.info(f"Ending session {session_id}. Duration: {session.total_duration:.1f}s, "
                       f"Interrupts: {session.interrupt_count}")
            del self.active_sessions[session_id]

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information for debugging"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        return {
            "session_id": session.session_id,
            "state": session.state.value,
            "phone_number": session.phone_number,
            "interrupt_count": session.interrupt_count,
            "duration": time.time() - session.created_at,
            "last_activity": session.last_activity
        }


class InterruptHandler:
    """Handle interruptions gracefully"""

    def __init__(self, vad: VoiceActivityDetector):
        self.vad = vad
        self.active_responses: Set[str] = set()

    async def handle_interrupt(self, session_id: str) -> Dict:
        """Handle user interruption during agent response"""
        session_info = self.vad.get_session_info(session_id)
        if not session_info:
            return {"error": "Session not found"}

        interrupt_count = session_info["interrupt_count"]

        # Adaptive responses based on interrupt frequency - now more natural
        import random
        if interrupt_count == 1:
            response_text = random.choice([
                "Oh sorry! Yeah, what's up?",
                "My bad - go ahead!",
                "Oops, what were you saying?",
                "Sorry about that! What's going on?"
            ])
        elif interrupt_count == 2:
            response_text = random.choice([
                "Yeah, totally - what's up?",
                "Sure thing! What do you need?",
                "Of course! Go for it.",
                "Absolutely - I'm listening!"
            ])
        else:
            response_text = random.choice([
                "Got it - what's up?",
                "Yeah, go ahead!",
                "I'm all ears!",
                "What's going on?"
            ])

        # Generate quick response for interruption
        return {
            "action": "interrupt_response",
            "text": response_text,
            "audio_url": None,  # Would use cached audio for speed
            "session_state": session_info
        }

    async def generate_interrupt_response(self, session_id: str, audio_service) -> Optional[str]:
        """Generate audio response for interruption using cached responses"""
        try:
            # Use pre-cached "thinking" or "hold" response for speed
            base_url = "https://your-app-url.com"  # Would be passed in
            cached_url = await audio_service.get_cached_audio_url("thinking", base_url)

            if cached_url:
                logger.info(f"Using cached interrupt response for session {session_id}")
                return cached_url

            # Fallback: generate quick response
            interrupt_text = "Sorry, go ahead."
            return await audio_service.generate_audio_file_streaming(interrupt_text, base_url)

        except Exception as e:
            logger.error(f"Error generating interrupt response: {e}")
            return None

    def should_cancel_response(self, session_id: str, response_id: str) -> bool:
        """Check if current response should be cancelled due to interrupt"""
        return not self.vad.is_response_valid(session_id, response_id)


class CallFlowManager:
    """Manage the overall call flow with VAD and interrupt handling"""

    def __init__(self):
        self.vad = VoiceActivityDetector()
        self.interrupt_handler = InterruptHandler(self.vad)

    async def start_call(self, phone_number: str) -> str:
        """Initialize a new call session"""
        session_id = self.vad.create_session(phone_number)
        return session_id

    async def process_speech_event(self, session_id: str, event_type: str, speech_result: str = None) -> Dict:
        """Process speech events from Twilio with topic monitoring"""
        if event_type == "speech_start":
            is_interrupt = self.vad.detect_speech_start(session_id)
            if is_interrupt:
                return await self.interrupt_handler.handle_interrupt(session_id)

        elif event_type == "speech_end":
            speech_ended = self.vad.detect_speech_end(session_id)
            if speech_ended and speech_result:
                # Check topic relevance before processing
                topic_result = await self.check_topic_compliance(session_id, speech_result)

                if topic_result["action"] in ["hangup_polite", "hangup_immediate"]:
                    return topic_result
                elif topic_result["action"] in ["warn_gentle", "warn_firm"]:
                    # Return warning but continue call
                    return {
                        "action": "topic_warning",
                        "text": speech_result,
                        "session_id": session_id,
                        "warning_response": topic_result["response"],
                        "warning_level": topic_result["action"]
                    }
                else:
                    # Topic is acceptable, proceed normally
                    return {
                        "action": "process_query",
                        "text": speech_result,
                        "session_id": session_id
                    }

        return {"action": "continue_listening"}

    async def start_response(self, session_id: str) -> Optional[str]:
        """Start agent response if conditions allow"""
        if self.vad.can_start_response(session_id):
            return self.vad.start_agent_response(session_id)
        return None

    async def end_response(self, session_id: str):
        """End agent response and return to listening"""
        self.vad.end_agent_response(session_id)

    async def check_topic_compliance(self, session_id: str, speech_text: str) -> Dict:
        """Check if speech complies with topic guidelines"""
        try:
            # Analyze the query with topic guard
            analysis = topic_guard.analyze_query(speech_text, session_id)

            # Get escalated response based on session history
            response_text, suggested_action = topic_guard.get_escalated_response(session_id, analysis)

            # Update session state based on analysis
            if session_id in self.vad.active_sessions:
                session = self.vad.active_sessions[session_id]

                if analysis.suggested_action in [CallAction.WARN_GENTLE, CallAction.WARN_FIRM]:
                    session.off_topic_warnings += 1
                    session.topic_violations += 1
                    self.vad.update_session_state(session_id, CallState.WARNED)

                elif analysis.suggested_action in [CallAction.HANGUP_POLITE, CallAction.HANGUP_IMMEDIATE]:
                    session.should_terminate = True
                    self.vad.update_session_state(session_id, CallState.FLAGGED)

            # Check if should force hangup based on pattern
            if topic_guard.should_hangup(session_id):
                suggested_action = CallAction.HANGUP_POLITE
                response_text = topic_guard._get_hangup_response()

            logger.info(f"Topic analysis for session {session_id}: {analysis.relevance.value} "
                       f"-> {suggested_action.value}")

            return {
                "action": suggested_action.value,
                "response": response_text,
                "relevance": analysis.relevance.value,
                "confidence": analysis.confidence,
                "reason": analysis.reason
            }

        except Exception as e:
            logger.error(f"Error in topic compliance check: {e}")
            return {
                "action": "continue",
                "response": "Let's keep this focused on Stateira Labs. How can I help?",
                "relevance": "unknown",
                "confidence": 0.0,
                "reason": f"Analysis error: {e}"
            }

    async def force_hangup(self, session_id: str, reason: str = "Policy violation") -> Dict:
        """Force immediate call termination"""
        if session_id in self.vad.active_sessions:
            session = self.vad.active_sessions[session_id]
            session.should_terminate = True
            self.vad.update_session_state(session_id, CallState.ENDED)

            logger.warning(f"Force hangup for session {session_id}: {reason}")

            return {
                "action": "hangup_immediate",
                "response": "I need to end this call now. Thanks for calling Stateira Labs.",
                "reason": reason
            }

        return {"action": "continue", "response": "Call session not found."}

    async def get_session_topic_stats(self, session_id: str) -> Dict:
        """Get topic compliance statistics for a session"""
        if session_id not in self.vad.active_sessions:
            return {"error": "Session not found"}

        session = self.vad.active_sessions[session_id]

        return {
            "session_id": session_id,
            "off_topic_warnings": session.off_topic_warnings,
            "topic_violations": session.topic_violations,
            "should_terminate": session.should_terminate,
            "call_duration": time.time() - session.created_at,
            "current_state": session.state.value
        }

    async def end_call(self, session_id: str):
        """Clean up call session"""
        # Clean up topic guard tracking
        topic_guard.cleanup_session(session_id)
        # Clean up VAD tracking
        self.vad.cleanup_session(session_id)


# Global call flow manager
call_flow_manager = CallFlowManager()