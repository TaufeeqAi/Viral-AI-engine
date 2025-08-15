import logging
from typing import Dict, List, Tuple
from fastapi import WebSocket, WebSocketDisconnect

# Configure logging for this module
logger = logging.getLogger(__name__)
# Ensure the logger level is set appropriately in your main application (e.g., main.py)
# For debugging, you might set it to logging.DEBUG:
# logging.basicConfig(level=logging.DEBUG)

class ConnectionManager:
    def __init__(self):
        # Stores active connections: {channel_name: [(websocket, user_id, session_id), ...]}
        # The `message` in broadcast is expected to be a JSON string.
        self.active_connections: Dict[str, List[Tuple[WebSocket, str, str]]] = {}
        logger.info("ConnectionManager initialized.")

    async def connect(self, websocket: WebSocket, user_id: str, session_id: str, channel: str):
        """
        Establishes a new WebSocket connection and adds it to the manager.
        """
        logger.debug(f"Attempting to connect WebSocket for user '{user_id}' to session '{session_id}' on channel '{channel}'.")
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
            logger.debug(f"Created new channel list for '{channel}'.")
        
        self.active_connections[channel].append((websocket, user_id, session_id))
        logger.info(f"Connection added to channel '{channel}' for user '{user_id}', session '{session_id}'. Total connections for channel: {len(self.active_connections[channel])}")
        logger.debug(f"Current active connections state: {self._get_connection_summary()}")


    def disconnect(self, websocket: WebSocket):
        """
        Removes a disconnected WebSocket connection from the manager.
        It iterates through all channels to find and remove the specific websocket.
        """
        logger.debug(f"Attempting to disconnect WebSocket: {websocket}")
        found_and_removed = False
        for channel, connections in list(self.active_connections.items()): # Iterate over a copy
            for conn_tuple in list(connections): # Iterate over a copy for safe removal
                if conn_tuple[0] == websocket:
                    user_id = conn_tuple[1]
                    session_id = conn_tuple[2]
                    connections.remove(conn_tuple)
                    found_and_removed = True
                    logger.info(f"Connection removed from channel '{channel}' for user '{user_id}', session '{session_id}'. Remaining in channel: {len(connections)}")
                    
                    if not connections: # If no more connections in channel, remove channel entry
                        del self.active_connections[channel]
                        logger.debug(f"Channel '{channel}' is now empty and removed.")
                    break # Break from inner loop once found
            if found_and_removed:
                break # Break from outer loop once found
        
        if not found_and_removed:
            logger.warning("Attempted to disconnect a WebSocket not found in active connections.")
        logger.debug(f"Current active connections state after disconnect: {self._get_connection_summary()}")


    async def broadcast(self, channel: str, message: str):
        """
        Broadcasts a message (expected to be a JSON string) to all connected clients in a specific channel.
        """
        logger.debug(f"Broadcast initiated for channel '{channel}'. Message content (first 100 chars): {message[:100]}...")
        
        if channel not in self.active_connections:
            logger.warning(f"Attempted to broadcast to non-existent channel: {channel}. No clients to send to.")
            return

        disconnected_websockets = []
        # Iterate over a copy of the list to safely remove elements during iteration
        for connection, user_id, session_id in list(self.active_connections[channel]):
            try:
                logger.debug(f"Sending message to user '{user_id}' on session '{session_id}' (channel '{channel}').")
                await connection.send_text(message) 
                logger.debug(f"Successfully sent message to user '{user_id}' on session '{session_id}' in channel '{channel}'.")
            except WebSocketDisconnect:
                logger.warning(f"Client disconnected during broadcast to channel {channel} (user: {user_id}, session: {session_id}). Marking for removal.")
                disconnected_websockets.append(connection)
            except RuntimeError as e:
                # This typically happens if the WebSocket is already closed by the client unexpectedly
                logger.warning(f"Failed to send message to client on channel {channel} (user: {user_id}, session: {session_id}): {e}. Marking for disconnection.")
                disconnected_websockets.append(connection)
            except Exception as e:
                logger.error(f"Unexpected error sending message to client on channel {channel} (user: {user_id}, session: {session_id}): {e}", exc_info=True)
                disconnected_websockets.append(connection)

        # Clean up disconnected websockets after iterating
        if disconnected_websockets:
            logger.info(f"Initiating cleanup for {len(disconnected_websockets)} disconnected websockets from channel '{channel}'.")
            for ws in disconnected_websockets:
                self.disconnect(ws) # Call the disconnect method to properly remove
            logger.info(f"Finished cleanup for channel '{channel}'. Remaining connections: {len(self.active_connections.get(channel, []))}")
        else:
            logger.debug(f"No websockets to clean up for channel '{channel}'.")

    def _get_connection_summary(self) -> Dict[str, int]:
        """Helper to get a summary of active connections per channel for logging."""
        return {channel: len(conns) for channel, conns in self.active_connections.items()}

