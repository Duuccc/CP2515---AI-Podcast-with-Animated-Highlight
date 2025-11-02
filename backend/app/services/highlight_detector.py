from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)

class HighlightDetector:
    """
    Detect highlights in transcript based on various signals
    """
    
    # Keywords that might indicate interesting content
    INTEREST_KEYWORDS = [
        'amazing', 'incredible', 'shocking', 'unbelievable',
        'discovered', 'breakthrough', 'revolutionary', 'secret',
        'surprising', 'wow', 'interesting', 'fascinating',
        'important', 'critical', 'essential', 'key',
        'problem', 'solution', 'question', 'answer'
    ]
    
    def __init__(self, min_duration: int = 15, max_duration: int = 90):
        self.min_duration = min_duration
        self.max_duration = max_duration
    
    def detect_highlights(
        self, 
        segments: List[Dict],
        num_highlights: int = 3
    ) -> List[Dict]:
        """
        Detect highlights from transcript segments
        
        Returns list of highlights sorted by score
        """
        logger.info(f"Analyzing {len(segments)} segments for highlights")
        
        scored_segments = []
        
        for i, segment in enumerate(segments):
            score = self._calculate_segment_score(segment, i, segments)
            
            scored_segments.append({
                "segment_index": i,
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "confidence": segment.get("confidence", 0.0),
                "score": score,
                "duration": segment["end"] - segment["start"]
            })
        
        # Sort by score
        scored_segments.sort(key=lambda x: x["score"], reverse=True)
        
        # Get top highlights
        highlights = []
        for segment in scored_segments[:num_highlights * 3]:  # Get more candidates
            # Try to expand to min_duration
            highlight = self._expand_segment(segment, segments)
            
            # Check duration - use the correct key names!
            duration = highlight["end_time"] - highlight["start_time"]
            if self.min_duration <= duration <= self.max_duration:
                highlights.append(highlight)
                
            if len(highlights) >= num_highlights:
                break
        
        logger.info(f"Found {len(highlights)} highlights")
        return highlights
    
    def _calculate_segment_score(
        self, 
        segment: Dict, 
        index: int, 
        all_segments: List[Dict]
    ) -> float:
        """Calculate interest score for a segment"""
        score = 0.0
        text = segment["text"].lower()
        
        # 1. Keyword matching
        keyword_count = sum(1 for keyword in self.INTEREST_KEYWORDS if keyword in text)
        score += keyword_count * 2.0
        
        # 2. Question marks (questions are often interesting)
        score += text.count('?') * 1.5
        
        # 3. Exclamation marks (excitement)
        score += text.count('!') * 1.0
        
        # 4. Length bonus (longer segments might be more complete thoughts)
        word_count = len(text.split())
        if 20 <= word_count <= 100:
            score += 1.0
        
        # 5. Confidence bonus
        confidence = segment.get("confidence", 0.0)
        score += abs(confidence) * 0.5
        
        # 6. Position penalty (beginning segments often less interesting)
        if index < 3:
            score *= 0.8
        
        return score
    
    def _expand_segment(
        self, 
        segment: Dict, 
        all_segments: List[Dict]
    ) -> Dict:
        """Expand segment to meet minimum duration by including nearby segments"""
        start_idx = segment["segment_index"]
        current_start = segment["start"]
        current_end = segment["end"]
        current_text = segment["text"]
        
        # Expand backwards
        idx = start_idx - 1
        while idx >= 0 and (current_end - all_segments[idx]["start"]) < self.max_duration:
            if (current_end - all_segments[idx]["start"]) >= self.min_duration:
                break
            current_start = all_segments[idx]["start"]
            current_text = all_segments[idx]["text"] + " " + current_text
            idx -= 1
        
        # Expand forwards
        idx = start_idx + 1
        while idx < len(all_segments) and (all_segments[idx]["end"] - current_start) < self.max_duration:
            current_end = all_segments[idx]["end"]
            current_text = current_text + " " + all_segments[idx]["text"]
            idx += 1
            if (current_end - current_start) >= self.min_duration:
                break
        
        return {
            "start_time": current_start,
            "end_time": current_end,
            "text": current_text.strip(),
            "confidence": segment["score"] / 10.0,  # Normalize
            "reason": self._generate_reason(current_text, segment["score"])
        }
    
    def _generate_reason(self, text: str, score: float) -> str:
        """Generate human-readable reason for highlight selection"""
        reasons = []
        
        text_lower = text.lower()
        
        # Check for keywords
        found_keywords = [kw for kw in self.INTEREST_KEYWORDS if kw in text_lower]
        if found_keywords:
            reasons.append(f"Contains key phrases: {', '.join(found_keywords[:3])}")
        
        if '?' in text:
            reasons.append("Engaging question")
        
        if '!' in text:
            reasons.append("High energy content")
        
        if score > 5:
            reasons.append("High engagement score")
        
        return "; ".join(reasons) if reasons else "Selected as potential highlight"

# Singleton
_highlight_detector = None

def get_highlight_detector() -> HighlightDetector:
    global _highlight_detector
    if _highlight_detector is None:
        _highlight_detector = HighlightDetector()
    return _highlight_detector