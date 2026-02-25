"""
Smart Topic Guardian System
Monitors conversations for relevance and handles off-topic/inappropriate calls
"""

import time
import logging
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TopicRelevance(Enum):
    HIGHLY_RELEVANT = "highly_relevant"      # Direct business questions
    SOMEWHAT_RELEVANT = "somewhat_relevant"  # Adjacent topics
    OFF_TOPIC = "off_topic"                 # Unrelated but harmless
    INAPPROPRIATE = "inappropriate"          # Spam, abuse, nonsense
    TIME_WASTING = "time_wasting"           # Intentional waste of time


class CallAction(Enum):
    CONTINUE = "continue"
    WARN_GENTLE = "warn_gentle"
    WARN_FIRM = "warn_firm"
    HANGUP_POLITE = "hangup_polite"
    HANGUP_IMMEDIATE = "hangup_immediate"


@dataclass
class TopicAnalysis:
    relevance: TopicRelevance
    confidence: float
    reason: str
    suggested_action: CallAction
    response_override: Optional[str] = None


class SmartTopicGuard:
    def __init__(self):
        # Stateira Labs relevant topics
        self.business_keywords = [
            # Core business
            "stateira", "labs", "software", "development", "tech", "technology",
            "crypto", "cryptocurrency", "finance", "financial", "trading",

            # Services
            "meeting", "consultation", "demo", "call", "schedule", "book",
            "product", "service", "solution", "help", "support", "question",

            # General business inquiries
            "price", "cost", "pricing", "quote", "estimate", "information",
            "about", "company", "team", "contact", "website", "email"
        ]

        # Off-topic but harmless keywords
        self.off_topic_keywords = [
            "weather", "sports", "movie", "music", "food", "recipe",
            "travel", "vacation", "personal", "family", "hobby",
            "game", "entertainment", "celebrity", "news"
        ]

        # Inappropriate/spam indicators
        self.inappropriate_patterns = [
            # Spam/sales
            r"(?i)(free|win|winner|prize|lottery|claim|limited time)",
            r"(?i)(credit card|loan|debt|insurance|extended warranty)",
            r"(?i)(congratulations|selected|chosen|exclusive offer)",

            # Nonsense/gibberish
            r"(?i)(test|testing|hello hello|blah|random|nonsense)",
            r"[a-z]{20,}",  # Very long random strings
            r"(\w)\1{5,}",   # Repeated characters (aaaaaa)

            # Inappropriate requests
            r"(?i)(personal|private|relationship|dating|inappropriate)",
            r"(?i)(waste.*time|just.*talking|nothing.*important)",
        ]

        # Time wasting patterns
        self.time_wasting_patterns = [
            r"(?i)(just.*calling|nothing.*specific|just.*wondering)",
            r"(?i)(random|bored|killing.*time|whatever)",
            r"(?i)(test.*system|checking.*works|see.*happens)",
        ]

        # Track call patterns
        self.call_tracking: Dict[str, Dict] = {}

    def analyze_query(self, query: str, session_id: str = None) -> TopicAnalysis:
        """Analyze query relevance and determine appropriate action"""
        query_lower = query.lower().strip()

        # Update call tracking
        if session_id:
            self._update_call_tracking(session_id, query)

        # Check for inappropriate content first
        inappropriateness_score = self._check_inappropriate_content(query_lower)
        if inappropriateness_score > 0.7:
            return TopicAnalysis(
                relevance=TopicRelevance.INAPPROPRIATE,
                confidence=inappropriateness_score,
                reason="Detected spam, nonsense, or inappropriate content",
                suggested_action=CallAction.WARN_FIRM if inappropriateness_score < 0.9 else CallAction.HANGUP_IMMEDIATE,
                response_override=self._get_inappropriate_response(inappropriateness_score)
            )

        # Check for time wasting
        time_wasting_score = self._check_time_wasting(query_lower)
        if time_wasting_score > 0.6:
            return TopicAnalysis(
                relevance=TopicRelevance.TIME_WASTING,
                confidence=time_wasting_score,
                reason="Detected time-wasting behavior",
                suggested_action=CallAction.WARN_GENTLE,
                response_override="Hey, I want to make sure I'm helping you with something specific. What can Stateira Labs do for you?"
            )

        # Check business relevance
        business_score = self._calculate_business_relevance(query_lower)

        if business_score > 0.6:
            return TopicAnalysis(
                relevance=TopicRelevance.HIGHLY_RELEVANT,
                confidence=business_score,
                reason="Directly related to Stateira Labs business",
                suggested_action=CallAction.CONTINUE
            )
        elif business_score > 0.3:
            return TopicAnalysis(
                relevance=TopicRelevance.SOMEWHAT_RELEVANT,
                confidence=business_score,
                reason="Possibly business related",
                suggested_action=CallAction.CONTINUE
            )
        else:
            # Check if it's just off-topic vs completely irrelevant
            off_topic_score = self._check_off_topic(query_lower)

            if off_topic_score > 0.5:
                return TopicAnalysis(
                    relevance=TopicRelevance.OFF_TOPIC,
                    confidence=off_topic_score,
                    reason="Off-topic but harmless conversation",
                    suggested_action=CallAction.WARN_GENTLE,
                    response_override="That's interesting, but I'm here to help with Stateira Labs stuff. What can we do for you business-wise?"
                )
            else:
                return TopicAnalysis(
                    relevance=TopicRelevance.OFF_TOPIC,
                    confidence=0.8,
                    reason="Unclear or unrelated query",
                    suggested_action=CallAction.WARN_GENTLE,
                    response_override="Hmm, I'm not sure how to help with that. I'm here for Stateira Labs questions - what can we do for you?"
                )

    def _calculate_business_relevance(self, query: str) -> float:
        """Calculate how relevant the query is to business"""
        words = query.split()
        business_matches = 0

        for word in words:
            if any(keyword in word for keyword in self.business_keywords):
                business_matches += 1

        if not words:
            return 0.0

        relevance_score = business_matches / len(words)

        # Boost score for direct company mentions
        if "stateira" in query or "labs" in query:
            relevance_score += 0.3

        # Boost for business intent words
        business_intent_words = ["help", "question", "about", "service", "product", "meeting"]
        for intent_word in business_intent_words:
            if intent_word in query:
                relevance_score += 0.2

        return min(relevance_score, 1.0)

    def _check_inappropriate_content(self, query: str) -> float:
        """Check for spam, nonsense, or inappropriate content"""
        score = 0.0

        # Check against patterns
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, query):
                score += 0.4

        # Check for very short nonsense
        if len(query.strip()) < 3:
            score += 0.3

        # Check for excessive punctuation or caps
        if len(re.findall(r'[!?]{3,}', query)) > 0:
            score += 0.2

        if len(re.findall(r'[A-Z]{5,}', query)) > 0:
            score += 0.2

        # Check for gibberish (high ratio of consonants)
        consonants = len(re.findall(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]', query))
        if len(query) > 0:
            consonant_ratio = consonants / len(query)
            if consonant_ratio > 0.8:
                score += 0.3

        return min(score, 1.0)

    def _check_time_wasting(self, query: str) -> float:
        """Check for time wasting indicators"""
        score = 0.0

        for pattern in self.time_wasting_patterns:
            if re.search(pattern, query):
                score += 0.4

        # Check for very vague queries
        vague_words = ["just", "wondering", "random", "whatever", "anything", "nothing specific"]
        vague_count = sum(1 for word in vague_words if word in query)
        score += vague_count * 0.2

        return min(score, 1.0)

    def _check_off_topic(self, query: str) -> float:
        """Check if query is off-topic but harmless"""
        score = 0.0

        for keyword in self.off_topic_keywords:
            if keyword in query:
                score += 0.3

        return min(score, 1.0)

    def _update_call_tracking(self, session_id: str, query: str):
        """Track call patterns for escalating responses"""
        current_time = time.time()

        if session_id not in self.call_tracking:
            self.call_tracking[session_id] = {
                "start_time": current_time,
                "queries": [],
                "off_topic_count": 0,
                "inappropriate_count": 0,
                "total_queries": 0
            }

        tracking = self.call_tracking[session_id]
        tracking["queries"].append({
            "text": query,
            "timestamp": current_time
        })
        tracking["total_queries"] += 1

    def get_escalated_response(self, session_id: str, analysis: TopicAnalysis) -> Tuple[str, CallAction]:
        """Get escalated response based on call history"""
        if session_id not in self.call_tracking:
            return analysis.response_override or "Let's keep this focused on Stateira Labs. What can I help you with?", analysis.suggested_action

        tracking = self.call_tracking[session_id]

        # Count recent off-topic/inappropriate queries
        recent_threshold = time.time() - 120  # Last 2 minutes
        recent_off_topic = sum(1 for q in tracking["queries"][-5:]
                              if self.analyze_query(q["text"]).relevance in [TopicRelevance.OFF_TOPIC, TopicRelevance.INAPPROPRIATE])

        # Escalate based on pattern
        if recent_off_topic >= 3:
            tracking["inappropriate_count"] += 1
            return self._get_hangup_response(), CallAction.HANGUP_POLITE
        elif recent_off_topic >= 2:
            return self._get_firm_warning(), CallAction.WARN_FIRM
        elif recent_off_topic >= 1:
            return analysis.response_override or self._get_gentle_warning(), CallAction.WARN_GENTLE
        else:
            return analysis.response_override or "Let's focus on Stateira Labs. How can I help?", CallAction.CONTINUE

    def _get_inappropriate_response(self, severity: float) -> str:
        """Get response for inappropriate content"""
        if severity > 0.9:
            return "I need to end this call. Thanks for calling Stateira Labs."
        elif severity > 0.7:
            return "Let's keep this professional. I'm here to help with Stateira Labs business questions."
        else:
            return "I think we're getting off track. What can Stateira Labs help you with?"

    def _get_gentle_warning(self) -> str:
        """Get gentle warning response"""
        import random
        responses = [
            "Hey, let's focus on what Stateira Labs can do for you. What's up?",
            "I want to make sure I'm helping you with the right stuff. What do you need from us?",
            "Let's keep this about Stateira Labs - how can we help you out?",
            "Hmm, let's get back to business. What brings you to Stateira Labs today?"
        ]
        return random.choice(responses)

    def _get_firm_warning(self) -> str:
        """Get firm warning response"""
        import random
        responses = [
            "I really need to keep this focused on Stateira Labs business. Last chance - what can we help you with?",
            "This needs to be about Stateira Labs. What specific business question do you have?",
            "I'm here for Stateira Labs business only. What do you actually need help with?",
            "Let's wrap this up - what's your specific Stateira Labs question?"
        ]
        return random.choice(responses)

    def _get_hangup_response(self) -> str:
        """Get polite hangup response"""
        import random
        responses = [
            "I think we're done here. Thanks for calling Stateira Labs. Goodbye.",
            "This isn't working out. Have a good day and thanks for calling.",
            "I'm going to end this call now. Take care!",
            "Time to go. Thanks for calling Stateira Labs. Bye!"
        ]
        return random.choice(responses)

    def should_hangup(self, session_id: str) -> bool:
        """Determine if call should be terminated"""
        if session_id not in self.call_tracking:
            return False

        tracking = self.call_tracking[session_id]

        # Auto hangup conditions
        conditions = [
            # Too many inappropriate queries
            tracking["inappropriate_count"] >= 2,

            # Call too long with no business content
            (time.time() - tracking["start_time"]) > 300 and tracking["total_queries"] > 8,

            # Too many queries with no business relevance
            tracking["total_queries"] > 10 and all(
                self.analyze_query(q["text"]).relevance in [TopicRelevance.OFF_TOPIC, TopicRelevance.INAPPROPRIATE, TopicRelevance.TIME_WASTING]
                for q in tracking["queries"][-5:]
            )
        ]

        return any(conditions)

    def cleanup_session(self, session_id: str):
        """Clean up tracking data for ended session"""
        if session_id in self.call_tracking:
            tracking = self.call_tracking[session_id]
            logger.info(f"Topic Guard session {session_id} ended: "
                       f"Duration: {time.time() - tracking['start_time']:.1f}s, "
                       f"Total queries: {tracking['total_queries']}, "
                       f"Off-topic incidents: {tracking['inappropriate_count']}")
            del self.call_tracking[session_id]


# Global topic guard instance
topic_guard = SmartTopicGuard()


# Quick test functions for verification
def test_topic_analysis():
    """Test the topic analysis system"""
    test_cases = [
        # Business relevant
        ("I want to learn about Stateira Labs", TopicRelevance.HIGHLY_RELEVANT),
        ("Can I schedule a meeting?", TopicRelevance.HIGHLY_RELEVANT),
        ("What services do you offer?", TopicRelevance.HIGHLY_RELEVANT),
        ("Tell me about your crypto products", TopicRelevance.HIGHLY_RELEVANT),

        # Somewhat relevant
        ("Do you work with fintech?", TopicRelevance.SOMEWHAT_RELEVANT),
        ("I need software development help", TopicRelevance.SOMEWHAT_RELEVANT),

        # Off topic but harmless
        ("How's the weather today?", TopicRelevance.OFF_TOPIC),
        ("What's your favorite movie?", TopicRelevance.OFF_TOPIC),

        # Time wasting
        ("Just calling to see what happens", TopicRelevance.TIME_WASTING),
        ("I'm just wondering about random stuff", TopicRelevance.TIME_WASTING),

        # Inappropriate
        ("aaaaaaaaaaaaaaaaaa", TopicRelevance.INAPPROPRIATE),
        ("CONGRATULATIONS YOU WON!!!", TopicRelevance.INAPPROPRIATE),
        ("test test test hello", TopicRelevance.INAPPROPRIATE),
    ]

    print("🛡️ Topic Guard Analysis Test Results:")
    print("=" * 50)

    for query, expected in test_cases:
        analysis = topic_guard.analyze_query(query)
        status = "✅" if analysis.relevance == expected else "❌"
        print(f"{status} \"{query}\" → {analysis.relevance.value} (confidence: {analysis.confidence:.2f})")
        if analysis.response_override:
            print(f"    Response: \"{analysis.response_override}\"")

    return True


if __name__ == "__main__":
    test_topic_analysis()