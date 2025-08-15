import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import List, Optional, Any, Dict, Union # Added Dict, Union
import asyncio
from uuid import UUID
from datetime import datetime

from ...core.chat_manager import ChatManager
from ...core.agent_manager import AgentManager # Import AgentManager
from ..dependencies import get_current_user, get_db_manager, get_agent_manager
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from ...models.chat_models import (
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionUpdate,
    ChatMessageCreate,
    ChatMessageRead,
    MessageContent # Keep MessageContent for internal conversion in ChatManager
)
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatResponse(BaseModel):
    message: str
    session_id: str

@router.get("/sessions", response_model=List[ChatSessionRead])
async def get_all_chat_sessions_endpoint(
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager),
    agent_id: Optional[str] = None,
    active_only: bool = True,
    limit: int = 100
):
    """
    Retrieve all chat sessions for the current user.
    """
    logger.info(f"API: GET /sessions - User '{current_user}' requesting all chat sessions.")
    logger.debug(f"API: GET /sessions - Filters: agent_id={agent_id}, active_only={active_only}, limit={limit}")

    chat_manager = ChatManager(db_manager)
    
    try:
        logger.info(f"API: GET /sessions - Calling chat_manager.get_all_sessions_for_user for user '{current_user}'.")
        sessions = await chat_manager.get_all_sessions_for_user(
            user_id=current_user,
            agent_id=agent_id,
            active_only=active_only,
            limit=limit
        )
        logger.info(f"API: GET /sessions - Successfully retrieved {len(sessions)} chat sessions for user '{current_user}'.")
        return sessions
    except Exception as e:
        logger.error(f"API: GET /sessions - Error fetching chat sessions for user '{current_user}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat sessions: {e}"
        )


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message_and_get_response(
    session_id: UUID, # Changed to UUID for path parameter
    message_data: ChatMessageCreate, # Accepts 'role' and 'content' (Union[str, Dict])
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager),
    agent_manager: AgentManager = Depends(get_agent_manager) # Type hint AgentManager
):
    """
    Handles sending a user message and triggers an agent response,
    streaming the LLM output via WebSockets.
    """
    logger.info(f"API: POST /sessions/{session_id}/messages - User '{current_user}' sending message.")
    logger.debug(f"API: POST /sessions/{session_id}/messages - Message data: {message_data.model_dump()}")

    chat_manager = ChatManager(db_manager)
    # Set the broadcast callbacks for the chat_manager (CRITICAL for streaming and sidebar updates)
    chat_manager.set_broadcast_callbacks(
        session_broadcast_cb=agent_manager.broadcast_message_to_session,
        user_broadcast_cb=agent_manager.broadcast_user_event
    )

    # 1. Validate session and user access
    logger.info(f"API: POST /sessions/{session_id}/messages - Validating session {session_id}.")
    session = await chat_manager.get_session(str(session_id)) # Convert UUID to str for manager
    if not session:
        logger.warning(f"API: POST /sessions/{session_id}/messages - Chat session {session_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    
    if str(session.user_id) != current_user:
        logger.warning(f"API: POST /sessions/{session_id}/messages - User '{current_user}' unauthorized for session {session_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this session.")
    logger.info(f"API: POST /sessions/{session_id}/messages - Session {session_id} found and authorized.")

    # 2. Add user message to DB (and it will be broadcast by chat_manager)
    logger.info(f"API: POST /sessions/{session_id}/messages - Adding user message to DB.")
    # message_data already contains 'role' and 'content' (Union[str, Dict])
    await chat_manager.add_message(
        session_id=str(session_id), # Convert UUID to str for manager
        data=message_data,
        is_partial=False # User messages are never partial
    )
    logger.info(f"API: POST /sessions/{session_id}/messages - User message added to session {session_id}.")

    # 3. Retrieve the agent and stream response
    agent_id = str(session.agent_id)
    logger.info(f"API: POST /sessions/{session_id}/messages - Retrieving agent {agent_id}.")
    initialized_agent_info = agent_manager.get_initialized_agent(agent_id)

    if not initialized_agent_info:
        logger.error(f"API: POST /sessions/{session_id}/messages - Agent with ID {agent_id} not initialized or found.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent with ID {agent_id} is not available. Please ensure it is configured and initialized."
        )

    agent_executor = initialized_agent_info["executor"]
    full_agent_response_content = ""

    # Helper to extract text content from LangChain message or dict
    def extract_ai_content(item: Any) -> Optional[str]:
        if isinstance(item, AIMessage) and item.content:
            return item.content
        if isinstance(item, dict):
            # Check for 'content' key in dict, which might be a string or another dict
            if 'content' in item:
                if isinstance(item['content'], str):
                    return item['content']
                elif isinstance(item['content'], dict) and 'text' in item['content']:
                    return item['content']['text']
            # Check for 'messages' list in dict (e.g., from LangGraph state)
            if 'messages' in item and isinstance(item['messages'], list):
                for msg in item['messages']:
                    if isinstance(msg, AIMessage) and msg.content:
                        return msg.content
        return None

    try:
        # Prepare initial state for agent_executor.astream
        # message_data.content is Union[str, Dict]. Convert to HumanMessage content.
        initial_message_content_text: str
        if isinstance(message_data.content, str):
            initial_message_content_text = message_data.content
        elif isinstance(message_data.content, dict) and 'text' in message_data.content:
            initial_message_content_text = message_data.content['text']
        else:
            initial_message_content_text = str(message_data.content) # Fallback for other dict types

        initial_agent_state = {"messages": [HumanMessage(content=initial_message_content_text)]}
        logger.info(f"API: POST /sessions/{session_id}/messages - Starting streaming response from agent {agent_id}.")
        
        # This ID will be used for all llm_stream_chunk events for this response.
        ai_message_id = UUID(int=datetime.now().timestamp() * 1000000)

        async for chunk in agent_executor.astream(initial_agent_state):
            logger.debug(f"API: POST /sessions/{session_id}/messages - Received raw agent chunk: {chunk}")
            
            current_chunk_content = extract_ai_content(chunk)

            if current_chunk_content:
                full_agent_response_content += current_chunk_content
                
                # Create ChatMessageRead for partial message (for broadcasting)
                # Content is the accumulated string
                partial_message_read = ChatMessageRead(
                    id=ai_message_id, # Consistent ID for streaming message
                    session_id=session_id,
                    role="agent",
                    content=full_agent_response_content, # Send accumulated string content
                    timestamp=datetime.now(),
                    is_partial=True
                )
                logger.debug(f"API: POST /sessions/{session_id}/messages - Broadcasting partial AIMessage: '{current_chunk_content[:50]}...'")
                
                # Broadcast the partial message directly via agent_manager (not saving to DB yet)
                await agent_manager.broadcast_message_to_session(
                    session_id=str(session_id), # Convert UUID to str for manager
                    message=partial_message_read,
                    event_type="llm_stream_chunk"
                )
            
            # Handle other types of chunks (e.g., tool calls) if your agent streams them
            if "messages" in chunk and chunk["messages"]:
                for message_in_chunk in chunk["messages"]:
                    if isinstance(message_in_chunk, ToolMessage):
                        logger.info(f"API: POST /sessions/{session_id}/messages - Tool used: {message_in_chunk.tool_call_id} -> {message_in_chunk.content[:100]}...")
            
            elif "output" in chunk:
                # This might be the final output from a graph, ensure it's captured
                output_content = extract_ai_content(chunk["output"])
                if output_content and not full_agent_response_content: # Only if no content was streamed yet
                    full_agent_response_content = output_content
                    logger.debug(f"API: POST /sessions/{session_id}/messages - Captured final output AIMessage content from 'output' key: '{output_content[:50]}...'")


        logger.info(f"API: POST /sessions/{session_id}/messages - LLM streaming complete for session {session_id}.")
        logger.debug(f"API: POST /sessions/{session_id}/messages - Full accumulated agent response content: '{full_agent_response_content}'")

        if not full_agent_response_content:
            logger.warning(f"API: POST /sessions/{session_id}/messages - Agent returned no content during streaming.")
            full_agent_response_content = "No response generated by the agent." # Default if empty

    except Exception as e:
        logger.error(f"API: POST /sessions/{session_id}/messages - Error during agent streaming: {e}", exc_info=True)
        error_message_content = f"An error occurred while generating the response: {e}"
        # Create ChatMessageCreate for error message (content is string)
        error_message_data = ChatMessageCreate(
            role="agent",
            content=error_message_content, # Send string content
            is_partial=False
        )
        # Add error message to DB and broadcast as a final message
        await chat_manager.add_message(
            session_id=str(session_id), # Convert UUID to str
            data=error_message_data,
            is_partial=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent response: {e}"
        )

    # 4. After streaming is complete, add the final full response to DB
    # This will also trigger the final message_created event broadcast by chat_manager.add_message
    final_message_data = ChatMessageCreate(
        role="agent",
        content=full_agent_response_content, # Send string content
        is_partial=False
    )
    logger.info(f"API: POST /sessions/{session_id}/messages - Saving final agent response to DB.")
    await chat_manager.add_message(
        session_id=str(session_id), # Convert UUID to str
        data=final_message_data,
        is_partial=False
    )
    logger.info(f"API: POST /sessions/{session_id}/messages - Final agent response saved for session {session_id}.")

    return ChatResponse(session_id=str(session_id), message="Message processed and response streamed.")

@router.post("/sessions", response_model=ChatSessionRead)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager),
    agent_manager: AgentManager = Depends(get_agent_manager) # Inject agent_manager
):
    logger.info(f"API: POST /sessions - User '{current_user}' creating new session.")
    logger.debug(f"API: POST /sessions - Session data: {session_data.model_dump()}")

    chat_manager = ChatManager(db_manager)
    # Set the broadcast callbacks for the chat_manager
    chat_manager.set_broadcast_callbacks(
        session_broadcast_cb=agent_manager.broadcast_message_to_session,
        user_broadcast_cb=agent_manager.broadcast_user_event
    )
    
    if str(session_data.user_id) != current_user:
        logger.warning(f"API: POST /sessions - User '{current_user}' attempted to create session for different user '{session_data.user_id}'.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create sessions for another user."
        )
    try:
        logger.info(f"API: POST /sessions - Calling chat_manager.create_session.")
        session = await chat_manager.create_session(session_data) # chat_manager.create_session will broadcast
        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat session: No session object returned."
            )
        logger.info(f"API: POST /sessions - Session created with ID: {session.id}. Returning session details.")
        return ChatSessionRead.model_validate(session)
    except Exception as e:
        logger.error(f"API: POST /sessions - Error creating session for user '{current_user}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat session: {e}"
        )

