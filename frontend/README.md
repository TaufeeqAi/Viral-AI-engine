## 🤖 Agent UI (Frontend)

This repository houses the Streamlit-based user interface for the Multi-Agent Bot system. It provides a user-friendly way to interact with the agent-api, allowing you to create, manage, and chat with your dynamically configured AI agents.

## ✨ Features

- **Agent Creation**: Intuitive forms to define new AI agents, including their name, bio, persona, and API secrets (Groq, Discord, Telegram).
- **Agent Listing**: View all currently registered agents with their essential details.
- **Interactive Chat**: Engage in real-time conversations with selected agents, supporting both general queries and platform-specific interactions (if the agent is configured for Discord/Telegram).
- **Dynamic Configuration**: Easily update agent details and secrets through the UI.
- **Responsive Design**: A simple, clean interface built with Streamlit.

## 🏛️ Architecture Context

The agent-UI serves as the primary interaction point for users with the backend agent-api. It sends requests to the agent-api for agent management (create, list) and chat interactions. It does not directly interact with the MCP servers or external platforms; all communication is proxied through the agent-api.

```

User <--> Agent UI <--> agent-api <--> Specialized MCPs <--> External Services

````

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Access to the running agent-api server.

### Installation

Clone this repository:

```bash
git clone https://github.com/CyreneAI/agent-UI.git
cd agent-UI
````

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Environment Variables

Before running the application, ensure you have a `.env` file in the root of this `agent-UI` directory with the following variable:

**Example for local development:**

```
BOT_API_BASE_URL=http://localhost:8000
```

```env
# .env in agent-UI directory
BOT_API_BASE_URL=http://localhost:8000
```

### Running the Application

Once dependencies are installed and the `.env` is configured, run the Streamlit app:

```bash
streamlit run app.py
```

The application will open in your default web browser.

## 🧪 Usage

* **Navigate** to the app in your browser (usually [http://localhost:8501](http://localhost:8501)).
* **Create Agents**: Use the provided forms to create new agents.

  * For agents that should interact with Discord, include `discord_bot_token` in the secrets JSON field.
  * For agents that should interact with Telegram, include `telegram_bot_token`, `telegram_api_id`, and `telegram_api_hash` in the secrets JSON field.
* **Select an Agent**: Choose an agent from the dropdown to start chatting.
* **Send Messages**: Type your message in the input box and press Enter. The agent's response will appear in the chat history.

## 📁 Project Structure

```
agent-UI/
├── .env.example
├── .gitignore
├── README.md           # <- This file
├── app.py              # Main Streamlit application file
├── requirements.txt    # Python dependencies for the UI
```

```


