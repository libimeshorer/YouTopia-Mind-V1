"""Communication style analyzer"""

# TODO: Understand where and how to use. Update logic accordingly.

import re
from typing import List, Dict, Optional
from collections import Counter
import statistics

from src.personality.profile import PersonalityProfile, CommunicationStyle
from src.utils.logging import get_logger
from src.utils.aws import save_personality_profile_to_s3, load_personality_profile_from_s3

logger = get_logger(__name__)


class StyleAnalyzer:
    """Analyzer for extracting communication style and personality traits"""
    
    def __init__(self):
        self.profile = None
    
    def analyze_texts(self, texts: List[str]) -> PersonalityProfile:
        """Analyze a collection of texts to extract personality profile"""
        if not texts:
            logger.warning("No texts provided for analysis")
            return PersonalityProfile()
        
        logger.info("Analyzing texts for personality", text_count=len(texts))
        
        # Combine all texts
        combined_text = " ".join(texts)
        
        # Analyze communication style
        communication_style = self._analyze_communication_style(texts)
        
        # Analyze writing patterns
        writing_patterns = self._analyze_writing_patterns(texts)
        
        # Analyze tone
        tone_characteristics = self._analyze_tone(combined_text)
        
        # Extract common phrases
        common_phrases = self._extract_common_phrases(texts)
        
        # Update communication style with common phrases
        communication_style.common_phrases = common_phrases
        
        # Create profile
        profile = PersonalityProfile(
            communication_style=communication_style,
            writing_patterns=writing_patterns,
            tone_characteristics=tone_characteristics,
            data_sources_count=len(texts),
        )
        
        self.profile = profile
        logger.info("Personality analysis completed")
        return profile
    
    def _analyze_communication_style(self, texts: List[str]) -> CommunicationStyle:
        """Analyze communication style from texts"""
        all_sentences = []
        punctuation_counts = Counter()
        decision_keywords = {
            "analytical": ["analyze", "consider", "evaluate", "assess", "examine"],
            "intuitive": ["feel", "sense", "intuition", "gut", "instinct"],
            "collaborative": ["we", "team", "together", "collaborate", "discuss"],
            "decisive": ["decide", "choose", "determine", "conclude", "final"],
        }
        
        decision_scores = {key: 0 for key in decision_keywords}
        detail_indicators = {
            "high": ["detailed", "comprehensive", "thorough", "in-depth", "extensive"],
            "low": ["brief", "summary", "overview", "high-level", "quick"],
        }
        detail_scores = {key: 0 for key in detail_indicators}
        directness_indicators = {
            "direct": ["clearly", "obviously", "definitely", "certainly", "absolutely"],
            "indirect": ["perhaps", "maybe", "might", "could", "possibly"],
        }
        directness_scores = {key: 0 for key in directness_indicators}
        
        for text in texts:
            # Split into sentences
            sentences = re.split(r'[.!?]+', text)
            all_sentences.extend([s.strip() for s in sentences if s.strip()])
            
            # Count punctuation
            punctuation_counts.update(re.findall(r'[.,!?;:—]', text))
            
            text_lower = text.lower()
            
            # Analyze decision-making style
            for style, keywords in decision_keywords.items():
                for keyword in keywords:
                    decision_scores[style] += text_lower.count(keyword)
            
            # Analyze detail level
            for level, indicators in detail_indicators.items():
                for indicator in indicators:
                    detail_scores[level] += text_lower.count(indicator)
            
            # Analyze directness
            for level, indicators in directness_indicators.items():
                for indicator in indicators:
                    directness_scores[level] += text_lower.count(indicator)
        
        # Calculate average sentence length
        sentence_lengths = [len(s.split()) for s in all_sentences if s]
        avg_sentence_length = statistics.mean(sentence_lengths) if sentence_lengths else 15.0
        
        # Determine formality (simple heuristic based on sentence structure and vocabulary)
        formal_indicators = ["therefore", "furthermore", "moreover", "consequently", "accordingly"]
        casual_indicators = ["hey", "yeah", "gonna", "wanna", "gotta"]
        formality_score = 0
        for text in texts:
            text_lower = text.lower()
            formality_score += sum(text_lower.count(ind) for ind in formal_indicators)
            formality_score -= sum(text_lower.count(ind) for ind in casual_indicators)
        
        if formality_score > 5:
            formality = "formal"
        elif formality_score < -5:
            formality = "casual"
        else:
            formality = "medium"
        
        # Determine decision-making style
        max_decision = max(decision_scores.items(), key=lambda x: x[1])
        decision_style = max_decision[0] if max_decision[1] > 0 else "analytical"
        
        # Determine detail level
        max_detail = max(detail_scores.items(), key=lambda x: x[1])
        detail_level = max_detail[0] if max_detail[1] > 0 else "medium"
        
        # Determine directness
        if directness_scores["direct"] > directness_scores["indirect"]:
            directness = "direct"
        elif directness_scores["indirect"] > directness_scores["direct"]:
            directness = "indirect"
        else:
            directness = "medium"
        
        # Calculate punctuation style
        total_punctuation = sum(punctuation_counts.values())
        punctuation_style = {
            punct: count / total_punctuation if total_punctuation > 0 else 0
            for punct, count in punctuation_counts.items()
        }
        
        return CommunicationStyle(
            formality_level=formality,
            sentence_length_avg=avg_sentence_length,
            punctuation_style=punctuation_style,
            decision_making_style=decision_style,
            detail_level=detail_level,
            directness=directness,
        )
    
    def _analyze_writing_patterns(self, texts: List[str]) -> Dict:
        """Analyze writing patterns"""
        patterns = {
            "avg_word_length": 0,
            "avg_paragraph_length": 0,
            "question_frequency": 0,
            "exclamation_frequency": 0,
        }
        
        all_words = []
        paragraphs = []
        question_count = 0
        exclamation_count = 0
        
        for text in texts:
            # Word analysis
            words = re.findall(r'\b\w+\b', text)
            all_words.extend(words)
            
            # Paragraph analysis
            text_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            paragraphs.extend(text_paragraphs)
            
            # Question and exclamation
            question_count += len(re.findall(r'\?', text))
            exclamation_count += len(re.findall(r'!', text))
        
        if all_words:
            patterns["avg_word_length"] = statistics.mean([len(w) for w in all_words])
        
        if paragraphs:
            patterns["avg_paragraph_length"] = statistics.mean([len(p.split()) for p in paragraphs])
        
        total_chars = sum(len(t) for t in texts)
        if total_chars > 0:
            patterns["question_frequency"] = question_count / (total_chars / 1000)
            patterns["exclamation_frequency"] = exclamation_count / (total_chars / 1000)
        
        return patterns
    
    def _analyze_tone(self, text: str) -> Dict[str, float]:
        """Analyze tone characteristics"""
        tone_keywords = {
            "positive": ["great", "excellent", "good", "wonderful", "amazing", "fantastic"],
            "negative": ["bad", "terrible", "awful", "horrible", "worst", "disappointing"],
            "neutral": ["okay", "fine", "acceptable", "adequate", "sufficient"],
            "professional": ["please", "thank you", "appreciate", "regards", "sincerely"],
            "friendly": ["hi", "hello", "hey", "thanks", "cheers", "best"],
        }
        
        text_lower = text.lower()
        tone_scores = {}
        
        for tone, keywords in tone_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            tone_scores[tone] = score
        
        # Normalize scores
        total = sum(tone_scores.values())
        if total > 0:
            tone_scores = {k: v / total for k, v in tone_scores.items()}
        
        return tone_scores
    
    def _extract_common_phrases(self, texts: List[str], min_occurrences: int = 3) -> List[str]:
        """Extract commonly used phrases"""
        # Simple bigram extraction
        phrases = []
        for text in texts:
            words = text.lower().split()
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                phrases.append(phrase)
        
        phrase_counts = Counter(phrases)
        common_phrases = [
            phrase for phrase, count in phrase_counts.items()
            if count >= min_occurrences
        ]
        
        # Return top 20 most common
        return [p[0] for p in phrase_counts.most_common(20)]
    
    def update_profile_from_new_data(self, new_texts: List[str]) -> PersonalityProfile:
        """Update existing profile with new data"""
        if not self.profile:
            return self.analyze_texts(new_texts)
        
        # Re-analyze with existing and new data
        # In a real implementation, you'd want to merge intelligently
        # For now, we'll re-analyze everything
        logger.info("Updating profile with new data", new_text_count=len(new_texts))
        self.profile.data_sources_count += len(new_texts)
        self.profile.update_timestamp()
        
        return self.profile
    
    def save_profile(self, s3_key: str = "profiles/personality_profile.json") -> bool:
        """Save profile to S3"""
        if not self.profile:
            logger.warning("No profile to save")
            return False
        
        return save_personality_profile_to_s3(self.profile.to_dict(), s3_key)
    
    def load_profile(self, s3_key: str = "profiles/personality_profile.json") -> Optional[PersonalityProfile]:
        """Load profile from S3"""
        profile_data = load_personality_profile_from_s3(s3_key)
        if profile_data:
            self.profile = PersonalityProfile.from_dict(profile_data)
            logger.info("Profile loaded from S3", s3_key=s3_key)
            return self.profile
        return None

