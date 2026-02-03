"""
Document Chunker

Handles chunking of guideline documents for RAG.
Implements semantic chunking strategy as specified:
- Chunk by semantic units (guideline sections)
- Target size: 300-800 tokens
- Metadata tagging for condition, topic, and source
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Chunk:
    """
    A chunk of text with metadata for RAG.
    
    Attributes:
        content: The text content of the chunk
        metadata: Dictionary containing condition, topic, source, etc.
        chunk_id: Unique identifier for this chunk
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: str = field(default_factory=lambda: str(uuid4()))


class DocumentChunker:
    """
    Chunks health guideline documents into semantic units for RAG.
    
    Chunking Strategy (from spec):
    - Chunk by semantic units (guideline sections), around 300-800 tokens each
    - Topics: "Dietary recommendations for hypertension", "Physical activity guidelines", etc.
    - Each chunk tagged with metadata: condition, topic, source, region
    """

    def __init__(
        self,
        chunk_size: int = 2000,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target size of each chunk in characters (~100-150 tokens)
            chunk_overlap: Overlap between consecutive chunks for context
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """
        Find a natural break point (sentence end) near the target position.
        
        Prioritizes breaking at:
        1. Paragraph breaks (double newline)
        2. Sentence ends (. ! ?)
        3. Line breaks
        """
        # Look for paragraph break first
        for i in range(end, max(start + self.chunk_size // 2, 0), -1):
            if i < len(text) - 1 and text[i:i+2] == "\n\n":
                return i + 2
        
        # Look for sentence end
        for i in range(end, max(start + self.chunk_size // 2, 0), -1):
            if i < len(text) and text[i] in ".!?":
                # Make sure it's not an abbreviation
                if i + 1 < len(text) and text[i + 1] in " \n":
                    return i + 1
        
        # Fall back to line break
        for i in range(end, max(start + self.chunk_size // 2, 0), -1):
            if i < len(text) and text[i] == "\n":
                return i + 1
        
        # No good break point found, use target end
        return min(end, len(text))

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Chunk a text document into semantic units.
        
        Args:
            text: The document text to chunk
            metadata: Base metadata to attach to each chunk
            doc_id: Document identifier for chunk IDs
            
        Returns:
            List of Chunk objects
        """
        if metadata is None:
            metadata = {}
        
        if doc_id is None:
            doc_id = str(uuid4())[:8]

        chunks = []
        start = 0
        chunk_index = 0

        # Clean the text
        text = text.strip()
        
        while start < len(text):
            # Calculate target end
            end = start + self.chunk_size
            
            # Find a good break point
            if end < len(text):
                end = self._find_break_point(text, start, end)
            else:
                end = len(text)
            
            # Extract chunk content
            chunk_content = text[start:end].strip()
            
            # Only keep chunks above minimum size
            if len(chunk_content) >= self.min_chunk_size:
                chunk = Chunk(
                    content=chunk_content,
                    metadata={
                        **metadata,
                        "chunk_index": chunk_index,
                        "doc_id": doc_id,
                        "char_start": start,
                        "char_end": end,
                    },
                    chunk_id=f"{doc_id}_chunk_{chunk_index}",
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move start with overlap, ensuring forward progress
            new_start = end - self.chunk_overlap
            if new_start <= start:
                break  # No forward progress; remaining text too small
            start = new_start

        return chunks

    def chunk_guideline(
        self,
        text: str,
        condition: str,
        topic: str,
        source: str = "WHO",
        region: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Chunk a health guideline document with appropriate metadata.
        
        As per spec, each chunk is tagged with:
        - condition: hypertension, diabetes, general_ncd
        - topic: diet, activity, red_flags, sdoh
        - source: WHO, MoH, etc.
        - region: optional regional context
        
        Args:
            text: The guideline text
            condition: hypertension, diabetes, or general_ncd
            topic: diet, activity, red_flags, sdoh
            source: Source of the guideline (WHO, MoH, etc.)
            region: Optional region (e.g., "kenya", "africa")
        """
        metadata = {
            "condition": condition,
            "topic": topic,
            "source": source,
            "doc_type": "guideline",
        }
        
        if region:
            metadata["region"] = region
        
        doc_id = f"{source.lower()}_{condition}_{topic}"
        
        return self.chunk_text(text, metadata, doc_id)

    def chunk_by_sections(
        self,
        text: str,
        section_delimiter: str = "\n## ",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Chunk a document by markdown-style sections.
        
        Useful for structured guideline documents with clear section headers.
        
        Args:
            text: Document text with section headers
            section_delimiter: String that marks section boundaries
            metadata: Base metadata for all chunks
        """
        if metadata is None:
            metadata = {}
        
        sections = text.split(section_delimiter)
        chunks = []
        
        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            
            # Extract section title (first line)
            lines = section.split("\n", 1)
            section_title = lines[0].strip()
            section_content = lines[1].strip() if len(lines) > 1 else ""
            
            # If section is too long, further chunk it
            if len(section_content) > self.chunk_size * 2:
                sub_chunks = self.chunk_text(
                    section_content,
                    {**metadata, "section_title": section_title},
                    f"section_{i}",
                )
                chunks.extend(sub_chunks)
            elif len(section_content) >= self.min_chunk_size:
                chunks.append(Chunk(
                    content=f"{section_title}\n\n{section_content}",
                    metadata={
                        **metadata,
                        "section_title": section_title,
                        "chunk_index": i,
                    },
                    chunk_id=f"section_{i}_chunk_0",
                ))
        
        return chunks
