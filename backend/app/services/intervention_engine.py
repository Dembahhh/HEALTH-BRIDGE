"""
Intervention Engine for HEALTH-BRIDGE

Generates proactive recommendations based on detected patterns.
Suggests alternative habits, modified approaches, and escalation paths.

Phase 4 Implementation
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.services.pattern_detector import (
    DetectedPattern, 
    PatternType, 
    Severity,
    HabitStatus
)


class InterventionType(Enum):
    """Types of interventions."""
    HABIT_MODIFICATION = "habit_modification"
    HABIT_REPLACEMENT = "habit_replacement"
    BARRIER_REMOVAL = "barrier_removal"
    MOTIVATION_BOOST = "motivation_boost"
    MEDICAL_REFERRAL = "medical_referral"
    GOAL_ADJUSTMENT = "goal_adjustment"
    SUPPORT_RECOMMENDATION = "support_recommendation"


@dataclass
class Intervention:
    """A recommended intervention."""
    intervention_type: InterventionType
    title: str
    description: str
    priority: int  # 1 = highest
    target_habit: Optional[str]
    specific_actions: List[str]
    expected_outcome: str
    requires_follow_up: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "type": self.intervention_type.value,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "target_habit": self.target_habit,
            "actions": self.specific_actions,
            "expected_outcome": self.expected_outcome,
            "requires_follow_up": self.requires_follow_up
        }


class InterventionEngine:
    """
    Generates interventions based on detected patterns.
    
    Uses pattern analysis to suggest:
    - Modified habits that address barriers
    - Alternative activities
    - Support resources
    - Escalation to healthcare providers
    """
    
    def __init__(self):
        # Habit alternatives mapping
        self.habit_alternatives = {
            "walking": {
                "weather": ["indoor walking (mall, home)", "stair climbing", "marching in place"],
                "time": ["10-minute walks 2x daily", "walking during phone calls", "parking farther away"],
                "health": ["gentle stretching", "chair exercises", "slow-paced walking"],
                "motivation": ["walking with music/podcasts", "step counting challenge", "walking buddy"],
            },
            "exercise": {
                "weather": ["home workout videos", "yoga", "resistance bands at home"],
                "time": ["7-minute HIIT", "exercise during TV commercials", "morning micro-workouts"],
                "health": ["chair exercises", "water aerobics", "physical therapy exercises"],
                "access": ["bodyweight exercises", "free YouTube workouts", "community center programs"],
            },
            "diet": {
                "time": ["meal prep on weekends", "healthy snack pre-packing", "simple one-pot meals"],
                "access": ["affordable healthy staples list", "seasonal produce focus", "community gardens"],
                "motivation": ["one healthy swap per week", "photo food diary", "cooking with family"],
            },
            "water": {
                "motivation": ["water bottle with time markers", "phone reminders", "habit stacking with meals"],
                "time": ["keep water at desk/bedside", "infused water for taste", "water before each meal"],
            },
            "medication": {
                "motivation": ["pill organizer", "phone alarms", "habit stack with meals"],
                "time": ["same time every day routine", "keep medications visible", "weekly pill prep"],
            },
            "monitoring": {
                "time": ["same time each day", "after morning routine", "before bed routine"],
                "motivation": ["tracking app", "share with family", "health diary"],
            },
        }
        
        # Escalation thresholds
        self.escalation_patterns = [
            PatternType.HEALTH_TREND,
        ]
    
    def generate_interventions(
        self,
        patterns: List[DetectedPattern],
        habit_summary: Dict[str, HabitStatus] = None
    ) -> List[Intervention]:
        """
        Generate interventions based on detected patterns.
        
        Args:
            patterns: Detected patterns from PatternDetector
            habit_summary: Current habit status summary
            
        Returns:
            List of recommended interventions, sorted by priority
        """
        interventions = []
        
        for pattern in patterns:
            pattern_interventions = self._generate_for_pattern(pattern, habit_summary)
            interventions.extend(pattern_interventions)
        
        # Add general interventions based on habit summary
        if habit_summary:
            summary_interventions = self._generate_from_summary(habit_summary)
            interventions.extend(summary_interventions)
        
        # Sort by priority
        interventions.sort(key=lambda x: x.priority)
        
        # Deduplicate by title
        seen_titles = set()
        unique_interventions = []
        for intervention in interventions:
            if intervention.title not in seen_titles:
                seen_titles.add(intervention.title)
                unique_interventions.append(intervention)
        
        return unique_interventions[:5]  # Return top 5
    
    def _generate_for_pattern(
        self,
        pattern: DetectedPattern,
        habit_summary: Dict[str, HabitStatus]
    ) -> List[Intervention]:
        """Generate interventions for a specific pattern."""
        interventions = []
        
        if pattern.pattern_type == PatternType.RECURRING_BARRIER:
            interventions.extend(self._handle_barrier_pattern(pattern))
        
        elif pattern.pattern_type == PatternType.HABIT_DECLINE:
            interventions.extend(self._handle_decline_pattern(pattern))
        
        elif pattern.pattern_type == PatternType.HABIT_IMPROVEMENT:
            interventions.extend(self._handle_improvement_pattern(pattern))
        
        elif pattern.pattern_type == PatternType.STRESS_CORRELATION:
            interventions.extend(self._handle_stress_pattern(pattern))
        
        elif pattern.pattern_type == PatternType.HEALTH_TREND:
            interventions.extend(self._handle_health_trend(pattern))
        
        return interventions
    
    def _handle_barrier_pattern(self, pattern: DetectedPattern) -> List[Intervention]:
        """Generate interventions for barrier patterns."""
        interventions = []
        
        # Extract barrier type from description
        barrier_type = None
        for bt in ["time", "weather", "health", "motivation", "access", "social"]:
            if bt in pattern.description.lower():
                barrier_type = bt
                break
        
        for habit in pattern.affected_habits:
            if habit in self.habit_alternatives and barrier_type:
                alternatives = self.habit_alternatives[habit].get(barrier_type, [])
                
                if alternatives:
                    interventions.append(Intervention(
                        intervention_type=InterventionType.HABIT_MODIFICATION,
                        title=f"Modify {habit} habit for {barrier_type} constraints",
                        description=f"Your {barrier_type} constraints are affecting {habit}. Here are alternatives that work around this barrier.",
                        priority=2 if pattern.severity == Severity.HIGH else 3,
                        target_habit=habit,
                        specific_actions=alternatives[:3],
                        expected_outcome=f"Maintain {habit} benefits despite {barrier_type} limitations",
                        requires_follow_up=True
                    ))
        
        return interventions
    
    def _handle_decline_pattern(self, pattern: DetectedPattern) -> List[Intervention]:
        """Generate interventions for declining habits."""
        interventions = []
        
        for habit in pattern.affected_habits:
            # Check severity
            if pattern.severity in [Severity.HIGH, Severity.CRITICAL]:
                interventions.append(Intervention(
                    intervention_type=InterventionType.GOAL_ADJUSTMENT,
                    title=f"Reset {habit} habit with easier goal",
                    description=f"The {habit} habit has been declining. Let's reset with a more achievable starting point.",
                    priority=1,
                    target_habit=habit,
                    specific_actions=[
                        f"Reduce {habit} goal by 50% for 2 weeks",
                        "Focus on consistency over intensity",
                        "Track completion, not perfection",
                        "Celebrate small wins"
                    ],
                    expected_outcome="Rebuild habit momentum with achievable goals",
                    requires_follow_up=True
                ))
            else:
                interventions.append(Intervention(
                    intervention_type=InterventionType.MOTIVATION_BOOST,
                    title=f"Reinvigorate {habit} habit",
                    description=f"Let's find ways to make {habit} more engaging and sustainable.",
                    priority=3,
                    target_habit=habit,
                    specific_actions=[
                        "Identify what made it work initially",
                        "Add variety or social element",
                        "Connect habit to meaningful personal goal"
                    ],
                    expected_outcome="Renewed engagement with habit",
                    requires_follow_up=True
                ))
        
        return interventions
    
    def _handle_improvement_pattern(self, pattern: DetectedPattern) -> List[Intervention]:
        """Generate interventions to build on improvements."""
        interventions = []
        
        for habit in pattern.affected_habits:
            interventions.append(Intervention(
                intervention_type=InterventionType.GOAL_ADJUSTMENT,
                title=f"Build on {habit} success",
                description=f"Great progress with {habit}! Let's consider leveling up.",
                priority=4,  # Lower priority - positive
                target_habit=habit,
                specific_actions=[
                    f"Consider increasing {habit} duration or frequency by 10-20%",
                    "Add a complementary habit",
                    "Share success strategy with others"
                ],
                expected_outcome="Sustained and enhanced habit performance",
                requires_follow_up=False
            ))
        
        return interventions
    
    def _handle_stress_pattern(self, pattern: DetectedPattern) -> List[Intervention]:
        """Generate interventions for stress-related issues."""
        interventions = []
        
        interventions.append(Intervention(
            intervention_type=InterventionType.SUPPORT_RECOMMENDATION,
            title="Address stress to support habit adherence",
            description="Stress appears to be affecting your habits. Managing stress may help with overall health goals.",
            priority=2,
            target_habit=None,
            specific_actions=[
                "Consider 5-minute daily breathing exercises",
                "Identify top stress triggers",
                "Temporarily simplify health goals",
                "Consider speaking with a counselor if stress persists"
            ],
            expected_outcome="Reduced stress impact on habit adherence",
            requires_follow_up=True
        ))
        
        # Also reduce expectations for affected habits
        for habit in pattern.affected_habits:
            interventions.append(Intervention(
                intervention_type=InterventionType.GOAL_ADJUSTMENT,
                title=f"Temporarily adjust {habit} expectations",
                description=f"During high stress, maintain {habit} at a reduced level rather than stopping completely.",
                priority=3,
                target_habit=habit,
                specific_actions=[
                    f"Reduce {habit} goal to minimum viable version",
                    "Focus on not breaking the chain",
                    "Any amount counts during stressful periods"
                ],
                expected_outcome="Habit maintained at reduced level until stress decreases",
                requires_follow_up=True
            ))
        
        return interventions
    
    def _handle_health_trend(self, pattern: DetectedPattern) -> List[Intervention]:
        """Generate interventions for health metric trends."""
        interventions = []
        
        if "upward" in pattern.description.lower() or "trending up" in pattern.description.lower():
            interventions.append(Intervention(
                intervention_type=InterventionType.MEDICAL_REFERRAL,
                title="Health metrics require attention",
                description=pattern.description,
                priority=1,
                target_habit=None,
                specific_actions=[
                    "Schedule follow-up with healthcare provider",
                    "Review current medications with doctor",
                    "Increase monitoring frequency",
                    "Double down on lifestyle modifications"
                ],
                expected_outcome="Professional guidance on managing health trend",
                requires_follow_up=True
            ))
        else:
            interventions.append(Intervention(
                intervention_type=InterventionType.MOTIVATION_BOOST,
                title="Health metrics improving - keep going!",
                description=pattern.description,
                priority=5,
                target_habit=None,
                specific_actions=[
                    "Continue current approach",
                    "Document what's working",
                    "Share progress with healthcare provider"
                ],
                expected_outcome="Sustained health improvement",
                requires_follow_up=False
            ))
        
        return interventions
    
    def _generate_from_summary(
        self,
        habit_summary: Dict[str, HabitStatus]
    ) -> List[Intervention]:
        """Generate interventions from overall habit summary."""
        interventions = []
        
        struggling_habits = [
            h for h, status in habit_summary.items()
            if status.current_status == "struggling"
        ]
        
        if len(struggling_habits) >= 3:
            interventions.append(Intervention(
                intervention_type=InterventionType.GOAL_ADJUSTMENT,
                title="Simplify - Focus on one habit at a time",
                description="Multiple habits are struggling. Research shows focusing on one habit leads to better success.",
                priority=1,
                target_habit=None,
                specific_actions=[
                    "Choose the easiest habit to restart",
                    "Put other habits on 'maintenance mode'",
                    "Rebuild one habit fully before adding another",
                    "Aim for 2 weeks of consistency before expanding"
                ],
                expected_outcome="Successful habit building through focused effort",
                requires_follow_up=True
            ))
        
        return interventions
    
    def format_intervention_message(self, interventions: List[Intervention]) -> str:
        """Format interventions into a readable message for the user."""
        if not interventions:
            return ""
        
        lines = ["📋 **Personalized Recommendations Based on Your Progress:**\n"]
        
        for i, intervention in enumerate(interventions[:3], 1):
            priority_emoji = "🔴" if intervention.priority == 1 else "🟡" if intervention.priority <= 3 else "🟢"
            
            lines.append(f"{priority_emoji} **{i}. {intervention.title}**")
            lines.append(f"   {intervention.description}")
            lines.append("   *Suggested actions:*")
            
            for action in intervention.specific_actions[:3]:
                lines.append(f"   • {action}")
            
            lines.append("")
        
        return "\n".join(lines)


# Singleton
_engine: Optional[InterventionEngine] = None


def get_intervention_engine() -> InterventionEngine:
    """Get or create intervention engine singleton."""
    global _engine
    if _engine is None:
        _engine = InterventionEngine()
    return _engine