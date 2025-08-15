import logging
import asyncio
import os
import json
import uuid
from typing import Any, Dict, Tuple, Optional, List, Set
from pydantic import Field, PrivateAttr

from langchain.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from ..models.agent_config import AgentConfig, AgentSecrets, Settings, AgentTool, Tool
from ..prompts import AGENT_SYSTEM_PROMPT
from ..langgraph_agents.custom_tool_agent import create_custom_tool_agent
from ..llm_factory import create_llm
from ..db.postgres_manager import PostgresManager
from ..db.repositories.agent_repository import AgentRepository


logger = logging.getLogger(__name__)

# Define the directory where agent configs are stored.
AGENT_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")

# A system-level UUID to use for default agents, ensuring they have an owner.
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


def _load_agent_configs_from_directory() -> List[AgentConfig]:
    """
    Loads agent configurations from all JSON files found in a specified directory
    and maps them to the AgentConfig Pydantic model.
    """
    if not os.path.isdir(AGENT_CONFIG_DIR):
        logger.warning(f"Agent config directory not found at {AGENT_CONFIG_DIR}. Skipping agent creation from files.")
        return []

    agent_configs = []
    for filename in os.listdir(AGENT_CONFIG_DIR):
        if filename.endswith('.json'):
            file_path = os.path.join(AGENT_CONFIG_DIR, filename)
            try:
                config_data = None
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                except UnicodeDecodeError:
                    logger.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1 encoding.")
                    with open(file_path, 'r', encoding='latin-1') as f:
                        config_data = json.load(f)

                if config_data is None:
                    logger.error(f"Could not load data from {file_path}.")
                    continue

                settings_data = config_data.get("settings", {})
                secrets_from_json = settings_data.get("secrets", {})
                
                # Create AgentSecrets instance
                agent_secrets_instance = AgentSecrets(**secrets_from_json)

                # Create Settings instance
                settings_instance = Settings(
                    model=settings_data.get("model", "llama3-8b-8192"),
                    temperature=settings_data.get("temperature", 0.7),
                    maxTokens=settings_data.get("maxTokens", 15000),
                    secrets=agent_secrets_instance,
                )

                # Get the list of tool names from the config file, if it exists
                allowed_tool_names = config_data.get("allowed_tool_names", [])

                # Create AgentConfig instance
                agent_config = AgentConfig(
                    id=str(uuid.uuid4()), # Generate a new ID for the agent
                    user_id=SYSTEM_USER_ID,
                    name=config_data.get("name", os.path.splitext(filename)[0]),
                    modelProvider=config_data.get("modelProvider", "groq"),
                    settings=settings_instance,
                    system=config_data.get("system"),
                    bio=config_data.get("bio", []),
                    lore=config_data.get("lore", []),
                    knowledge=config_data.get("knowledge", []),
                    tools=[], # Tools will be populated dynamically
                    allowed_tool_names=allowed_tool_names
                )
                agent_configs.append(agent_config)
                logger.info(f"Successfully loaded agent config from {file_path}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from {file_path}: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred while loading agent config from {file_path}: {e}", exc_info=True)

    return agent_configs


class TelegramToolWrapper(BaseTool):
    """
    A wrapper for Telegram tools that injects API credentials into the tool's arguments.
    This allows a single Telegram MCP server to manage multiple Telegram bots.
    """
    _wrapped_tool: BaseTool = PrivateAttr()
    telegram_api_id: int = Field(..., description="Telegram API ID for the bot.")
    telegram_api_hash: str = Field(..., description="Telegram API Hash for the bot.")
    telegram_bot_token: str = Field(..., description="Telegram Bot Token.")

    def __init__(self, wrapped_tool: BaseTool, telegram_api_id: int, telegram_api_hash: str, telegram_bot_token: str, **kwargs: Any):
        super().__init__(
            name=wrapped_tool.name,
            description=wrapped_tool.description,
            args_schema=wrapped_tool.args_schema,
            return_direct=wrapped_tool.return_direct,
            func=wrapped_tool.func,
            coroutine=wrapped_tool.coroutine,
            telegram_api_id=telegram_api_id,
            telegram_api_hash=telegram_api_hash,
            telegram_bot_token=telegram_bot_token,
            **kwargs
        )
        self._wrapped_tool = wrapped_tool

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        all_kwargs = {**kwargs}
        all_kwargs['telegram_api_id'] = self.telegram_api_id
        all_kwargs['telegram_api_hash'] = self.telegram_api_hash
        all_kwargs['telegram_bot_token'] = self.telegram_bot_token

        logger.debug(f"Invoking wrapped Telegram tool '{self.name}' with injected credentials. Final Args: {all_kwargs}")
        return await self._wrapped_tool.ainvoke(all_kwargs)

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Telegram tools are asynchronous and should use _arun.")


