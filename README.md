## Viral AI Engine

An extensible and scalable multi-agent AI bot system leveraging LangChain, FastMCP, and deployed on a local Kubernetes cluster using KinD. This system now supports dynamic registration of Discord and Telegram bots based on API keys provided at agent creation.

## Table of Contents

- [Features](#features)  
- [Architecture Overview](#architecture-overview)  
- [Getting Started](#getting-started)  
  - [Prerequisites](#prerequisites)  
  - [Setup & Deployment](#setup--deployment)  
- [Usage & Testing](#usage--testing)  
- [Project Structure](#project-structure)  
- [Contributing](#contributing)  
- [License](#license)  

---

✨ ## Features

- **Modular Architecture**  
  Separate core logic, tool definitions (MCPs), and platform integrations.  

- **Multi-Agent Reasoning**  
  Powered by LangChain and Groq LLMs for intelligent tool selection and interaction.  

- **FastMCP Integration**  
  Dynamic discovery of specialized MCP servers for web search, finance, RAG, and platform communication.  

- **Dynamic Platform Integrations**  
  - **Discord**: Multiple Discord bots can be dynamically registered and managed via their tokens. Each agent can interact through its dedicated Discord bot.  
  - **Telegram**: Multiple Telegram bots can be dynamically registered and managed via their tokens and API credentials. Each agent can interact through its dedicated Telegram bot.  

- **Containerized Deployment**  
  Dockerized services for portability.  

- **Persistent Storage**  
  RAG data stored in ChromaDB on Persistent Volume Claims (PVC).  

- **Automated Scripts**  
  Bash scripts to build images and deploy to KinD, and to set up Telegram webhooks.  

* **bot-api**: Core agent application using Langgraph, responsible for agent creation, management, and orchestrating interactions.
* **fastmcp-core-server**: Central registry for all available MCP tools.

**Specialized MCPs:**

* **web-mcp**, **finance-mcp**, **rag-mcp**: Provide general-purpose tools.
* **telegram-mcp**, **discord-mcp**: Manage individual bot clients for their respective platforms, dynamically starting and stopping them based on agent requirements. They also handle forwarding messages to bot-api with the correct bot context.

**ChromaDB**: Vector store for RAG, ensuring knowledge persistence across restarts.

---

🚀 ## Getting Started

### Prerequisites

* Git
* Python 3.12+
* Docker Desktop (ensure sufficient resources: 4–8 GB RAM, 2–4 CPUs recommended)
* KinD (Kubernetes in Docker)
* kubectl (Kubernetes CLI)
* ngrok (optional, but highly recommended for exposing your telegram-mcp server to Telegram's webhook API)

### Setup & Deployment

1. **Clone Repository**

   ```bash
   git clone https://github.com/your-username/multi-agent-bot.git
   cd multi-agent-bot
   ```

2. **Environment Variables**
   Create a `.env` file by copying `.env.example`.

   ```bash
   cp .env.example .env
   ```

   Fill in your API keys and tokens. At a minimum, you'll need:

   * `GROQ_API_KEY`: For the LLM used by agents.

   > **Note:** Discord and Telegram bot tokens/API keys are provided when you create/update an agent via the bot-api's `/agents/create` or `/agents/update` endpoints, not directly in the `.env` for the bot-api itself. However, if you are running MCPs locally, they might still need some of these in their own `.env` files or passed via environment variables. For Kubernetes, these will be managed via `k8s/secrets.yaml`.

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Build Docker Images**

   ```bash
   chmod +x scripts/build_images.sh
   ./scripts/build_images.sh
   ```

5. **Load RAG Data (if applicable)**

   ```bash
   kubectl apply -f k8s/jobs/rag-data-loader-job.yaml
   # Monitor job status:
   kubectl get job rag-data-loader -n multi-agent-bot
   # Check logs:
   kubectl logs job/rag-data-loader -n multi-agent-bot
   ```

---

🧪 ## Usage & Testing

Once all services are deployed and running:

1. **Access Bot API**
   The `bot-api` service will typically be exposed via a Kubernetes Ingress or a NodePort/LoadBalancer. For local KinD, you might port‑forward it:

   ```bash
   kubectl port-forward service/bot-api-svc 8000:8000 -n multi-agent-bot
   ```

   You can then interact with the API at `http://localhost:8000`.

2. **Create Agents (via API or Frontend)**
   Use your frontend (if available) or `curl` to create agents, providing their `groq_api_key` and any `discord_bot_token` or `telegram_bot_token`/`api_id`/`api_hash` in the `secrets` field of the `AgentConfig` payload. This will dynamically start the corresponding bot clients on the `discord-mcp` or `telegram-mcp` servers.

   **Example curl for creating a Discord-enabled agent:**

   ```bash
   curl -X POST "http://localhost:8000/agents/create" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "MyDiscordAgent",
          "bio": "A helpful Discord bot.",
          "persona": "friendly and concise",
          "secrets": {
            "groq_api_key": "sk-...",
            "discord_bot_token": "YOUR_DISCORD_BOT_TOKEN"
          }
        }'
   ```

3. **Discord Integration**

   * Ensure your Discord bot has the necessary intents enabled in the Discord Developer Portal (Message Content, Members).
   * Invite your Discord bot to a server.
   * Send messages to the bot in Discord. The `discord-mcp` will receive them via WebSocket, forward them to `bot-api`, and the agent will process and reply.

4. **Telegram Integration**

   * Port‑forward `telegram-mcp`:

     ```bash
     kubectl port-forward service/telegram-mcp-svc 9003:9003 -n multi-agent-bot
     ```
   * Expose `telegram-mcp` via ngrok:

     ```bash
     ngrok http 9003
     ```
   * Copy the HTTPS URL provided by ngrok (e.g., `https://xxxxxx.ngrok-free.app`).
   * Set Telegram Webhook using `scripts/setup_webhooks.sh` (update `NGROK_URL` in the script):

     ```bash
     chmod +x scripts/setup_webhooks.sh
     ./scripts/setup_webhooks.sh
     ```
   * Send messages via your Telegram bot.

5. **Tool Queries**
   Test your agents with various queries to ensure tools are functioning:

   * **Web**: “What is the capital of France?”
   * **Finance**: “AAPL current stock price?”
   * **RAG**: “Performance of Alita on GAIA benchmark?” (Requires RAG data to be loaded)

6. **Monitoring Logs**
   To view logs for any component:

   ```bash
   kubectl logs deployment/<deployment-name> -n multi-agent-bot --tail 50 -f
   # Example:
   kubectl logs deployment/bot-api-deployment -n multi-agent-bot --tail 50 -f
   kubectl logs deployment/discord-mcp-deployment -n multi-agent-bot --tail 50 -f
   ```

---

📁 ## Project Structure

```
multi-agent-bot/
├── .env.example
├── .gitignore
├── Dockerfile.fastmcp_core
├── Dockerfile.rag_data_loader
├── README.md
├── api-auth/
│       ├── Dockerfile 
│       ├── README.md 
│       ├── __init__.py
│       ├── main.py 
│       └── requirements.txt
├── agent-api/
│   ├── Dockerfile
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   └── main.py
│   ├── core
│   │   ├── __init__.py
│   │   └── agent_manager.py
│   ├── db
│   │   ├── __init__.py
│   │   └── sqlite_manager.py
│   ├── langgraph_agents
│   │   └── custom_tool_agent.py
│   ├── models
│   │   ├── __init__.py
│   │   └── agent_config.py
│   ├── prompts.py
│   └── requirements.txt
├── common
│   └── utils.py
├── frontend
│   └── flutter-app/
│       ├── android/
│       ├── ios/
│       ├── lib/
│       │   ├── main.dart (new)
│       │   ├── models/
│       │   │   └── agent.dart (new)
│       │   ├── pages/
│       │   │   ├── agent_list_page.dart (new)
│       │   │   ├── chat_page.dart (new)
│       │   │   └── create_agent_page.dart (new)
│       │   └── services/
│       │       ├── api_client.dart (new)
│       │       └── auth_service.dart (new)
│       ├── pubspec.yaml (new)
│       ├── ... (other Flutter files)
│ 
├── mcp-servers
│   ├── base-mcp
│   │   ├── Dockerfile.base
│   │   └── requirements.txt
│   ├── discord-mcp
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py
│   ├── finance-mcp
│   │   ├── Dockerfile
│   │   └── server.py
│   ├── rag-mcp
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py
│   ├── telegram-mcp
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py
│   └── web-mcp
│       ├── Dockerfile
│       └── server.py
├── requirements.txt
├── scripts
│     └── setup_webhooks.sh

```

---

🤝 ## Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request.

```
