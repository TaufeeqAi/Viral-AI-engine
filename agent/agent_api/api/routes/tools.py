import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from ...models.agent_config import Tool, AgentTool
from ..dependencies import get_current_user, get_db_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])

# --------- TOOL CRUD ---------

@router.post("/", response_model=Tool, status_code=status.HTTP_201_CREATED)
async def create_or_update_tool(
    tool: Tool,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        tool_id = await db_manager.upsert_tool(tool)
        tool.id = tool_id
        return tool
    except Exception as e:
        logger.error(f"Failed to create/update tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not save tool.")


@router.get("/", response_model=List[Tool])
async def list_all_tools(
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        return await db_manager.get_all_tool_metadata()
    except Exception as e:
        logger.error("Error fetching tools", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch tools.")


@router.get("/{tool_id}", response_model=Tool)
async def get_tool_by_id(
    tool_id: str,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        tool = await db_manager.get_tool_by_id(tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        return tool
    except Exception as e:
        logger.error("Error fetching tool by ID", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch tool.")


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        await db_manager.delete_tool(tool_id)
    except Exception as e:
        logger.error("Error deleting tool", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete tool.")


# --------- AGENT-TOOL ASSOCIATION ---------

@router.post("/{agent_id}/add/{tool_id}", status_code=status.HTTP_200_OK)
async def add_tool_to_agent(
    agent_id: str,
    tool_id: str,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        await db_manager.add_tool_to_agent(agent_id, tool_id)
        return {"message": f"Tool {tool_id} added to agent {agent_id}."}
    except Exception as e:
        logger.error("Error adding tool to agent", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add tool to agent.")


@router.delete("/{agent_id}/remove/{tool_id}", status_code=status.HTTP_200_OK)
async def remove_tool_from_agent(
    agent_id: str,
    tool_id: str,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        await db_manager.remove_tool_from_agent(agent_id, tool_id)
        return {"message": f"Tool {tool_id} removed from agent {agent_id}."}
    except Exception as e:
        logger.error("Error removing tool from agent", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove tool from agent.")


@router.get("/{agent_id}/agent-tools", response_model=List[AgentTool])
async def get_agent_tools(
    agent_id: str,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        return await db_manager.get_tools_for_agent(agent_id)
    except Exception as e:
        logger.error("Error getting tools for agent", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch agent's tools.")


@router.patch("/{agent_id}/toggle/{tool_id}", status_code=status.HTTP_200_OK)
async def toggle_tool_status(
    agent_id: str,
    tool_id: str,
    is_enabled: bool,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    try:
        await db_manager.update_tool_enabled_status(agent_id, tool_id, is_enabled)
        return {"message": f"Tool {tool_id} {'enabled' if is_enabled else 'disabled'} for agent {agent_id}."}
    except Exception as e:
        logger.error("Error toggling tool status", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update tool status.")
