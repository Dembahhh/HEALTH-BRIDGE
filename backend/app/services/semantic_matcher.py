"""
Semantic Matcher for HEALTH-BRIDGE

Production-ready semantic understanding that works WITHOUT requiring LLM API calls.
Uses multiple strategies:
1. Embedding similarity (using sentence-transformers, already in your deps)
2. Synonym expansion
3. Intent classification
4. Fuzzy string matching

This is the missing layer between LLM and Regex.
"""

import re
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import os

# Try to import sentence-transformers (you already have this for ChromaDB)
try:
    from sentence_transformers import SentenceTransformer, util
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️ sentence-transformers not available, using fuzzy matching only")


class Intent(Enum):
    """User intent categories."""
    AFFIRMATIVE = "affirmative"          # yes, yeah, correct
    NEGATIVE = "negative"                # no, none, nope
    QUALIFIED_YES = "qualified_yes"      # yes but sometimes, yes with exceptions
    QUALIFIED_NO = "qualified_no"        # no except..., not really but...
    UNCERTAIN = "uncertain"              # maybe, not sure, possibly
    INFORMATIVE = "informative"          # providing information
    QUESTION = "question"                # asking something
    CLARIFICATION = "clarification"      # asking for clarification
    GREETING = "greeting"                # hello, hi
    FAREWELL = "farewell"                # bye, thanks


@dataclass
class SemanticMatch:
    """Result of semantic matching."""
    field_name: str
    value: Any
    confidence: float
    method: str  # "embedding", "synonym", "fuzzy", "pattern"
    intent: Optional[Intent] = None
    alternatives: List[Any] = None  # Other possible interpretations


    # Stop words to filter from word overlap matching
STOP_WORDS = {
    "i", "a", "an", "the", "am", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "don't", "dont", "doesn't",
    "my", "me", "mine", "we", "our", "you", "your", "he", "she", "it", "they",
    "in", "at", "to", "of", "for", "and", "or", "but", "not", "on", "with",
    "that", "this", "all", "very", "really", "just", "so", "like", "also",
    "been", "being", "would", "could", "should", "will", "can", "may",
    "about", "than", "then", "too", "much", "many", "some", "any",
}


