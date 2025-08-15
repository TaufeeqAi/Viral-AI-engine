# mcp-servers/rag-mcp/Dockerfile
FROM base-mcp:latest 
WORKDIR /app

# Copy the MCP server file and any RAG-specific data/directories
COPY mcp-servers/rag-mcp/server.py /app/mcp-servers/rag-mcp/server.py

# Copy MCP-specific requirements.txt and install them
COPY mcp-servers/rag-mcp/requirements.txt /app/mcp-servers/rag-mcp/requirements.txt
RUN pip install --no-cache-dir -r mcp-servers/rag-mcp/requirements.txt


# Set environment variables for Kubernetes deployment
ENV LOCAL_MODE="false"
ENV FASTMCP_BASE_URL="http://fastmcp-core-svc:9000"

# Standard MCP port in Kubernetes
EXPOSE 9000

CMD ["uvicorn", "mcp-servers.rag-mcp.server:app", "--host", "0.0.0.0", "--port", "9000"]