class DiscordToolWrapper(BaseTool):
    """
    A wrapper for Discord tools that injects the bot_id into the tool's arguments.
    This allows a single Discord MCP server to manage multiple Discord bots.
    """
    _wrapped_tool: BaseTool = PrivateAttr()
    bot_id: str = Field(..., description="The Discord bot ID to use for this tool.")

    def __init__(self, wrapped_tool: BaseTool, bot_id: str, **kwargs: Any):
        super().__init__(
            name=wrapped_tool.name,
            description=wrapped_tool.description,
            args_schema=wrapped_tool.args_schema,
            return_direct=wrapped_tool.return_direct,
            func=wrapped_tool.func,
            coroutine=wrapped_tool.coroutine,
            bot_id=bot_id,
            **kwargs
        )
        self._wrapped_tool = wrapped_tool

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously runs the wrapped tool, injecting the Discord bot_id."""
        all_kwargs = {**kwargs}
        all_kwargs['bot_id'] = self.bot_id

        logger.debug(f"Invoking wrapped Discord tool '{self.name}' with injected bot_id: {self.bot_id}. Final Args: {all_kwargs}")
        return await self._wrapped_tool.ainvoke(all_kwargs)

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Discord tools are asynchronous and should use _arun.")


class AgentManager:
    """
    Manages the lifecycle, initialization, and caching of AI agents.
    This class encapsulates the _initialized_agents dictionary and provides methods
    to interact with it, as well as handle dynamic agent creation and shutdown.
    """
    def __init__(self, postgres_manager: PostgresManager):
        self._initialized_agents: Dict[str, Dict[str, Any]] = {}
        self._postgres_manager = postgres_manager
        # Access the actual repository after connection is established
        self._agent_repository: Optional[AgentRepository] = None
    
    def _ensure_repository_access(self):
        """Ensures agent repository is accessible after connection."""
        if self._agent_repository is None:
            if self._postgres_manager.agent_repo is None:
                raise RuntimeError("PostgresManager not connected. Call postgres_manager.connect() first.")
            self._agent_repository = self._postgres_manager.agent_repo
    
    def add_initialized_agent(self, agent_id: str, agent_name: str, executor: Any, mcp_client: MultiServerMCPClient,
                              tools: List[BaseTool], discord_bot_id: Optional[str] = None, telegram_bot_id: Optional[str] = None):
        """Adds an initialized agent, its MCP client, and platform-specific bot IDs to the cache."""
        agent_info = {
            "name": agent_name,
            "executor": executor,
            "mcp_client": mcp_client,
            "tools": tools,
        }
        if discord_bot_id:
            agent_info["discord_bot_id"] = discord_bot_id
        if telegram_bot_id:
            agent_info["telegram_bot_id"] = telegram_bot_id

        self._initialized_agents[agent_id] = agent_info
        logger.info(f"Agent '{agent_name}' (ID: {agent_id}) and its MCP client added to cache with {len(tools)} tools. Discord Bot ID: {discord_bot_id}, Telegram Bot ID: {telegram_bot_id}")

    def get_initialized_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an initialized agent (executor and mcp_client) from the cache."""
        return self._initialized_agents.get(agent_id)

    def get_all_initialized_agents(self) -> Dict[str, Dict[str, Any]]:
        """Returns all initialized agents from the cache."""
        return self._initialized_agents

    async def shutdown_all_agents(self):
        """Shuts down all initialized agents and their components."""
        logger.info("Shutting down all agents...")
        for agent_id, agent_info in list(self._initialized_agents.items()):
            await self.shutdown_specific_agent(agent_id)
        logger.info("All agents shut down and cache cleared.")

    async def close(self):
        """
        Shuts down all initialized agents and their associated resources,
        providing a single, unified method for graceful shutdown.
        This method is an alias for `shutdown_all_agents`.
        """
        await self.shutdown_all_agents()

    async def shutdown_specific_agent(self, agent_id: str):
        """Shuts down a specific agent and removes it from the cache."""
        agent_info = self._initialized_agents.pop(agent_id, None)
        if agent_info:
            mcp_client = agent_info.get("mcp_client")
            if mcp_client:
                await mcp_client.close()
                logger.info(f"MCP Client for agent {agent_id} closed.")

            logger.info(f"Agent {agent_id} removed from cache.")
        else:
            logger.warning(f"Attempted to shut down agent {agent_id}, but it was not found in cache.")

    async def initialize_agents_from_config(self, local_mode: bool):
        """
        Loads agent configurations from a local JSON file, initializes the agents,
        and then saves their full configurations to the database.
        
        This method is designed to be the primary startup entry point to ensure
        the database is always in sync with the source-of-truth configuration file.
        """
        try:
            # Ensure we have access to the repository
            self._ensure_repository_access()
            
            agent_configs = _load_agent_configs_from_directory()
            
            if not agent_configs:
                logger.warning("No agent configurations found in the directory. Skipping agent initialization.")
                return
            
            logger.info(f"Successfully loaded {len(agent_configs)} agent configurations from the config directory.")
            
            for agent_config in agent_configs:
                logger.info(f"Initializing agent '{agent_config.name}' from file config...")
                
                # Use the create method to build the agent and get its tools
                executor, mcp_client, discord_id, telegram_id, agent_tools = \
                    await self.create_dynamic_agent_instance(agent_config, local_mode)

                # Update the agent_config's tools list with the fetched tools' details
                agent_config.tools = [AgentTool(tool_details=Tool(name=tool.name, description=tool.description)) for tool in agent_tools]

                # Now, upsert the complete configuration to the database
                await self._agent_repository.upsert_agent_config(agent_config)
                logger.info(f"Agent '{agent_config.name}' configuration updated in DB.")
                
                # Store the initialized agent in the manager's cache
                self.add_initialized_agent(
                    agent_config.id,
                    agent_config.name,
                    executor,
                    mcp_client,
                    tools=agent_tools,
                    discord_bot_id=discord_id,
                    telegram_bot_id=telegram_id
                )

        except FileNotFoundError:
            logger.error(f"Agent configuration file not found at: {AGENT_CONFIG_DIR}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse agent configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"An error occurred during agent initialization from config: {e}", exc_info=True)
            raise

    async def create_dynamic_agent_instance(self, agent_config: AgentConfig, local_mode: bool) -> Tuple[Any, MultiServerMCPClient, Optional[str], Optional[str], List[BaseTool]]:
        """
        Dynamically creates and initializes an agent instance based on AgentConfig.
        Returns the compiled agent executor (LangGraph runnable), its associated MCPClient,
        and fetched bot IDs.
        
        This function now expects to receive a valid AgentConfig object, either
        from a file or from a pre-populated database entry.
        """
        agent_id = agent_config.id
        agent_name = agent_config.name
        llm_model_provider = agent_config.modelProvider
        llm_model_name = agent_config.settings.model
        llm_temperature = agent_config.settings.temperature
        llm_max_tokens = agent_config.settings.maxTokens
        llm_secrets = agent_config.settings.secrets
        
        agent_bio = agent_config.bio
        agent_persona = agent_config.system
        agent_knowledge = agent_config.knowledge
        agent_lore = agent_config.lore
        
        # Get the set of allowed tool names from the config.
        # This will be an empty set if the list is empty or None.
        allowed_tool_names_set = set(agent_config.allowed_tool_names or [])

        logger.info(f"Dynamically initializing agent '{agent_name}' (ID: {agent_id})...")
        logger.info(f"Allowed tool names from config: {allowed_tool_names_set}")

        # --- LLM Initialization using the factory ---
        llm_api_key = None
        if llm_model_provider == "groq":
            llm_api_key = llm_secrets.groq_api_key or os.getenv("GROQ_API_KEY")
        elif llm_model_provider == "google":
            llm_api_key = llm_secrets.google_api_key or os.getenv("GOOGLE_API_KEY")
        elif llm_model_provider == "openai":
            llm_api_key = llm_secrets.openai_api_key or os.getenv("OPENAI_API_KEY")
        elif llm_model_provider == "anthropic":
            llm_api_key = llm_secrets.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        try:
            llm = create_llm(
                provider=llm_model_provider,
                api_key=llm_api_key,
                model=llm_model_name,
                temperature=llm_temperature,
                max_tokens=llm_max_tokens
            )
            logger.info(f"✅ Initialized LLM for agent '{agent_name}': Provider={llm_model_provider}, Model={llm_model_name}")
        except ValueError as e:
            logger.error(f"Failed to initialize LLM for agent '{agent_name}': {e}", exc_info=True)
            raise

        # --- MCP Server Configuration ---
        agent_mcp_config = {
            "web_search": {"url": "http://localhost:9000/mcp/", "transport": "streamable_http"},
            "finance": {"url": "http://localhost:9001/mcp/", "transport": "streamable_http"},
            "rag": {"url": "http://localhost:9002/mcp/", "transport": "streamable_http"},
            "crawler": {"url": "http://localhost:9005/mcp/", "transport": "streamable_http"},
        }

        if not local_mode:
            agent_mcp_config["web_search"]["url"] = "http://web-mcp:9000/mcp/"
            agent_mcp_config["finance"]["url"] = "http://finance-mcp:9001/mcp/"
            agent_mcp_config["rag"]["url"] = "http://rag-mcp:9002/mcp/"
            agent_mcp_config["crawler"]["url"] = "http://crawler-mcp:9005/mcp/"

        discord_bot_id = None
        telegram_bot_id = None
        
        discord_token = llm_secrets.discord_bot_token
        discord_secrets_provided = bool(discord_token)
        if discord_secrets_provided:
            if local_mode:
                agent_mcp_config["discord"] = {"url": "http://localhost:9004/mcp/", "transport": "streamable_http"}
            else:
                agent_mcp_config["discord"] = {"url": "http://discord-mcp:9004/mcp/", "transport": "streamable_http"}
            logger.info(f"Agent '{agent_name}' will include Discord tools.")
        else:
            logger.info(f"Agent '{agent_name}' does not have Discord bot token. Discord tools will NOT be enabled.")

        telegram_token = llm_secrets.telegram_bot_token
        telegram_api_id = llm_secrets.telegram_api_id
        telegram_api_hash = llm_secrets.telegram_api_hash

        telegram_secrets_provided = (
            telegram_token and
            telegram_api_id is not None and
            telegram_api_hash
        )
        if telegram_secrets_provided:
            if local_mode:
                agent_mcp_config["telegram"] = {"url": "http://localhost:9003/mcp/", "transport": "streamable_http"}
            else:
                agent_mcp_config["telegram"] = {"url": "http://telegram-mcp:9003/mcp/", "transport": "streamable_http"}
            logger.info(f"Agent '{agent_name}' will include Telegram tools.")
        else:
            if telegram_token:
                logger.warning(f"Agent '{agent_name}' has Telegram bot token but is missing telegram_api_id or telegram_api_hash. Telegram tools will NOT be enabled.")

        mcp_client = MultiServerMCPClient(agent_mcp_config)
        
        # --- RETRY MECHANISM ---
        max_attempts = 12
        base_delay = 2
        fetched_tools_list = []
        for attempt in range(1, max_attempts + 1):
            try:
                fetched_tools_list = await mcp_client.get_tools()
                if fetched_tools_list:
                    logger.info(f"Successfully fetched {len(fetched_tools_list)} raw tools on attempt {attempt}.")
                    logger.info(f"Fetched raw tools from MCP: {[t.name for t in fetched_tools_list]}")
                    break
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed to fetch tools for agent '{agent_name}': {e}")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to fetch tools for agent '{agent_name}' after {max_attempts} attempts. Configured MCP servers might be down or inaccessible.")
                    fetched_tools_list = []
                    break
        
        # New logic: Create a dictionary for efficient lookup
        available_tools_dict = {tool.name: tool for tool in fetched_tools_list}
        agent_tools_final = []

        # Step 1: Handle platform tools first (Discord, Telegram)
        if discord_secrets_provided and "register_discord_bot" in available_tools_dict:
            register_tool = available_tools_dict["register_discord_bot"]
            try:
                logger.info(f"Calling 'register_discord_bot' for agent '{agent_name}' with token (first 5 chars): {discord_token[:5]}...")
                discord_bot_id = await register_tool.ainvoke({"bot_token": discord_token})
                logger.info(f"✅ Successfully registered Discord bot for agent '{agent_name}'. Bot ID: {discord_bot_id}")
            except Exception as e:
                logger.error(f"Failed to register Discord bot for agent '{agent_name}': {e}", exc_info=True)
                discord_bot_id = None
        elif discord_secrets_provided:
            logger.warning(f"Agent '{agent_name}' has Discord token but 'register_discord_bot' tool not found. Discord tools will NOT be enabled.")

        if telegram_secrets_provided and "register_telegram_bot" in available_tools_dict:
            register_tool = available_tools_dict["register_telegram_bot"]
            try:
                logger.info(f"Calling 'register_telegram_bot' for agent '{agent_name}' with token (first 5 chars): {telegram_token[:5]}...")
                telegram_bot_id = await register_tool.ainvoke({
                    "api_id": telegram_api_id, 
                    "api_hash": telegram_api_hash, 
                    "bot_token": telegram_token
                })
                logger.info(f"✅ Successfully registered Telegram bot for agent '{agent_name}'. Bot ID: {telegram_bot_id}")
            except Exception as e:
                logger.error(f"Failed to register Telegram bot for agent '{agent_name}': {e}", exc_info=True)
                telegram_bot_id = None
        elif telegram_secrets_provided:
            logger.warning(f"Agent '{agent_name}' has Telegram credentials but 'register_telegram_bot' tool not found. Telegram tools will NOT be enabled.")


        # Step 2: Iterate through the allowed tools and add them to the final list, wrapping them if necessary.
        if allowed_tool_names_set:
            for tool_name in allowed_tool_names_set:
                if tool_name not in available_tools_dict:
                    logger.warning(f"Configured tool '{tool_name}' not found for agent '{agent_name}'. Skipping.")
                    continue
                
                tool_item = available_tools_dict[tool_name]

                is_telegram_tool = tool_name in ["send_message_telegram", "get_chat_history_telegram", "get_bot_id_telegram"]
                is_discord_tool = tool_name in ["send_message_discord", "get_channel_messages_discord", "get_bot_id_discord"]

                if is_telegram_tool and telegram_secrets_provided:
                    try:
                        telegram_api_id_int = int(telegram_api_id) if telegram_api_id is not None else 0
                    except (ValueError, TypeError):
                        logger.error(f"Invalid or missing telegram_api_id for agent '{agent_name}'. Skipping Telegram tool wrapping.")
                        continue
                    
                    wrapped_tool = TelegramToolWrapper(
                        wrapped_tool=tool_item,
                        telegram_api_id=telegram_api_id_int,
                        telegram_api_hash=telegram_api_hash,
                        telegram_bot_token=telegram_token
                    )
                    agent_tools_final.append(wrapped_tool)
                    logger.debug(f"Wrapped Telegram tool '{tool_name}' for agent '{agent_name}'.")

                elif is_discord_tool and discord_bot_id:
                    wrapped_tool = DiscordToolWrapper(
                        wrapped_tool=tool_item,
                        bot_id=discord_bot_id
                    )
                    agent_tools_final.append(wrapped_tool)
                    logger.debug(f"Wrapped Discord tool '{tool_name}' for agent '{agent_name}'.")

                else:
                    # Append all other tools directly
                    agent_tools_final.append(tool_item)
                    logger.debug(f"Added non-wrapped tool '{tool_name}' for agent '{agent_name}'.")
        else:
            logger.warning(f"No 'allowed_tool_names' specified for agent '{agent_name}'. Agent will be created with no tools.")

        # Assign the final list of tools to the mcp_client for later use
        mcp_client.tools = {tool.name: tool for tool in agent_tools_final}

        logger.info(f"🔧 Loaded {len(agent_tools_final)} tools for agent '{agent_name}'. Tools found: {[t.name for t in agent_tools_final]}.")
        
        system_prompt = AGENT_SYSTEM_PROMPT
        if agent_persona:
            system_prompt = f"{system_prompt}\n\nYour persona: {agent_persona}"
        if agent_bio:
            system_prompt = f"{system_prompt}\n\nYour bio: {'\n'.join(agent_bio)}"
        if agent_knowledge:
            system_prompt = f"{system_prompt}\n\nKnowledge: {'\n'.join(agent_knowledge)}"
        if agent_lore:
            system_prompt = f"{system_prompt}\n\nLore: {'\n'.join(agent_lore)}"
        
        logger.info(f"Using AGENT_SYSTEM_PROMPT for agent '{agent_name}'.")
        
        agent_executor = await create_custom_tool_agent(llm, agent_tools_final, system_prompt, agent_name)

        logger.info(f"🧠 Agent: {agent_name} (ID: {agent_id}) initialized as a custom LangGraph agent with {len(agent_tools_final)} tools.")

        return agent_executor, mcp_client, discord_bot_id, telegram_bot_id, agent_tools_final