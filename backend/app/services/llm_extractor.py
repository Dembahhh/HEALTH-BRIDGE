"""
LLM-Based Field Extraction for HEALTH-BRIDGE

Production-ready extraction with multiple fallback layers:
1. LLM (Gemini/OpenAI) - Best accuracy
2. Semantic Matcher - Good accuracy, no API needed
3. Regex - Basic patterns

This ensures the system NEVER fails to understand reasonable user inputs.
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    """Result of extracting a single field."""
    field_name: str
    value: Optional[Any]
    confidence: float
    needs_clarification: bool
    clarifying_question: Optional[str]
    source: str  # "llm", "semantic", "regex"


@dataclass
class FullExtractionResult:
    """Result of extracting all fields from a message."""
    fields: Dict[str, ExtractionResult]
    implied: Dict[str, str]
    urgent_symptoms: List[str]
    raw_text: str


class LLMExtractor:
    """
    Production-ready extractor with multiple fallback layers.
    """
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.llm_client = None
        self.llm_available = False
        self.llm_type = None
        self.semantic_matcher = None
        
        # Initialize LLM
        if use_llm:
            self._init_llm()
        
        # Initialize semantic matcher (always available)
        self._init_semantic_matcher()
    
    def _init_llm(self):
        """Initialize LLM client with proper error handling."""
        # Try Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        if api_key:
            try:
                from google import genai

                self._genai_client = genai.Client(api_key=api_key)

                # Try different model names (lite first to save quota)
                models_to_try = [
                    "gemini-2.0-flash-lite",
                    "gemini-2.0-flash",
                    "gemini-1.5-flash",
                ]

                for model_name in models_to_try:
                    try:
                        response = self._genai_client.models.generate_content(
                            model=model_name, contents="Say 'ok'"
                        )
                        if response.text:
                            self.llm_available = True
                            self.llm_type = "gemini"
                            self._gemini_model = model_name
                            logger.info(f"LLM Extractor: Using {model_name}")
                            return
                    except Exception:
                        continue

                logger.warning("All Gemini models failed")

            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
        
        # Try OpenAI — skip empty or placeholder keys
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        _is_placeholder = not openai_key or openai_key.startswith("your_") or len(openai_key) < 10
        if openai_key and not _is_placeholder:
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=openai_key)
                # Test
                response = self.llm_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Say ok"}],
                    max_tokens=5
                )
                self.llm_available = True
                self.llm_type = "openai"
                logger.info("LLM Extractor: Using OpenAI")
                return
            except Exception as e:
                logger.warning(f"OpenAI init failed: {e}")
        
        logger.info("LLM unavailable for extractor, using semantic + regex fallback")
    
    def _init_semantic_matcher(self):
        """Initialize semantic matcher."""
        try:
            from app.services.semantic_matcher import get_semantic_matcher
            self.semantic_matcher = get_semantic_matcher(use_embeddings=True)
            logger.info("Semantic Matcher: Initialized")
        except Exception as e:
            logger.warning(f"Semantic matcher init failed: {e}")
            self.semantic_matcher = None
    
    def extract_all(
        self,
        message: str,
        context: List[str] = None,
        last_question_field: str = None
    ) -> FullExtractionResult:
        """
        Extract all fields using SMART routing:
        1. Try semantic/regex FIRST for simple inputs (no API cost)
        2. Only use LLM for complex, multi-field messages
        """
        # Always check urgent symptoms first
        urgent = self._detect_urgent_symptoms(message)

        # SMART ROUTING: Check message complexity
        is_simple = self._is_simple_input(message)

        # Layer 1: Try Semantic FIRST for simple inputs (FREE, fast)
        if self.semantic_matcher:
            try:
                result = self._extract_with_semantic(message, last_question_field, urgent)
                if result.fields:
                    # Calculate confidence
                    max_confidence = max((f.confidence for f in result.fields.values()), default=0)
                    # If semantic is confident OR input is simple, use it without LLM
                    if max_confidence >= 0.7 or is_simple:
                        return result
            except Exception as e:
                logger.debug(f"Semantic extraction failed: {e}")

        # Layer 2: Try LLM only for complex/ambiguous inputs
        if self.llm_available and self.use_llm and not is_simple:
            try:
                result = self._extract_with_llm(message, context, last_question_field, urgent)
                if result.fields:
                    return result
            except Exception as e:
                logger.error(f"LLM extraction failed: {e}")

        # Layer 3: Regex fallback (always available)
        return self._extract_with_regex(message, last_question_field, urgent)

    def _is_simple_input(self, message: str) -> bool:
        """Detect if input is simple enough for semantic/regex only."""
        msg = message.lower().strip()
        word_count = len(msg.split())

        if word_count <= 3:
            return True

        simple_patterns = [
            r"^(yes|no|yeah|yep|nope|nah|none|male|female|m|f)$",
            r"^\d{1,3}$",
            r"^i'?m\s+\d{1,3}$",
            r"^(i\s+)?(don'?t|never|no)\s+(smoke|drink)\s*\w*$",
            r"^(i\s+)?(have\s+)?(never)\s+(smoked|drank|touched)",
            r"^(i\s+)?(smoke|drink)\s*(occasionally|sometimes|daily|regularly)?$",
            r"^(sedentary|active|moderate|light)$",
            r"^no\s*(one|body|history|issues?|problems?|conditions?)$",
            r"^(former|ex|quit|stopped)\s",
            r"^(healthy|fine|good|okay|ok)$",
            r"^not?\s*(really|much|often|at all)$",
        ]

        for pattern in simple_patterns:
            if re.search(pattern, msg):
                return True

        if word_count <= 6 and "," not in msg and " and " not in msg:
            return True

        return False

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
            context_str = "Recent messages:\n" + "\n".join(f"- {m}" for m in context[-3:]) + "\n\n"
        
        field_hint = ""
        if last_question_field:
            field_hint = f"We just asked about '{last_question_field}', so this likely answers that.\n\n"
        
        prompt = f"""{context_str}{field_hint}User said: "{message}"