class SemanticMatcher:
    """
    Production-ready semantic understanding for health conversations.

    Features:
    - Works offline (no API calls)
    - Fast (<50ms per match)
    - Handles typos, synonyms, and natural language
    - Provides confidence scores
    - Suggests clarifications when uncertain
    """

    def __init__(self, use_embeddings: bool = True):
        """
        Initialize semantic matcher.
        
        Args:
            use_embeddings: Whether to use sentence embeddings (slower but more accurate)
        """
        self.use_embeddings = use_embeddings and EMBEDDINGS_AVAILABLE
        self.model = None
        self.intent_cache = {}
        self.embedding_cache = {}
        
        # Initialize embeddings model if available
        if self.use_embeddings:
            try:
                # Use a small, fast model
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Semantic Matcher: Using embeddings")
            except Exception as e:
                print(f"⚠️ Could not load embedding model: {e}")
                self.use_embeddings = False
        
        # Comprehensive knowledge base
        self._init_knowledge_base()
    
    def _init_knowledge_base(self):
        """Initialize the semantic knowledge base."""
        
        # Intent patterns with examples
        self.intent_examples = {
            Intent.AFFIRMATIVE: [
                "yes", "yeah", "yep", "yup", "correct", "right", "exactly",
                "that's right", "indeed", "absolutely", "definitely", "sure",
                "of course", "certainly", "i do", "i have", "i am", "true"
            ],
            Intent.NEGATIVE: [
                "no", "nope", "nah", "none", "nothing", "not really",
                "i don't", "i dont", "don't have", "dont have", "never",
                "none that i know", "not that i know of", "i don't think so",
                "not at all", "negative", "false", "neither", "nor",
                "i'm fine", "i'm good", "i'm healthy", "all good",
                "no issues", "no problems", "nothing wrong"
            ],
            Intent.UNCERTAIN: [
                "maybe", "perhaps", "possibly", "not sure", "i think",
                "i guess", "probably", "might", "could be", "sometimes",
                "kind of", "sort of", "i believe", "supposedly"
            ],
        }
        
        # Field-specific semantic mappings
        self.field_semantics = {
            "conditions": {
                "none": [
                    "none", "no", "nothing", "healthy", "fine", "good",
                    "none that i know", "not that i know of", "i don't have any",
                    "don't have any", "no conditions", "no health issues",
                    "no problems", "all clear", "clean bill of health",
                    "i'm healthy", "perfectly healthy", "no medical conditions",
                    "nothing diagnosed", "never been diagnosed"
                ],
                "hypertension": [
                    "hypertension", "high blood pressure", "high bp", "hbp",
                    "blood pressure issues", "bp issues", "bp problems",
                    "elevated blood pressure", "elevated bp", "pressure is high",
                    "borderline high bp", "borderline hypertension",
                    "my bp is high", "doctor said high bp"
                ],
                "diabetes": [
                    "diabetes", "diabetic", "type 1", "type 2", "type1", "type2",
                    "blood sugar", "sugar issues", "sugar problems", "high sugar",
                    "glucose issues", "pre-diabetic", "prediabetic", "pre diabetic",
                    "sugar disease", "my sugar is high"
                ],
                "heart_disease": [
                    "heart disease", "heart problem", "heart issues", "heart condition",
                    "cardiac", "coronary", "heart attack", "heart failure",
                    "cardiovascular", "heart trouble", "bad heart",
                    "angina", "arrhythmia", "afib", "heart surgery"
                ],
                "cholesterol": [
                    "cholesterol", "high cholesterol", "cholesterol issues",
                    "lipid problems", "fatty liver", "triglycerides"
                ],
                "stroke": [
                    "stroke", "had a stroke", "mini stroke", "tia",
                    "brain attack", "cerebrovascular"
                ],
                "kidney_disease": [
                    "kidney disease", "kidney problems", "kidney issues",
                    "renal", "ckd", "chronic kidney", "kidney failure",
                    "dialysis", "kidney stones"
                ],
                "asthma": [
                    "asthma", "asthmatic", "breathing problems", "copd",
                    "respiratory", "inhaler", "wheezing", "bronchitis"
                ],
                "obesity": [
                    "obese", "obesity", "overweight", "morbidly obese",
                    "weight problem", "very heavy", "bmi over 30"
                ]
            },
            
            "sex": {
                "male": [
                    "male", "man", "m", "boy", "guy", "gentleman", "dude",
                    "i'm a man", "i'm a guy", "i am male", "i am a man"
                ],
                "female": [
                    "female", "woman", "f", "girl", "lady", "gal",
                    "i'm a woman", "i'm a lady", "i am female", "i am a woman"
                ]
            },
            
                        "smoking": {
                "no": [
                    "no", "never", "don't smoke", "dont smoke", "non smoker",
                    "non-smoker", "nonsmoker", "never smoked", "hate smoking",
                    "i don't", "nope", "not me", "no way",
                    # Additional natural phrases
                    "never touched", "never touched a cigarette", "never tried",
                    "don't touch cigarettes", "never have", "never did",
                    "haven't smoked", "havent smoked", "never in my life",
                    "not a smoker", "tobacco free", "smoke free"
                ],
                "yes": [
                    "yes", "i smoke", "smoker", "smoking", "cigarettes",
                    "pack a day", "half pack", "few cigarettes", "daily",
                    "regularly", "yeah i smoke", "i do smoke",
                    "smoke daily", "smoke regularly", "chain smoker"
                ],
                "former": [
                    "quit", "stopped", "gave up", "used to", "former smoker",
                    "ex smoker", "ex-smoker", "not anymore", "i quit",
                    "stopped smoking", "kicked the habit", "years ago",
                    "used to smoke", "gave it up", "no longer smoke"
                ],
                "occasionally": [
                    "occasionally", "sometimes", "socially", "rarely",
                    "once in a while", "at parties", "when drinking",
                    "not often", "few times", "now and then"
                ]
            },
            
            "alcohol": {
                "no": [
                    "no", "never", "don't drink", "dont drink", "teetotal",
                    "sober", "non drinker", "abstain", "not at all",
                    "i don't drink", "never touch alcohol"
                ],
                "occasionally": [
                    "occasionally", "sometimes", "socially", "rarely",
                    "once in a while", "not often", "seldom", "few times",
                    "social drinker", "at parties", "weekends only",
                    "couple times a month", "not much"
                ],
                "regularly": [
                    "regularly", "daily", "often", "frequently", "every day",
                    "most days", "a lot", "heavy drinker", "couple drinks a day",
                    "every night", "with dinner"
                ]
            },
            
            "family_history": {
                "none": [
                    "none", "no", "nobody", "no one", "not that i know",
                    "none that i know of", "no family history", "no one in my family",
                    "everyone is healthy", "no hereditary issues"
                ],
                "has_history": [
                    "father", "mother", "dad", "mom", "parent", "parents",
                    "grandfather", "grandmother", "grandpa", "grandma",
                    "brother", "sister", "sibling", "uncle", "aunt",
                    "family", "hereditary", "runs in the family", "genetic"
                ]
            },
            
            "activity": {
                "sedentary": [
                    "sedentary", "inactive", "don't exercise", "no exercise",
                    "sit all day", "desk job", "couch potato", "lazy",
                    "never exercise", "no physical activity", "not active"
                ],
                "light": [
                    "light", "sometimes", "occasionally", "walk a bit",
                    "not much", "here and there", "when i can"
                ],
                "moderate": [
                    "moderate", "regular", "few times a week", "walk daily",
                    "30 minutes", "exercise regularly", "gym sometimes"
                ],
                "active": [
                    "active", "very active", "daily exercise", "gym daily",
                    "athlete", "sports", "workout every day", "fit"
                ]
            },

            "weight": {
                "underweight": [
                    "underweight", "too thin", "skinny", "very thin",
                    "below normal weight", "need to gain weight"
                ],
                "normal": [
                    "normal weight", "healthy weight", "average weight",
                    "normal bmi", "balanced weight"
                ],
                "overweight": [
                    "overweight", "a bit heavy", "chubby", "heavy",
                    "above normal", "need to lose weight", "carrying extra weight"
                ],
                "obese": [
                    "obese", "very overweight", "morbidly obese",
                    "severely overweight", "obesity"
                ]
            },

            "diet": {
                "healthy": [
                    "healthy", "balanced", "clean eating", "lots of vegetables",
                    "fruits and vegetables", "whole foods", "nutritious",
                    "eat well", "healthy eating", "good diet"
                ],
                "moderate": [
                    "moderate", "average", "mixed", "try to eat healthy",
                    "sometimes healthy", "ok diet", "decent"
                ],
                "poor": [
                    "junk food", "fast food", "processed food", "unhealthy",
                    "lots of sugar", "high salt", "fried food", "takeaway",
                    "poor diet", "bad diet", "eat out a lot", "snacking"
                ],
                "traditional": [
                    "traditional", "local food", "african food", "cultural",
                    "home cooked", "traditional diet", "local dishes"
                ],
                "vegetarian": [
                    "vegetarian", "vegan", "plant based", "no meat",
                    "plant-based", "meatless"
                ]
            }
        }
        
        # Pre-compute embeddings for all reference phrases if embeddings available
        if self.use_embeddings:
            self._precompute_embeddings()
    
    def _precompute_embeddings(self):
        """Pre-compute embeddings for all reference phrases."""
        if not self.use_embeddings or self.model is None:
            return
        
        for field, categories in self.field_semantics.items():
            self.embedding_cache[field] = {}
            for category, phrases in categories.items():
                # Compute embeddings for all phrases in this category
                embeddings = self.model.encode(phrases, convert_to_tensor=True)
                self.embedding_cache[field][category] = {
                    "phrases": phrases,
                    "embeddings": embeddings
                }
    
    def classify_intent(self, text: str) -> Tuple[Intent, float]:
        """
        Classify the intent of user input.
        
        Returns:
            Tuple of (Intent, confidence)
        """
        text_lower = text.lower().strip()
        
        # Check cache
        if text_lower in self.intent_cache:
            return self.intent_cache[text_lower]
        
        best_intent = Intent.INFORMATIVE
        best_score = 0.0

        # Check for qualified patterns first ("yes but...", "no except...")
        qualified_yes_patterns = [
            r"\b(yes|yeah|yep)\b.*\b(but|except|however|although|though|sometimes)\b",
            r"\b(mostly|usually|generally)\b.*\b(yes|yeah)\b",
        ]
        qualified_no_patterns = [
            r"\b(no|nope|nah)\b.*\b(but|except|however|although|well|sometimes)\b",
            r"\b(not really|not much)\b.*\b(but|except)\b",
        ]

        for pattern in qualified_yes_patterns:
            if re.search(pattern, text_lower):
                result = (Intent.QUALIFIED_YES, 0.85)
                self.intent_cache[text_lower] = result
                return result

        for pattern in qualified_no_patterns:
            if re.search(pattern, text_lower):
                result = (Intent.QUALIFIED_NO, 0.85)
                self.intent_cache[text_lower] = result
                return result

        for intent, examples in self.intent_examples.items():
            # Check for exact or substring match
            for example in examples:
                if example == text_lower:
                    result = (intent, 1.0)
                    self.intent_cache[text_lower] = result
                    return result

                if example in text_lower:
                    score = len(example) / len(text_lower)
                    if score > best_score:
                        best_score = score
                        best_intent = intent

        # Use embeddings for better matching if available
        if self.use_embeddings and best_score < 0.7:
            text_embedding = self.model.encode(text_lower, convert_to_tensor=True)

            for intent, examples in self.intent_examples.items():
                example_embeddings = self.model.encode(examples, convert_to_tensor=True)
                similarities = util.cos_sim(text_embedding, example_embeddings)
                max_sim = float(similarities.max())

                if max_sim > best_score:
                    best_score = max_sim
                    best_intent = intent

        result = (best_intent, min(best_score, 1.0))
        self.intent_cache[text_lower] = result
        return result
    
    def match_field(
        self,
        text: str,
        field_name: str,
        context_field: str = None
    ) -> Optional[SemanticMatch]:
        """
        Match user input to a specific field value.
        
        Args:
            text: User input
            field_name: Field to match (conditions, sex, smoking, etc.)
            context_field: The field we're currently asking about
            
        Returns:
            SemanticMatch or None
        """
        if field_name not in self.field_semantics:
            return None
        
        text_lower = text.lower().strip()
        categories = self.field_semantics[field_name]
        
        best_match = None
        best_score = 0.0
        method = "pattern"
        
        # Strategy 1: Exact and substring matching
        for category, phrases in categories.items():
            for phrase in phrases:
                # Exact match
                if phrase == text_lower:
                    return SemanticMatch(
                        field_name=field_name,
                        value=self._normalize_value(field_name, category),
                        confidence=1.0,
                        method="exact",
                        intent=self.classify_intent(text)[0]
                    )
                
                # Substring match
                if phrase in text_lower:
                    score = len(phrase) / max(len(text_lower), 1)
                    if score > best_score:
                        best_score = score
                        best_match = category
                        method = "substring"
                
                # Reverse substring (text in phrase)
                if text_lower in phrase and len(text_lower) > 2:
                    score = len(text_lower) / len(phrase) * 0.9
                    if score > best_score:
                        best_score = score
                        best_match = category
                        method = "reverse_substring"
        
        # Strategy 2: Word overlap (with stop word filtering)
        text_words = set(text_lower.split()) - STOP_WORDS
        for category, phrases in categories.items():
            for phrase in phrases:
                phrase_words = set(phrase.split()) - STOP_WORDS
                if not text_words or not phrase_words:
                    continue
                overlap = len(text_words & phrase_words)
                if overlap > 0:
                    score = overlap / max(len(text_words), len(phrase_words)) * 0.85
                    if score > best_score:
                        best_score = score
                        best_match = category
                        method = "word_overlap"
        
        # Strategy 3: Embedding similarity (if available)
        if self.use_embeddings and best_score < 0.7 and field_name in self.embedding_cache:
            text_embedding = self.model.encode(text_lower, convert_to_tensor=True)
            
            for category, data in self.embedding_cache[field_name].items():
                similarities = util.cos_sim(text_embedding, data["embeddings"])
                max_sim = float(similarities.max())
                
                # Embedding similarity threshold
                if max_sim > 0.6 and max_sim > best_score:
                    best_score = max_sim
                    best_match = category
                    method = "embedding"
        
        # Strategy 4: Fuzzy matching for typos
        if best_score < 0.6:
            fuzzy_result = self._fuzzy_match(text_lower, field_name)
            if fuzzy_result and fuzzy_result[1] > best_score:
                best_match, best_score = fuzzy_result
                method = "fuzzy"
        
        # Return result if confidence is high enough
        if best_match and best_score >= 0.5:
            return SemanticMatch(
                field_name=field_name,
                value=self._normalize_value(field_name, best_match),
                confidence=best_score,
                method=method,
                intent=self.classify_intent(text)[0]
            )
        
        return None
    
    def _fuzzy_match(
        self,
        text: str,
        field_name: str
    ) -> Optional[Tuple[str, float]]:
        """
        Fuzzy string matching for handling typos.
        
        Uses Levenshtein distance approximation.
        """
        if field_name not in self.field_semantics:
            return None
        
        best_match = None
        best_score = 0.0
        
        for category, phrases in self.field_semantics[field_name].items():
            for phrase in phrases:
                # Simple fuzzy score based on common characters
                score = self._simple_fuzzy_score(text, phrase)
                if score > best_score:
                    best_score = score
                    best_match = category
        
        if best_score >= 0.6:
            return (best_match, best_score * 0.8)  # Reduce confidence for fuzzy
        
        return None
    
    def _simple_fuzzy_score(self, s1: str, s2: str) -> float:
        """
        Fuzzy matching using Levenshtein edit distance.
        Score = 1 - (edit_distance / max_length).
        """
        if not s1 or not s2:
            return 0.0

        s1, s2 = s1.lower(), s2.lower()

        if s1 == s2:
            return 1.0

        # Levenshtein distance via dynamic programming
        m, n = len(s1), len(s2)
        # Optimize: if lengths differ too much, score will be low
        if abs(m - n) > max(m, n) * 0.5:
            return 0.0

        prev = list(range(n + 1))
        curr = [0] * (n + 1)

        for i in range(1, m + 1):
            curr[0] = i
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    curr[j] = prev[j - 1]
                else:
                    curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
            prev, curr = curr, prev

        distance = prev[n]
        max_len = max(m, n)
        return 1.0 - (distance / max_len)
    
    def _normalize_value(self, field_name: str, category: str) -> Any:
        """Normalize matched category to standard output value."""
        
        # Map internal categories to output values
        normalizations = {
            "conditions": {
                "none": "none",
                "hypertension": "hypertension",
                "diabetes": "diabetes",
                "heart_disease": "heart disease",
                "cholesterol": "high cholesterol",
                "stroke": "stroke history",
                "kidney_disease": "kidney disease",
                "asthma": "respiratory condition",
                "obesity": "obesity"
            },
            "sex": {
                "male": "male",
                "female": "female"
            },
            "smoking": {
                "no": "no",
                "yes": "yes",
                "former": "former",
                "occasionally": "occasionally"
            },
            "alcohol": {
                "no": "no",
                "occasionally": "occasionally",
                "regularly": "regularly"
            },
            "family_history": {
                "none": "none",
                "has_history": "yes"
            },
            "activity": {
                "sedentary": "sedentary",
                "light": "light activity",
                "moderate": "moderate activity",
                "active": "very active"
            },
            "weight": {
                "underweight": "underweight",
                "normal": "normal weight",
                "overweight": "overweight",
                "obese": "obese"
            },
            "diet": {
                "healthy": "healthy diet",
                "moderate": "moderate diet",
                "poor": "poor diet",
                "traditional": "traditional diet",
                "vegetarian": "vegetarian/plant-based"
            }
        }
        
        if field_name in normalizations:
            return normalizations[field_name].get(category, category)
        
        return category
    
    def extract_all_fields(
        self,
        text: str,
        context_field: str = None
    ) -> Dict[str, SemanticMatch]:
        """
        Extract all detectable fields from text.
        
        Args:
            text: User input
            context_field: The field we're currently asking about
            
        Returns:
            Dict of field_name -> SemanticMatch
        """
        results = {}
        
        # First, classify intent
        intent, intent_confidence = self.classify_intent(text)
        
        # If it's a clear negative with context, match to context field
        if intent == Intent.NEGATIVE and context_field and intent_confidence > 0.7:
            if context_field in ["conditions", "family_history", "constraints"]:
                results[context_field] = SemanticMatch(
                    field_name=context_field,
                    value="none",
                    confidence=intent_confidence,
                    method="intent",
                    intent=intent
                )
            elif context_field in ["smoking", "alcohol"]:
                results[context_field] = SemanticMatch(
                    field_name=context_field,
                    value="no",
                    confidence=intent_confidence,
                    method="intent",
                    intent=intent
                )

        # Handle affirmative responses to context field questions
        if intent == Intent.AFFIRMATIVE and context_field and intent_confidence > 0.7:
            if context_field == "family_history":
                results[context_field] = SemanticMatch(
                    field_name=context_field,
                    value="yes",
                    confidence=intent_confidence,
                    method="intent",
                    intent=intent
                )
            elif context_field in ["smoking", "alcohol"]:
                results[context_field] = SemanticMatch(
                    field_name=context_field,
                    value="yes",
                    confidence=intent_confidence,
                    method="intent",
                    intent=intent
                )

        # Handle uncertain responses to context field questions
        if intent == Intent.UNCERTAIN and context_field and intent_confidence > 0.6:
            if context_field in ["conditions", "family_history", "constraints"]:
                results[context_field] = SemanticMatch(
                    field_name=context_field,
                    value="uncertain",
                    confidence=intent_confidence * 0.7,
                    method="intent",
                    intent=intent
                )

        # Detect family context: words like "father", "mother" + condition keywords
        # should route to family_history, not conditions
        family_words = {"father", "mother", "dad", "mom", "parent", "parents",
                        "grandfather", "grandmother", "grandpa", "grandma",
                        "brother", "sister", "uncle", "aunt", "sibling"}
        text_words_lower = set(text.lower().split())
        has_family_context = bool(text_words_lower & family_words)

        if has_family_context and "family_history" not in results:
            # Extract the condition mentioned alongside the family member
            detail = text.strip()
            results["family_history"] = SemanticMatch(
                field_name="family_history",
                value=detail,
                confidence=0.9,
                method="family_context",
                intent=intent
            )

        # Try to match each field
        for field_name in self.field_semantics.keys():
            if field_name in results:
                continue  # Already matched via intent or family context

            match = self.match_field(text, field_name, context_field)
            if match and match.confidence >= 0.5:
                # Boost score for context_field matches
                if field_name == context_field:
                    match.confidence = min(match.confidence * 1.3, 1.0)
                # Suppress conditions match when family context detected
                if field_name == "conditions" and has_family_context:
                    continue
                results[field_name] = match
        
        # Extract age separately (numeric)
        age_match = self._extract_age(text)
        if age_match:
            results["age"] = age_match
        
        return results
    
    def _extract_age(self, text: str) -> Optional[SemanticMatch]:
        """Extract age from text with semantic understanding."""
        text_lower = text.lower()
        
        # Numeric patterns
        patterns = [
            (r"\b(\d{1,3})\s*(years?\s*old|y/?o|yrs?)\b", lambda m: int(m.group(1))),
            (r"\b(?:i'?m|i am|am)\s*(\d{2,3})\b", lambda m: int(m.group(1))),
            (r"\bmid[- ]?(\d)0'?s?\b", lambda m: int(m.group(1)) * 10 + 5),
            (r"\b(early)\s*(\d)0'?s?\b", lambda m: int(m.group(2)) * 10 + 2),
            (r"\b(late)\s*(\d)0'?s?\b", lambda m: int(m.group(2)) * 10 + 8),
            (r"^(\d{2,3})$", lambda m: int(m.group(1))),
        ]
        
        for pattern, extractor in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = extractor(match)
                    if 1 <= value <= 120:
                        return SemanticMatch(
                            field_name="age",
                            value=value,
                            confidence=0.95,
                            method="pattern"
                        )
                except (ValueError, IndexError):
                    continue
        
        # Word-based age extraction
        word_ages = {
            "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
            "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9
        }
        
        # Handle "forty five" or "forty-five"
        for tens_word, tens_val in [("twenty", 20), ("thirty", 30), ("forty", 40), 
                                     ("fifty", 50), ("sixty", 60), ("seventy", 70),
                                     ("eighty", 80), ("ninety", 90)]:
            for ones_word, ones_val in [("one", 1), ("two", 2), ("three", 3), 
                                        ("four", 4), ("five", 5), ("six", 6),
                                        ("seven", 7), ("eight", 8), ("nine", 9)]:
                pattern = rf"\b{tens_word}[\s-]?{ones_word}\b"
                if re.search(pattern, text_lower):
                    return SemanticMatch(
                        field_name="age",
                        value=tens_val + ones_val,
                        confidence=0.9,
                        method="word_number"
                    )
        
        return None
    
    def get_clarification(
        self,
        text: str,
        field_name: str,
        attempt_count: int = 1
    ) -> str:
        """
        Generate a smart clarification question instead of repeating.
        
        Args:
            text: What user said
            field_name: What we're trying to extract
            attempt_count: How many times we've asked
            
        Returns:
            A rephrased question
        """
        intent, _ = self.classify_intent(text)
        
        clarifications = {
            "conditions": {
                1: f'I heard "{text}". Just to confirm - do you have any diagnosed health conditions like high blood pressure or diabetes? (yes/no)',
                2: "Let me ask differently: Has a doctor ever told you that you have hypertension, diabetes, or heart disease?",
                3: "I'll note that as no known conditions. Let's continue."
            },
            "sex": {
                1: "Are you male or female?",
                2: "For your health profile, I need to know: male or female?",
                3: "Please type 'male' or 'female'."
            },
            "smoking": {
                1: f'When you say "{text}", does that mean you currently smoke, used to smoke, or never smoked?',
                2: "Do you smoke cigarettes? (never / sometimes / daily / quit)",
                3: "I'll continue with the next question."
            },
            "alcohol": {
                1: f'Regarding alcohol - do you drink never, occasionally, or regularly?',
                2: "How often do you drink alcohol? (never / social occasions / weekly / daily)",
                3: "I'll continue with the next question."
            },
            "family_history": {
                1: "Does anyone in your immediate family (parents, siblings) have high blood pressure, diabetes, or heart disease?",
                2: "Any family history of these conditions? Just say yes or no.",
                3: "I'll note no known family history."
            }
        }
        
        if field_name in clarifications:
            attempt = min(attempt_count, 3)
            return clarifications[field_name].get(attempt, clarifications[field_name][3])
        
        return f"Could you please clarify your {field_name.replace('_', ' ')}?"


# Singleton
_matcher: Optional[SemanticMatcher] = None


def get_semantic_matcher(use_embeddings: bool = True) -> SemanticMatcher:
    """Get or create semantic matcher singleton."""
    global _matcher
    if _matcher is None:
        _matcher = SemanticMatcher(use_embeddings=use_embeddings)
    return _matcher