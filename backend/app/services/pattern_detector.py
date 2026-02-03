"""
Pattern Detection for HEALTH-BRIDGE

Analyzes conversation and memory data to detect:
- Temporal patterns (habit changes over time)
- Recurring barriers (same issues across sessions)
- Behavioral trends (improving/declining adherence)
- Contextual triggers (weather, stress, work affecting habits)

Phase 4 Implementation
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class PatternType(Enum):
    """Types of patterns that can be detected."""
    HABIT_DECLINE = "habit_decline"           # Habit adherence dropping
    HABIT_IMPROVEMENT = "habit_improvement"    # Habit adherence improving
    RECURRING_BARRIER = "recurring_barrier"    # Same barrier mentioned multiple times
    SEASONAL_PATTERN = "seasonal_pattern"      # Weather/season affecting habits
    STRESS_CORRELATION = "stress_correlation"  # Stress linked to habit failure
    TIME_CONSTRAINT = "time_constraint"        # Work/schedule issues
    HEALTH_TREND = "health_trend"              # BP/weight/sugar trending


class Severity(Enum):
    """Severity of detected patterns."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DetectedPattern:
    """A detected pattern in user data."""
    pattern_type: PatternType
    description: str
    severity: Severity
    evidence: List[str]  # Messages/data points that support this
    detected_at: str
    recommendation: Optional[str] = None
    affected_habits: List[str] = field(default_factory=list)
    confidence: float = 0.7
    
    def to_dict(self) -> Dict:
        return {
            "type": self.pattern_type.value,
            "description": self.description,
            "severity": self.severity.value,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "affected_habits": self.affected_habits,
            "confidence": self.confidence
        }


@dataclass
class HabitStatus:
    """Status of a single habit over time."""
    name: str
    mentions: List[Dict]  # [{message, status, timestamp}]
    current_status: str  # active, struggling, stopped, unknown
    adherence_trend: str  # improving, stable, declining, unknown
    barriers: List[str]
    last_updated: str


