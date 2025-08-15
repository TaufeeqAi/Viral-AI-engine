from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field
import uuid
from datetime import datetime # Import datetime for the new fields

# Pydantic model for a Tool, mirroring the SQLAlchemy model
class Tool(BaseModel):
    """Pydantic model for a single Tool, for use within AgentTool."""
    id: Optional[str] = Field(None, description="The unique ID of the tool.")
    name: str = Field(..., description="The name of the tool (e.g., 'Google Search').")
    description: Optional[str] = Field(None, description="A description of the tool's function.")
    config: Optional[Dict[str, Any]] = Field(None, description="A dictionary of configuration settings for the tool.")

# New Pydantic model for the association between an Agent and a Tool
class AgentTool(BaseModel):
    """Pydantic model for an agent's association with a tool, including its enabled status."""
    tool_id: Optional[str] = Field(None, description="The ID of the tool.")
    is_enabled: bool = Field(False, description="Whether the tool is enabled for this agent.")
    tool_details: Optional[Tool] = Field(None, description="The detailed information of the associated tool.")

class AgentSecrets(BaseModel):
    """Pydantic model for storing API keys and secrets for an agent's tools."""
    discord_bot_token: Optional[str] = None
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    serpapi_api_key: Optional[str] = None
    newsapi_org_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    quandl_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

class Settings(BaseModel):
    """Pydantic model for the nested 'settings' object in the agent config."""
    model: Optional[str] = Field(None, description="The specific LLM model name to use (e.g., 'llama3-70b-8192', 'gemini-pro', 'gpt-4').")
    temperature: float = Field(0.7, description="Temperature for LLM generation.")
    maxTokens: int = Field(8192, description="Maximum number of tokens for LLM generation.")
    secrets: AgentSecrets = Field(default_factory=AgentSecrets)
    voice: Optional[Dict[str, str]] = Field(None, description="Voice model settings.")

    class Config:
        populate_by_name = True
        extra = "forbid"

class AgentConfig(BaseModel):
    """Pydantic model for an agent's overall configuration, matching the JSON structure."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = Field(None, description="The ID of the user who owns this agent.")
    name: str
    modelProvider: str = Field(..., description="The provider of the LLM (e.g., 'anthropic', 'groq', 'google', 'openai', 'ollama').")
    
    settings: Settings = Field(..., description="LLM and other settings for the agent.")

    system: Optional[str] = Field(None, description="The persona for the agent.")

    bio: Optional[List[str]] = Field(None, description="A list of biography points.")
    lore: Optional[List[str]] = Field(None, description="Lore and background information as a list.")
    knowledge: Optional[List[str]] = Field(None, description="Specific knowledge points as a list.")
    
    # New fields for agent usage statistics
    lastUsed: Optional[datetime] = Field(None, description="Timestamp of when the agent was last used.")
    totalSessions: Optional[int] = Field(0, description="Total number of chat sessions initiated with this agent.")

    # New field to represent the agent's tools
    tools: Optional[List[AgentTool]] = Field(None, description="A list of tools associated with this agent, and their enabled status.")
    
    messageExamples: Optional[Union[List[Dict[str, Any]], List[List[Dict[str, Any]]]]] = Field(
        None, 
        description="Examples of messages for the agent. Can be flat list or nested list format."
    )
    style: Optional[Union[str, Dict[str, List[str]]]] = Field(None, description="Stylistic guidelines for the agent's responses.")

    class Config:
        populate_by_name = True
        extra = "forbid" # Keep as forbid for strict validation
