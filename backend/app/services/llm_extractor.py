"""
LLM-Based Field Extraction for HEALTH-BRIDGE

Replaces regex patterns with intelligent extraction that understands:
- Approximate values: "around 45", "mid-40s" 
- Negative responses: "no", "none", "I don't have any"
- Implied information: "I work night shifts" → sleep issues
- Ambiguous responses that need clarification

Phase 3 Implementation:
- Uses Gemini (free tier friendly) or falls back to regex
- Extracts multiple fields from single message
- Detects urgent symptoms
- Provides confidence scores
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """Result of extracting a single field."""
    field_name: str
    value: Optional[Any]
    confidence: float  # 0.0 to 1.0
    needs_clarification: bool
    clarifying_question: Optional[str]
    source: str  # "llm" or "regex"


@dataclass
class FullExtractionResult:
    """Result of extracting all fields from a message."""
    fields: Dict[str, ExtractionResult]
    implied: Dict[str, str]  # field -> "value (reason)"
    urgent_symptoms: List[str]
    raw_text: str


class LLMExtractor:
    """
    Extracts health information from user messages.
    
    Uses Gemini for intelligent extraction, falls back to regex.
    Designed to be rate-limit friendly.
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize extractor.
        
        Args:
            use_llm: Whether to attempt LLM extraction (set False for testing)
        """
        self.use_llm = use_llm
        self.llm_client = None
        self.llm_available = False
        self.llm_type = None
        
        if use_llm:
            self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM client."""
        # Try Gemini first (better free tier)
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.llm_client = genai.GenerativeModel("gemini-1.5-flash")
                self.llm_available = True
                self.llm_type = "gemini"
                print("✅ LLM Extractor: Using Gemini")
                return
            except Exception as e:
                print(f"⚠️ Gemini init failed: {e}")
        
        # Try OpenAI as backup
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self.llm_client = OpenAI()
                self.llm_available = True
                self.llm_type = "openai"
                print("✅ LLM Extractor: Using OpenAI")
                return
            except Exception as e:
                print(f"⚠️ OpenAI init failed: {e}")
        
        print("ℹ️ LLM Extractor: Using regex fallback")
    
    def extract_all(
        self,
        message: str,
        context: List[str] = None,
        last_question_field: str = None
    ) -> FullExtractionResult:
        """
        Extract all detectable fields from a message.
        
        Args:
            message: Current user message
            context: Previous messages for context
            last_question_field: The field we just asked about
            
        Returns:
            FullExtractionResult with all extracted data
        """
        # Always check for urgent symptoms first (fast regex)
        urgent = self._detect_urgent_symptoms(message)
        
        # Try LLM extraction
        if self.llm_available and self.use_llm:
            try:
                return self._extract_with_llm(message, context, last_question_field, urgent)
            except Exception as e:
                print(f"LLM extraction failed: {e}")
        
        # Fallback to regex
        return self._extract_with_regex(message, last_question_field, urgent)
    
    def _extract_with_llm(
        self,
        message: str,
        context: List[str],
        last_question_field: str,
        urgent_symptoms: List[str]
    ) -> FullExtractionResult:
        """Extract using LLM."""
        
        context_str = ""
        if context:
            context_str = "Recent conversation:\n" + "\n".join(f"- {m}" for m in context[-3:]) + "\n\n"
        
        field_hint = ""
        if last_question_field:
            field_hint = f"Note: We just asked about '{last_question_field}', so this response likely answers that.\n\n"
        
        prompt = f"""{context_str}{field_hint}Current message: "{message}"

Extract health information from this message. Look for:
- age: numeric age (handle "around 45", "mid-40s", etc.)
- sex: male or female
- conditions: health conditions (hypertension, diabetes, heart disease, etc.) or "none"
- family_history: family health history or "none"  
- smoking: smoking status (yes/no/former/occasionally)
- alcohol: alcohol use (no/occasionally/regularly)
- diet: dietary description
- activity: physical activity level
- constraints: barriers to healthy habits

For each field found, provide:
- value: the extracted value
- confidence: 0.0-1.0 (1.0 = explicitly stated, 0.7 = clearly implied, 0.5 = inferred)
- needs_clarification: true if ambiguous

Also identify:
- implied: information implied but not stated (e.g., "night shifts" implies sleep issues)

Respond ONLY with valid JSON:
{{
  "fields": {{
    "field_name": {{"value": ..., "confidence": 0.9, "needs_clarification": false}}
  }},
  "implied": {{
    "field": "value (reason)"
  }}
}}"""

        try:
            if self.llm_type == "gemini":
                response = self.llm_client.generate_content(prompt)
                result_text = response.text
            else:
                response = self.llm_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Extract health info. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0
                )
                result_text = response.choices[0].message.content
            
            # Parse JSON
            result_text = self._clean_json(result_text)
            parsed = json.loads(result_text)
            
            # Convert to ExtractionResult objects
            fields = {}
            for name, data in parsed.get("fields", {}).items():
                if data.get("value") is not None:
                    fields[name] = ExtractionResult(
                        field_name=name,
                        value=data["value"],
                        confidence=float(data.get("confidence", 0.7)),
                        needs_clarification=data.get("needs_clarification", False),
                        clarifying_question=self._get_clarifying_question(name),
                        source="llm"
                    )
            
            return FullExtractionResult(
                fields=fields,
                implied=parsed.get("implied", {}),
                urgent_symptoms=urgent_symptoms,
                raw_text=result_text
            )
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            raise
    
    def _clean_json(self, text: str) -> str:
        """Clean LLM response to valid JSON."""
        text = text.strip()
        # Remove markdown code blocks
        if text.startswith("```"):
            text = re.sub(r"```json?\n?", "", text)
            text = text.rstrip("`")
        # Find JSON object
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return match.group()
        return text
    
    def _extract_with_regex(
        self,
        message: str,
        last_question_field: str,
        urgent_symptoms: List[str]
    ) -> FullExtractionResult:
        """Fallback regex extraction."""
        
        fields = {}
        msg_lower = message.lower().strip()
        
        # =====================
        # AGE PATTERNS
        # =====================
        age_patterns = [
            (r"\b(\d{1,3})\s*(years?\s*old|y/?o|yrs?)\b", lambda m: int(m.group(1))),
            (r"\b(?:i'?m|i am|am)\s*(\d{2,3})\b", lambda m: int(m.group(1))),
            (r"\bmid[- ]?(\d)0'?s\b", lambda m: int(m.group(1)) * 10 + 5),
            (r"\b(early)\s*(\d)0'?s\b", lambda m: int(m.group(2)) * 10 + 2),
            (r"\b(late)\s*(\d)0'?s\b", lambda m: int(m.group(2)) * 10 + 8),
            (r"^(\d{2,3})$", lambda m: int(m.group(1)) if 10 <= int(m.group(1)) <= 120 else None),
        ]
        
        for pattern, extractor in age_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                value = extractor(match)
                if value and 10 <= value <= 120:
                    fields["age"] = ExtractionResult("age", value, 0.9, False, None, "regex")
                    break
        
        # =====================
        # SEX PATTERNS
        # =====================
        if re.search(r"\b(male|man|boy)\b", msg_lower) and not re.search(r"\b(female|woman)\b", msg_lower):
            fields["sex"] = ExtractionResult("sex", "male", 0.9, False, None, "regex")
        elif re.search(r"\b(female|woman|girl)\b", msg_lower):
            fields["sex"] = ExtractionResult("sex", "female", 0.9, False, None, "regex")
        elif last_question_field == "sex":
            if msg_lower.strip() in ["m", "male"]:
                fields["sex"] = ExtractionResult("sex", "male", 0.9, False, None, "regex")
            elif msg_lower.strip() in ["f", "female"]:
                fields["sex"] = ExtractionResult("sex", "female", 0.9, False, None, "regex")
        
        # =====================
        # CONDITIONS PATTERNS
        # =====================
        conditions = []
        if re.search(r"\b(hypertension|high\s*blood\s*pressure|hbp)\b", msg_lower):
            conditions.append("hypertension")
        if re.search(r"\b(diabetes|diabetic|blood\s*sugar)\b", msg_lower):
            conditions.append("diabetes")
        if re.search(r"\b(heart\s*(disease|problem|condition|attack)|cardiac|coronary)\b", msg_lower):
            conditions.append("heart disease")
        if re.search(r"\b(high\s*cholesterol|cholesterol)\b", msg_lower):
            conditions.append("high cholesterol")
        if re.search(r"\b(stroke)\b", msg_lower):
            conditions.append("stroke history")
        
        # Check for "none" / "no" responses to conditions question
        if re.search(r"^\s*(no|none|nope|nah|nothing|don'?t\s*have\s*any|no\s*conditions?)\s*$", msg_lower):
            if last_question_field == "conditions":
                fields["conditions"] = ExtractionResult("conditions", "none", 0.9, False, None, "regex")
            elif last_question_field == "family_history":
                fields["family_history"] = ExtractionResult("family_history", "none", 0.9, False, None, "regex")
        elif conditions:
            fields["conditions"] = ExtractionResult("conditions", conditions, 0.8, False, None, "regex")
        
        # =====================
        # FAMILY HISTORY PATTERNS
        # =====================
        family_patterns = [
            r"\b(father|mother|dad|mom|parent|brother|sister|grandpa|grandma|grandfather|grandmother|uncle|aunt)\b.*\b(had|has|have|died|passed|diagnosed)\b",
            r"\bfamily\s*(history|member)\b.*\b(hypertension|diabetes|heart|stroke)\b",
            r"\b(hereditary|genetic|runs\s*in)\b",
        ]
        for pattern in family_patterns:
            if re.search(pattern, msg_lower):
                fields["family_history"] = ExtractionResult("family_history", message, 0.7, False, None, "regex")
                break
        
        # No family history
        if re.search(r"\bno\s*(family\s*)?(history|one)\b", msg_lower):
            fields["family_history"] = ExtractionResult("family_history", "none", 0.8, False, None, "regex")
        
        # =====================
        # SMOKING PATTERNS
        # =====================
        if re.search(r"\b(don'?t|never|no|non)\s*smok", msg_lower):
            fields["smoking"] = ExtractionResult("smoking", "no", 0.9, False, None, "regex")
        elif re.search(r"\b(quit|stopped|gave\s*up|former)\s*(smok|cigarette)", msg_lower):
            fields["smoking"] = ExtractionResult("smoking", "former", 0.8, False, None, "regex")
        elif re.search(r"\b(smoke|smoking|cigarette|tobacco)\b", msg_lower):
            fields["smoking"] = ExtractionResult("smoking", "yes", 0.7, False, None, "regex")
        elif last_question_field == "smoking":
            if msg_lower.strip() in ["no", "nope", "never", "nah"]:
                fields["smoking"] = ExtractionResult("smoking", "no", 0.9, False, None, "regex")
            elif msg_lower.strip() in ["yes", "yeah", "yep"]:
                fields["smoking"] = ExtractionResult("smoking", "yes", 0.9, False, None, "regex")
        
        # =====================
        # ALCOHOL PATTERNS (FIXED)
        # =====================
        if re.search(r"\b(don'?t|never|no)\s*drink", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "no", 0.9, False, None, "regex")
        elif re.search(r"\b(occasional|occasionally|sometimes|social|once\s*a\s*week|rarely|seldom)\b", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "occasionally", 0.8, False, None, "regex")
        elif re.search(r"\bdrink\b.*\b(occasional|sometimes|weekly|rarely)\b", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "occasionally", 0.8, False, None, "regex")
        elif re.search(r"\b(regular|daily|often|frequent|every\s*day|heavily|a\s*lot)\b.*\bdrink", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "regularly", 0.8, False, None, "regex")
        elif re.search(r"\bdrink\b.*\b(regular|daily|often|every\s*day)\b", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "regularly", 0.8, False, None, "regex")
        elif last_question_field == "alcohol":
            if msg_lower.strip() in ["no", "nope", "never", "nah"]:
                fields["alcohol"] = ExtractionResult("alcohol", "no", 0.9, False, None, "regex")
            elif msg_lower.strip() in ["yes", "yeah", "yep"]:
                fields["alcohol"] = ExtractionResult("alcohol", "yes", 0.7, True, "How often do you drink?", "regex")
            elif msg_lower.strip() in ["occasionally", "sometimes", "rarely", "socially"]:
                fields["alcohol"] = ExtractionResult("alcohol", "occasionally", 0.9, False, None, "regex")
        
        # =====================
        # DIET PATTERNS
        # =====================
        diet_keywords = ["eat", "food", "diet", "vegetable", "fruit", "meat", "rice", "bread", 
                        "processed", "junk", "healthy", "meal", "breakfast", "lunch", "dinner"]
        if any(kw in msg_lower for kw in diet_keywords):
            fields["diet"] = ExtractionResult("diet", message, 0.7, False, None, "regex")
        
        # =====================
        # ACTIVITY PATTERNS
        # =====================
        activity_keywords = ["exercise", "walk", "run", "gym", "sport", "active", "jog", "swim", 
                            "cycle", "workout", "fitness", "yoga", "hiking"]
        if any(kw in msg_lower for kw in activity_keywords):
            fields["activity"] = ExtractionResult("activity", message, 0.7, False, None, "regex")
        elif re.search(r"\b(don'?t|never|no)\s*(exercise|move|walk|workout)", msg_lower):
            fields["activity"] = ExtractionResult("activity", "sedentary", 0.7, False, None, "regex")
        elif re.search(r"\b(sedentary|inactive|sit\s*all\s*day|desk\s*job)\b", msg_lower):
            fields["activity"] = ExtractionResult("activity", "sedentary", 0.8, False, None, "regex")
        
        # =====================
        # CONSTRAINTS PATTERNS
        # =====================
        constraint_keywords = ["can't", "cannot", "unable", "difficult", "hard", "busy", 
                              "expensive", "afford", "no time", "no access", "work hours"]
        if any(kw in msg_lower for kw in constraint_keywords):
            fields["constraints"] = ExtractionResult("constraints", message, 0.7, False, None, "regex")
        elif re.search(r"\b(long|busy|irregular)\s*(hours?|schedule|shift)", msg_lower):
            fields["constraints"] = ExtractionResult("constraints", message, 0.7, False, None, "regex")
        elif last_question_field == "constraints" and msg_lower.strip() in ["no", "none", "nope"]:
            fields["constraints"] = ExtractionResult("constraints", "none", 0.9, False, None, "regex")
        
        # =====================
        # IMPLIED INFORMATION (FIXED)
        # =====================
        implied = {}
        
        # Night shift → sleep issues
        if re.search(r"\b(night\s*shift|overnight|graveyard|work\s*nights?|third\s*shift)\b", msg_lower):
            implied["sleep_pattern"] = "irregular (works night shifts)"
        
        # Desk job → sedentary
        if re.search(r"\b(desk\s*job|office\s*work|sit\s*all\s*day|computer\s*all\s*day|sedentary\s*job)\b", msg_lower):
            implied["activity_level"] = "likely sedentary (desk job)"
        
        # Stress mentions
        if re.search(r"\b(stress|stressed|anxious|anxiety|overwhelmed|pressure)\b", msg_lower):
            implied["stress_level"] = "elevated (mentioned stress)"
        
        # Caregiver → time constraints
        if re.search(r"\b(caregiver|caring\s*for|look\s*after|elderly\s*parent|sick\s*family)\b", msg_lower):
            implied["time_constraints"] = "limited (caregiver responsibilities)"
        
        # Budget concerns
        if re.search(r"\b(budget|afford|expensive|cost|money|cheap)\b", msg_lower):
            implied["financial_constraints"] = "mentioned financial concerns"
        
        return FullExtractionResult(
            fields=fields,
            implied=implied,
            urgent_symptoms=urgent_symptoms,
            raw_text=""
        )
    
    def _detect_urgent_symptoms(self, message: str) -> List[str]:
        """Detect urgent symptoms needing immediate attention."""
        urgent = []
        msg_lower = message.lower()
        
        patterns = [
            (r"\b(chest\s*pain|chest\s*pressure|chest\s*tight)", "chest pain"),
            (r"\b(can'?t\s*breathe|difficulty\s*breathing|short\s*of\s*breath|breathing\s*problem)", "breathing difficulty"),
            (r"\b(severe\s*headache|worst\s*headache|sudden\s*headache)", "severe headache"),
            (r"\b(blurred?\s*vision|vision\s*problem|can'?t\s*see|losing\s*vision)", "vision problems"),
            (r"\b(faint|fainting|passed?\s*out|lost\s*conscious|blackout)", "fainting"),
            (r"\b(numb|numbness|tingling|weak|weakness).{0,30}(arm|leg|face|side)", "numbness/weakness"),
            (r"\b(slurred?\s*speech|can'?t\s*speak|trouble\s*speaking|speech\s*problem)", "speech problems"),
        ]
        
        for pattern, symptom in patterns:
            if re.search(pattern, msg_lower):
                urgent.append(symptom)
        
        return urgent
    
    def _get_clarifying_question(self, field: str) -> str:
        """Get clarifying question for a field."""
        questions = {
            "age": "Could you tell me your exact age?",
            "conditions": "Could you be more specific about your health conditions?",
            "family_history": "Which family member had this condition?",
            "smoking": "How often do you smoke - daily, occasionally, or have you quit?",
            "alcohol": "About how many drinks per week?",
            "diet": "Could you describe what you typically eat in a day?",
            "activity": "How many days per week do you exercise, and for how long?",
        }
        return questions.get(field, f"Could you tell me more about your {field}?")


# Singleton
_extractor: Optional[LLMExtractor] = None


def get_extractor(use_llm: bool = True) -> LLMExtractor:
    """Get or create extractor singleton."""
    global _extractor
    if _extractor is None:
        _extractor = LLMExtractor(use_llm=use_llm)
    return _extractor