@router.get("/sessions/{id}", response_model=ChatSessionRead)
async def get_session(
    id: UUID,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    logger.info(f"API: GET /sessions/{id} - User '{current_user}' requesting session.")
    chat_manager = ChatManager(db_manager)
    try:
        logger.info(f"API: GET /sessions/{id} - Calling chat_manager.get_session.")
        session = await chat_manager.get_session(str(id))
        if not session:
            logger.warning(f"API: GET /sessions/{id} - Session {id} not found.")
            raise HTTPException(status_code=404, detail="Session not found")
        if str(session.user_id) != current_user:
            logger.warning(f"API: GET /sessions/{id} - User '{current_user}' unauthorized for session {id}.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this session.")
        logger.info(f"API: GET /sessions/{id} - Session {id} fetched successfully.")
        return ChatSessionRead.model_validate(session)
    except Exception as e:
        logger.error(f"API: GET /sessions/{id} - Error fetching session {id} for user '{current_user}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat session: {e}"
        )

@router.put("/sessions/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_session(
    id: UUID,
    update_data: ChatSessionUpdate,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager),
    agent_manager: AgentManager = Depends(get_agent_manager) # Inject agent_manager
):
    logger.info(f"API: PUT /sessions/{id} - User '{current_user}' updating session.")
    logger.debug(f"API: PUT /sessions/{id} - Update data: {update_data.model_dump()}")
    chat_manager = ChatManager(db_manager)
    chat_manager.set_broadcast_callbacks(
        session_broadcast_cb=agent_manager.broadcast_message_to_session,
        user_broadcast_cb=agent_manager.broadcast_user_event
    )
    try:
        logger.info(f"API: PUT /sessions/{id} - Checking authorization for session {id}.")
        session = await chat_manager.get_session(str(id))
        if not session or str(session.user_id) != current_user:
            logger.warning(f"API: PUT /sessions/{id} - User '{current_user}' unauthorized or session {id} not found.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied or session not found.")
        
        logger.info(f"API: PUT /sessions/{id} - Calling chat_manager.update_session.")
        # Assume update_session in ChatManager returns the updated session object
        updated_session_obj = await chat_manager.update_session(str(id), update_data) # chat_manager.update_session will broadcast
        logger.info(f"API: PUT /sessions/{id} - Session {id} updated successfully.")

    except Exception as e:
        logger.error(f"API: PUT /sessions/{id} - Error updating session {id} for user '{current_user}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat session: {e}"
        )


@router.get("/sessions/{id}/messages", response_model=List[ChatMessageRead])
async def get_messages(
    id: UUID,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    """
    Retrieves all messages for a specific chat session.
    """
    logger.info(f"API: GET /sessions/{id}/messages - User '{current_user}' requesting messages for session {id}.")
    chat_manager = ChatManager(db_manager)
    try:
        logger.info(f"API: GET /sessions/{id}/messages - Checking authorization for session {id}.")
        session = await chat_manager.get_session(str(id))
        if not session or str(session.user_id) != current_user:
            logger.warning(f"API: GET /sessions/{id}/messages - User '{current_user}' unauthorized or session {id} not found.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied or session not found.")

        logger.info(f"API: GET /sessions/{id}/messages - Calling chat_manager.get_messages.")
        messages = await chat_manager.get_messages(str(id)) # chat_manager.get_messages will return ChatMessageRead
        logger.info(f"API: GET /sessions/{id}/messages - Retrieved {len(messages)} messages for session {id}.")
        return messages
    except Exception as e:
        logger.error(f"API: GET /sessions/{id}/messages - Error fetching messages for session {id} for user '{current_user}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat messages: {e}"
        )
