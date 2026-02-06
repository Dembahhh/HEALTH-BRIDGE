"""
Corrective RAG Critic

Implements the Corrective RAG pattern from the spec:
- After a draft answer is generated, check if statements are supported by retrieved text
- Signal low confidence if not supported
- Suggest refined queries and trigger re-retrieval if needed
"""

from typing import List, Dict, Any, Tuple


class CorrectiveRAGCritic:
    """
    Reviews generated answers for factual grounding in retrieved documents.
    
    As per spec:
    - Checks if answer statements are supported by retrieved text
    - Signals low confidence if not supported
    - Suggests refined queries for re-retrieval
    """

    def __init__(self, confidence_threshold: float = 0.6):
        """
        Initialize the critic.

        Args:
            confidence_threshold: Minimum confidence score to accept answer
        """
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def _stem_word(word: str) -> str:
        """Simple suffix-stripping stemmer (no external deps).
        Strips common English suffixes so 'smoking' matches 'smoke', etc."""
        if len(word) <= 3:
            return word
        # Order matters: try longest suffixes first
        suffixes = [
            "ation", "tion", "sion", "ment", "ness", "ance", "ence",
            "ings", "ing", "ated", "ous", "ive", "ful", "less",
            "able", "ible",
            "ed", "er", "est", "ly", "al",
            "es", "s",
        ]
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[:-len(suffix)]
        return word

    def extract_key_claims(self, answer: str) -> List[str]:
        """
        Extract key claims/statements from an answer.
        
        Args:
            answer: Generated answer text
            
        Returns:
            List of key claims to verify
        """
        # Simple extraction: split by sentences and filter
        sentences = answer.replace("!", ".").replace("?", ".").split(".")
        
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Keep substantive claims (not greetings, questions, etc.)
            if len(sentence) > 20 and not sentence.lower().startswith(("i ", "you ", "thank")):
                claims.append(sentence)
        
        return claims

    def check_claim_support(
        self,
        claim: str,
        retrieved_docs: List[Dict[str, Any]],
    ) -> Tuple[bool, float, str]:
        """
        Check if a claim is supported by retrieved documents.
        
        Args:
            claim: The claim to verify
            retrieved_docs: List of retrieved document chunks
            
        Returns:
            Tuple of (is_supported, confidence, supporting_source)
        """
        claim_lower = claim.lower()
        claim_words = set(claim_lower.split())

        # Remove common words
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "to", "of", "and", "in", "that", "for", "with", "on", "at",
                     "it", "its", "this", "or", "by", "can", "may", "should",
                     "not", "no", "but", "also", "has", "have", "had"}
        claim_words -= stopwords

        # Apply stemming for better matching ("smoking" -> "smok", "smoke" -> "smok")
        claim_stems = {self._stem_word(w) for w in claim_words}

        best_match_score = 0.0
        best_source = ""

        for doc in retrieved_docs:
            content = doc.get("content", "").lower()
            content_words = set(content.split()) - stopwords
            content_stems = {self._stem_word(w) for w in content_words}

            # Calculate overlap on stemmed words
            overlap = claim_stems & content_stems
            if claim_stems:
                match_score = len(overlap) / len(claim_stems)
            else:
                match_score = 0.0

            if match_score > best_match_score:
                best_match_score = match_score
                source = doc.get("metadata", {}).get("source", "Unknown")
                best_source = source

        is_supported = best_match_score >= 0.4  # At least 40% stemmed keyword match

        return is_supported, best_match_score, best_source

    def review_answer(
        self,
        answer: str,
        retrieved_docs: List[Dict[str, Any]],
        original_query: str,
    ) -> Dict[str, Any]:
        """
        Review a generated answer for factual grounding.
        
        Args:
            answer: Generated answer text
            retrieved_docs: Retrieved document chunks used for generation
            original_query: The original user query
            
        Returns:
            Dictionary with:
            - is_acceptable: Whether the answer passes review
            - confidence: Overall confidence score
            - unsupported_claims: List of claims not well-supported
            - suggested_refinements: Suggestions for improving retrieval
        """
        claims = self.extract_key_claims(answer)
        
        if not claims:
            return {
                "is_acceptable": True,
                "confidence": 1.0,
                "unsupported_claims": [],
                "suggested_refinements": [],
                "review_notes": "No substantive claims to verify",
            }
        
        supported_count = 0
        unsupported_claims = []
        sources_used = set()
        
        for claim in claims:
            is_supported, score, source = self.check_claim_support(claim, retrieved_docs)
            if is_supported:
                supported_count += 1
                sources_used.add(source)
            else:
                unsupported_claims.append({
                    "claim": claim,
                    "confidence": score,
                })
        
        # Calculate overall confidence
        overall_confidence = supported_count / len(claims) if claims else 1.0
        
        # Generate refinement suggestions
        suggested_refinements = []
        if overall_confidence < self.confidence_threshold:
            suggested_refinements.append(
                f"Try more specific query terms related to: {original_query}"
            )
            if unsupported_claims:
                # Suggest queries based on unsupported claims
                for unsupported in unsupported_claims[:2]:
                    suggested_refinements.append(
                        f"Add retrieval for: {unsupported['claim'][:50]}..."
                    )
        
        return {
            "is_acceptable": overall_confidence >= self.confidence_threshold,
            "confidence": overall_confidence,
            "claims_checked": len(claims),
            "claims_supported": supported_count,
            "unsupported_claims": unsupported_claims,
            "sources_used": list(sources_used),
            "suggested_refinements": suggested_refinements,
        }

    def should_retry(self, review_result: Dict[str, Any]) -> bool:
        """
        Determine if a retry with refined query is warranted.
        
        Args:
            review_result: Result from review_answer()
            
        Returns:
            True if retry is recommended
        """
        return (
            not review_result["is_acceptable"]
            and review_result["confidence"] < self.confidence_threshold
            and len(review_result.get("suggested_refinements", [])) > 0
        )