class PatternDetector:
    """
    Detects patterns across user conversations and sessions.
    
    Works with both ConversationState and memory recalls to find:
    - Declining habits that need intervention
    - Recurring barriers that need addressing
    - Health metric trends
    - Contextual factors affecting adherence
    """
    
    def __init__(self):
        # Barrier keywords for detection
        self.barrier_keywords = {
            "time": ["busy", "no time", "work", "schedule", "hours", "late"],
            "weather": ["rain", "cold", "hot", "weather", "season", "flood"],
            "health": ["sick", "injury", "pain", "tired", "fatigue", "unwell"],
            "motivation": ["lazy", "don't feel", "can't be bothered", "forgot", "skipped"],
            "access": ["expensive", "afford", "no access", "far", "unavailable"],
            "social": ["family", "kids", "caring for", "responsibilities"],
        }
        
        # Habit keywords
        self.habit_keywords = {
            "walking": ["walk", "walking", "steps", "stroll"],
            "exercise": ["exercise", "gym", "workout", "run", "jog", "swim"],
            "diet": ["eat", "food", "diet", "salt", "sugar", "vegetable", "fruit"],
            "water": ["water", "hydrat", "drink", "fluid"],
            "sleep": ["sleep", "rest", "bed", "insomnia"],
            "medication": ["medicine", "medication", "pill", "tablet", "drug"],
            "monitoring": ["measure", "check", "monitor", "reading", "bp", "blood pressure", "weight"],
        }
        
        # Status keywords
        self.positive_status = ["doing", "following", "keeping", "maintained", "success", "good", "well", "daily", "regularly"]
        self.negative_status = ["stopped", "quit", "can't", "haven't", "struggle", "difficult", "hard", "failed", "missed", "skipped"]
    
    def analyze_session(
        self,
        messages: List[str],
        previous_patterns: List[DetectedPattern] = None
    ) -> List[DetectedPattern]:
        """
        Analyze a session's messages for patterns.
        
        Args:
            messages: List of user messages from current session
            previous_patterns: Patterns detected in earlier sessions
            
        Returns:
            List of newly detected patterns
        """
        patterns = []
        combined_text = " ".join(messages).lower()
        
        # Detect barrier patterns
        barrier_patterns = self._detect_barriers(messages)
        patterns.extend(barrier_patterns)
        
        # Detect habit status changes
        habit_patterns = self._detect_habit_changes(messages)
        patterns.extend(habit_patterns)
        
        # Check for recurring patterns from previous sessions
        if previous_patterns:
            recurring = self._detect_recurring_patterns(messages, previous_patterns)
            patterns.extend(recurring)
        
        # Detect stress correlation
        stress_patterns = self._detect_stress_correlation(messages)
        patterns.extend(stress_patterns)
        
        return patterns
    
    def analyze_memory_history(
        self,
        memories: List[Dict],
        current_session_type: str = "follow_up"
    ) -> List[DetectedPattern]:
        """
        Analyze memory history for long-term patterns.
        
        Args:
            memories: List of memory dicts from recall
            current_session_type: Type of current session
            
        Returns:
            Detected patterns from memory analysis
        """
        patterns = []
        
        if not memories:
            return patterns
        
        # Extract text from memories
        texts = []
        for mem in memories:
            if isinstance(mem, dict):
                text = mem.get("text", "")
                # Try to parse JSON content
                try:
                    parsed = json.loads(text)
                    if "user_message" in parsed:
                        texts.append(parsed["user_message"])
                    elif "habits" in parsed:
                        texts.append(str(parsed["habits"]))
                except (json.JSONDecodeError, TypeError):
                    texts.append(text)
            else:
                texts.append(str(mem))
        
        # Analyze for habit trajectory
        habit_trajectory = self._analyze_habit_trajectory(texts)
        patterns.extend(habit_trajectory)
        
        # Look for health metric trends
        health_trends = self._detect_health_trends(texts)
        patterns.extend(health_trends)
        
        return patterns
    
    def _detect_barriers(self, messages: List[str]) -> List[DetectedPattern]:
        """Detect barrier mentions in messages."""
        patterns = []
        combined = " ".join(messages).lower()
        
        detected_barriers = {}
        
        for barrier_type, keywords in self.barrier_keywords.items():
            mentions = []
            for msg in messages:
                msg_lower = msg.lower()
                if any(kw in msg_lower for kw in keywords):
                    mentions.append(msg)
            
            if mentions:
                detected_barriers[barrier_type] = mentions
        
        # Create patterns for significant barriers
        for barrier_type, mentions in detected_barriers.items():
            if len(mentions) >= 1:
                # Find affected habits
                affected = []
                for habit, keywords in self.habit_keywords.items():
                    if any(kw in combined for kw in keywords):
                        affected.append(habit)
                
                severity = Severity.MEDIUM if len(mentions) >= 2 else Severity.LOW
                
                recommendations = {
                    "time": "Consider shorter habit sessions (10 min instead of 30) or habit stacking with existing routines",
                    "weather": "Suggest indoor alternatives: home exercises, indoor walking, mall walking",
                    "health": "Modify habits to accommodate current health status, consult healthcare provider",
                    "motivation": "Break habits into smaller steps, use habit tracking, find an accountability partner",
                    "access": "Find free or low-cost alternatives, community resources, home-based options",
                    "social": "Involve family in habits, find time-efficient options, adjust expectations temporarily",
                }
                
                patterns.append(DetectedPattern(
                    pattern_type=PatternType.RECURRING_BARRIER,
                    description=f"User mentions {barrier_type}-related barriers",
                    severity=severity,
                    evidence=mentions[:3],
                    detected_at=datetime.now().isoformat(),
                    recommendation=recommendations.get(barrier_type),
                    affected_habits=affected,
                    confidence=0.7 + (0.1 * min(len(mentions), 3))
                ))
        
        return patterns
    
    def _detect_habit_changes(self, messages: List[str]) -> List[DetectedPattern]:
        """Detect changes in habit status."""
        patterns = []
        
        for habit, keywords in self.habit_keywords.items():
            habit_mentions = []
            
            for msg in messages:
                msg_lower = msg.lower()
                if any(kw in msg_lower for kw in keywords):
                    # Determine status
                    is_positive = any(pos in msg_lower for pos in self.positive_status)
                    is_negative = any(neg in msg_lower for neg in self.negative_status)
                    
                    status = "positive" if is_positive else "negative" if is_negative else "neutral"
                    habit_mentions.append({"message": msg, "status": status})
            
            if habit_mentions:
                # Check if mostly negative
                negative_count = sum(1 for m in habit_mentions if m["status"] == "negative")
                positive_count = sum(1 for m in habit_mentions if m["status"] == "positive")
                
                if negative_count > positive_count and negative_count >= 1:
                    patterns.append(DetectedPattern(
                        pattern_type=PatternType.HABIT_DECLINE,
                        description=f"User reports struggling with {habit} habit",
                        severity=Severity.MEDIUM if negative_count >= 2 else Severity.LOW,
                        evidence=[m["message"] for m in habit_mentions if m["status"] == "negative"][:3],
                        detected_at=datetime.now().isoformat(),
                        recommendation=f"Consider modifying {habit} habit or addressing barriers",
                        affected_habits=[habit],
                        confidence=0.6 + (0.1 * negative_count)
                    ))
                elif positive_count > negative_count and positive_count >= 1:
                    patterns.append(DetectedPattern(
                        pattern_type=PatternType.HABIT_IMPROVEMENT,
                        description=f"User reports success with {habit} habit",
                        severity=Severity.LOW,
                        evidence=[m["message"] for m in habit_mentions if m["status"] == "positive"][:3],
                        detected_at=datetime.now().isoformat(),
                        recommendation=f"Reinforce and potentially build on {habit} success",
                        affected_habits=[habit],
                        confidence=0.6 + (0.1 * positive_count)
                    ))
        
        return patterns
    
    def _detect_recurring_patterns(
        self,
        messages: List[str],
        previous_patterns: List[DetectedPattern]
    ) -> List[DetectedPattern]:
        """Detect patterns that recur from previous sessions."""
        patterns = []
        combined = " ".join(messages).lower()
        
        for prev in previous_patterns:
            if prev.pattern_type == PatternType.RECURRING_BARRIER:
                # Check if same barrier type mentioned again
                for evidence in prev.evidence:
                    if any(word in combined for word in evidence.lower().split()[:5]):
                        patterns.append(DetectedPattern(
                            pattern_type=PatternType.RECURRING_BARRIER,
                            description=f"Recurring issue: {prev.description}",
                            severity=Severity.HIGH,  # Escalate severity
                            evidence=prev.evidence + [f"Mentioned again in current session"],
                            detected_at=datetime.now().isoformat(),
                            recommendation=f"This barrier persists - consider more significant intervention: {prev.recommendation}",
                            affected_habits=prev.affected_habits,
                            confidence=0.85
                        ))
                        break
        
        return patterns
    
    def _detect_stress_correlation(self, messages: List[str]) -> List[DetectedPattern]:
        """Detect stress correlated with habit issues."""
        patterns = []
        combined = " ".join(messages).lower()

        stress_keywords = ["stress", "stressed", "anxious", "anxiety", "overwhelmed", "pressure", "worried", "tension"]
        has_stress = any(kw in combined for kw in stress_keywords)

        if has_stress:
            # Check if habits are also struggling (in any message, not just same message)
            struggling_habits = []
            for habit, keywords in self.habit_keywords.items():
                habit_mentioned = any(kw in combined for kw in keywords)
                has_negative = any(neg in combined for neg in self.negative_status)

                if habit_mentioned and has_negative:
                    struggling_habits.append(habit)

            # Also check if stress is directly linked to habits in same sentence
            for msg in messages:
                msg_lower = msg.lower()
                msg_has_stress = any(kw in msg_lower for kw in stress_keywords)

                if msg_has_stress:
                    for habit, keywords in self.habit_keywords.items():
                        if any(kw in msg_lower for kw in keywords):
                            if habit not in struggling_habits:
                                struggling_habits.append(habit)

            if struggling_habits:
                stress_evidence = [msg for msg in messages if any(kw in msg.lower() for kw in stress_keywords)]

                patterns.append(DetectedPattern(
                    pattern_type=PatternType.STRESS_CORRELATION,
                    description=f"Stress appears linked to difficulty with habits",
                    severity=Severity.MEDIUM,
                    evidence=stress_evidence[:2],
                    detected_at=datetime.now().isoformat(),
                    recommendation="Address stress management first - consider relaxation techniques, reduce habit expectations temporarily",
                    affected_habits=struggling_habits,
                    confidence=0.65
                ))

        return patterns
    
    def _analyze_habit_trajectory(self, texts: List[str]) -> List[DetectedPattern]:
        """Analyze habit mentions over time for trajectory."""
        patterns = []
        
        # Count positive vs negative mentions across all texts
        for habit, keywords in self.habit_keywords.items():
            positive_mentions = 0
            negative_mentions = 0
            
            for text in texts:
                text_lower = text.lower()
                if any(kw in text_lower for kw in keywords):
                    if any(pos in text_lower for pos in self.positive_status):
                        positive_mentions += 1
                    if any(neg in text_lower for neg in self.negative_status):
                        negative_mentions += 1
            
            total = positive_mentions + negative_mentions
            if total >= 2:
                if negative_mentions > positive_mentions * 2:
                    patterns.append(DetectedPattern(
                        pattern_type=PatternType.HABIT_DECLINE,
                        description=f"Historical pattern: {habit} habit shows declining adherence",
                        severity=Severity.HIGH,
                        evidence=[f"{negative_mentions} negative mentions vs {positive_mentions} positive"],
                        detected_at=datetime.now().isoformat(),
                        recommendation=f"Significant intervention needed for {habit} - consider complete habit redesign",
                        affected_habits=[habit],
                        confidence=0.75
                    ))
        
        return patterns
    
    def _detect_health_trends(self, texts: List[str]) -> List[DetectedPattern]:
        """Detect trends in health readings mentioned in texts."""
        patterns = []
        
        # Look for BP readings
        bp_readings = []
        bp_pattern = r'(\d{2,3})\s*/\s*(\d{2,3})'
        
        for text in texts:
            matches = re.findall(bp_pattern, text)
            for match in matches:
                try:
                    systolic = int(match[0])
                    diastolic = int(match[1])
                    if 70 <= systolic <= 250 and 40 <= diastolic <= 150:
                        bp_readings.append((systolic, diastolic))
                except ValueError:
                    continue
        
        if len(bp_readings) >= 2:
            # Check trend
            systolic_values = [bp[0] for bp in bp_readings]
            if systolic_values[-1] > systolic_values[0] + 10:
                patterns.append(DetectedPattern(
                    pattern_type=PatternType.HEALTH_TREND,
                    description="Blood pressure appears to be trending upward",
                    severity=Severity.HIGH,
                    evidence=[f"BP readings: {bp_readings}"],
                    detected_at=datetime.now().isoformat(),
                    recommendation="Monitor closely, consider medication review, reinforce lifestyle modifications",
                    confidence=0.7
                ))
            elif systolic_values[-1] < systolic_values[0] - 10:
                patterns.append(DetectedPattern(
                    pattern_type=PatternType.HEALTH_TREND,
                    description="Blood pressure shows improvement",
                    severity=Severity.LOW,
                    evidence=[f"BP readings: {bp_readings}"],
                    detected_at=datetime.now().isoformat(),
                    recommendation="Continue current approach, maintain lifestyle modifications",
                    confidence=0.7
                ))
        
        return patterns
    
    def get_habit_summary(self, messages: List[str]) -> Dict[str, HabitStatus]:
        """Get summary of all habit statuses from messages."""
        summary = {}
        
        for habit, keywords in self.habit_keywords.items():
            mentions = []
            barriers = []
            
            for msg in messages:
                msg_lower = msg.lower()
                if any(kw in msg_lower for kw in keywords):
                    is_positive = any(pos in msg_lower for pos in self.positive_status)
                    is_negative = any(neg in msg_lower for neg in self.negative_status)
                    status = "positive" if is_positive else "negative" if is_negative else "neutral"
                    
                    mentions.append({
                        "message": msg[:100],
                        "status": status,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Check for barriers
                    for barrier_type, barrier_kws in self.barrier_keywords.items():
                        if any(bkw in msg_lower for bkw in barrier_kws):
                            barriers.append(barrier_type)
            
            if mentions:
                positive = sum(1 for m in mentions if m["status"] == "positive")
                negative = sum(1 for m in mentions if m["status"] == "negative")
                
                if negative > positive:
                    current_status = "struggling"
                    trend = "declining"
                elif positive > negative:
                    current_status = "active"
                    trend = "improving"
                else:
                    current_status = "unknown"
                    trend = "stable"
                
                summary[habit] = HabitStatus(
                    name=habit,
                    mentions=mentions,
                    current_status=current_status,
                    adherence_trend=trend,
                    barriers=list(set(barriers)),
                    last_updated=datetime.now().isoformat()
                )
        
        return summary


# Singleton
_detector: Optional[PatternDetector] = None


def get_pattern_detector() -> PatternDetector:
    """Get or create pattern detector singleton."""
    global _detector
    if _detector is None:
        _detector = PatternDetector()
    return _detector