Extract health information. Return JSON only:
{{
  "fields": {{
    "field_name": {{"value": "...", "confidence": 0.9}}
  }},
  "implied": {{}}
}}

Fields: age (number), sex (male/female), conditions (list or "none"), family_history, smoking (yes/no/former), alcohol (no/occasionally/regularly), diet, activity, constraints"""

        try:
            if self.llm_type == "gemini":
                response = self._genai_client.models.generate_content(
                    model=self._gemini_model, contents=prompt
                )
                result_text = response.text
            else:
                response = self.llm_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0
                )
                result_text = response.choices[0].message.content
            
            result_text = self._clean_json(result_text)
            parsed = json.loads(result_text)
            
            fields = {}
            for name, data in parsed.get("fields", {}).items():
                if data.get("value") is not None:
                    fields[name] = ExtractionResult(
                        field_name=name,
                        value=data["value"],
                        confidence=float(data.get("confidence", 0.8)),
                        needs_clarification=False,
                        clarifying_question=None,
                        source="llm"
                    )
            
            return FullExtractionResult(
                fields=fields,
                implied=parsed.get("implied", {}),
                urgent_symptoms=urgent_symptoms,
                raw_text=result_text
            )
            
        except Exception as e:
            raise Exception(f"LLM parsing failed: {e}")
    
    def _extract_with_semantic(
        self,
        message: str,
        last_question_field: str,
        urgent_symptoms: List[str]
    ) -> FullExtractionResult:
        """Extract using semantic matcher."""
        fields = {}
        matches = self.semantic_matcher.extract_all_fields(message, last_question_field)
        
        for field_name, match in matches.items():
            fields[field_name] = ExtractionResult(
                field_name=field_name,
                value=match.value,
                confidence=match.confidence,
                needs_clarification=match.confidence < 0.7,
                clarifying_question=None,
                source=f"semantic_{match.method}"
            )
        
        implied = {}
        msg_lower = message.lower()
        
        if re.search(r"\b(night\s*shift|overnight|graveyard)\b", msg_lower):
            implied["sleep_pattern"] = "irregular (works nights)"
        if re.search(r"\b(desk\s*job|office|sit\s*all\s*day)\b", msg_lower):
            implied["activity_hint"] = "likely sedentary"
        if re.search(r"\b(stress|stressed|anxious)\b", msg_lower):
            implied["stress"] = "mentioned stress"
        
        return FullExtractionResult(
            fields=fields,
            implied=implied,
            urgent_symptoms=urgent_symptoms,
            raw_text=""
        )
    
    def _extract_with_regex(
        self,
        message: str,
        last_question_field: str,
        urgent_symptoms: List[str]
    ) -> FullExtractionResult:
        """Fallback regex extraction."""
        fields = {}
        msg_lower = message.lower().strip()
        
        age_patterns = [
            (r"\b(\d{1,3})\s*(years?\s*old|y/?o|yrs?)\b", lambda m: int(m.group(1))),
            (r"\b(?:i'?m|i am)\s*(\d{2,3})\b", lambda m: int(m.group(1))),
            (r"\bmid[- ]?(\d)0'?s?\b", lambda m: int(m.group(1)) * 10 + 5),
            (r"\bin\s*my\s*(\d)0'?s?\b", lambda m: int(m.group(1)) * 10 + 5),
            (r"\b(?:turned|just turned|turning)\s*(\d{2,3})\b", lambda m: int(m.group(1))),
            (r"\baround\s*(\d{2,3})\b", lambda m: int(m.group(1))),
            (r"^(\d{2,3})$", lambda m: int(m.group(1))),
        ]
        
        for pattern, extractor in age_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    value = extractor(match)
                    if 1 <= value <= 120:
                        fields["age"] = ExtractionResult("age", value, 0.9, False, None, "regex")
                        break
                except:
                    continue
        
        if re.search(r"\b(male|man|boy|guy)\b", msg_lower):
            fields["sex"] = ExtractionResult("sex", "male", 0.9, False, None, "regex")
        elif re.search(r"\b(female|woman|girl|lady)\b", msg_lower):
            fields["sex"] = ExtractionResult("sex", "female", 0.9, False, None, "regex")
        elif last_question_field == "sex" and msg_lower in ["m", "f"]:
            fields["sex"] = ExtractionResult("sex", "male" if msg_lower == "m" else "female", 0.9, False, None, "regex")
        
        none_patterns = [
            r"^\s*(no|none|nope|nah)\s*$",
            r"\b(none|no|not)\s*(that)?\s*(i|we)?\s*(know|aware|have|think)\b",
            r"\b(don'?t|do\s*not)\s*(have|think)\b",
            r"\b(i'?m|i\s*am)\s*(healthy|fine|good|okay)\b",
            r"\bno\s*(health)?\s*(issues?|problems?|conditions?)\b",
            r"\bnot\s*really\b",
        ]
        
        is_none = any(re.search(p, msg_lower) for p in none_patterns)
        
        if is_none and last_question_field in ["conditions", "family_history", "constraints"]:
            fields[last_question_field] = ExtractionResult(last_question_field, "none", 0.85, False, None, "regex")
        elif is_none and last_question_field in ["smoking", "alcohol"]:
            fields[last_question_field] = ExtractionResult(last_question_field, "no", 0.85, False, None, "regex")
        
        conditions = []
        if re.search(r"\b(hypertension|high\s*blood\s*pressure|high\s*bp|hbp)\b", msg_lower):
            conditions.append("hypertension")
        if re.search(r"\b(diabetes|diabetic|blood\s*sugar|sugar)\b", msg_lower):
            conditions.append("diabetes")
        if re.search(r"\b(heart\s*(disease|problem|attack|condition)|cardiac)\b", msg_lower):
            conditions.append("heart disease")
        if re.search(r"\b(cholesterol|high\s*cholesterol|lipid)\b", msg_lower):
            conditions.append("high cholesterol")
        if re.search(r"\b(stroke|mini\s*stroke|tia)\b", msg_lower):
            conditions.append("stroke")
        if re.search(r"\b(kidney|renal|ckd)\b", msg_lower):
            conditions.append("kidney disease")
        if re.search(r"\b(asthma|breathing\s*problems?|copd|respiratory)\b", msg_lower):
            conditions.append("respiratory condition")

        if conditions:
            fields["conditions"] = ExtractionResult("conditions", conditions, 0.8, False, None, "regex")
        
        if re.search(r"\b(don'?t|never|no)\s*smok", msg_lower):
            fields["smoking"] = ExtractionResult("smoking", "no", 0.85, False, None, "regex")
        elif re.search(r"\b(quit|stopped|former)\b", msg_lower):
            fields["smoking"] = ExtractionResult("smoking", "former", 0.8, False, None, "regex")
        elif re.search(r"\bsmok", msg_lower):
            fields["smoking"] = ExtractionResult("smoking", "yes", 0.7, False, None, "regex")
        
        if re.search(r"\b(don'?t|never|no)\s*drink", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "no", 0.85, False, None, "regex")
        elif re.search(r"\b(occasional|sometimes|social|rarely)\b", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "occasionally", 0.8, False, None, "regex")
        elif re.search(r"\b(regular|daily|often)\b", msg_lower):
            fields["alcohol"] = ExtractionResult("alcohol", "regularly", 0.8, False, None, "regex")
        
        return FullExtractionResult(
            fields=fields,
            implied={},
            urgent_symptoms=urgent_symptoms,
            raw_text=""
        )
    
    def _detect_urgent_symptoms(self, message: str) -> List[str]:
        """Detect urgent symptoms."""
        urgent = []
        msg_lower = message.lower()
        
        patterns = [
            (r"\b(chest\s*pain|chest\s*pressure)", "chest pain"),
            (r"\b(can'?t\s*breathe|difficulty\s*breathing)", "breathing difficulty"),
            (r"\b(severe\s*headache)", "severe headache"),
            (r"\b(blurred?\s*vision)", "vision problems"),
            (r"\b(faint|passed?\s*out)", "fainting"),
            (r"\b(numb|weak).{0,20}(arm|leg|face)", "numbness/weakness"),
            (r"\b(slurred?\s*speech)", "speech problems"),
        ]
        
        for pattern, symptom in patterns:
            if re.search(pattern, msg_lower):
                urgent.append(symptom)
        
        return urgent
    
    def _clean_json(self, text: str) -> str:
        """Clean LLM response to valid JSON."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"```json?\n?", "", text)
            text = text.rstrip("`")
        match = re.search(r"\{[\s\S]*\}", text)
        return match.group() if match else text


# Singleton
_extractor: Optional[LLMExtractor] = None


def get_extractor(use_llm: bool = True) -> LLMExtractor:
    """Get or create extractor singleton."""
    global _extractor
    if _extractor is None:
        _extractor = LLMExtractor(use_llm=use_llm)
    return _extractor