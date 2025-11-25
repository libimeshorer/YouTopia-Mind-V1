"""Personality profile data model"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CommunicationStyle(BaseModel):
    """Communication style characteristics"""
    formality_level: str = Field(default="medium", description="Formal, medium, casual")
    sentence_length_avg: float = Field(default=15.0, description="Average sentence length")
    punctuation_style: Dict[str, float] = Field(default_factory=dict, description="Punctuation usage patterns")
    common_phrases: List[str] = Field(default_factory=list, description="Frequently used phrases")
    decision_making_style: str = Field(default="analytical", description="Decision-making approach")
    detail_level: str = Field(default="medium", description="High, medium, low detail preference")
    directness: str = Field(default="medium", description="Direct, medium, indirect communication")


class PersonalityProfile(BaseModel):
    """Complete personality profile"""
    person_name: Optional[str] = None
    communication_style: CommunicationStyle = Field(default_factory=CommunicationStyle)
    knowledge_domains: List[str] = Field(default_factory=list, description="Areas of expertise")
    writing_patterns: Dict[str, any] = Field(default_factory=dict, description="Writing pattern analysis")
    tone_characteristics: Dict[str, float] = Field(default_factory=dict, description="Tone analysis")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    data_sources_count: int = Field(default=0, description="Number of data sources analyzed")
    
    def to_dict(self) -> Dict:
        """Convert profile to dictionary"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PersonalityProfile":
        """Create profile from dictionary"""
        return cls(**data)
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()


