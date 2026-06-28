# x-langgraph

## Project Introduction

**x-langgraph** is an enterprise-grade LangGraph workflow orchestration framework designed to help developers quickly build complex multi-step workflow applications based on large language models. This project adopts engineering and modular design, providing complete workflow examples and production-grade deployment solutions, suitable as a reference template for enterprise applications.

**Use Cases**:
- Intelligent customer service systems (multi-turn dialogue, intent recognition, ticket routing)
- RAG document Q&A (knowledge base retrieval, context building)
- Multi-agent collaboration (task decomposition, parallel execution, result aggregation)
- Automated approval workflows (risk assessment, human-machine interaction)
- Complex business process orchestration (conditional routing, state management)

## What is LangGraph

`LangGraph` is a framework in the LangChain ecosystem specifically designed for workflow orchestration. It provides a declarative way to define and execute complex workflows based on language models.

### LangGraph vs LangChain

| Feature | LangChain | LangGraph |
|---------|-----------|-----------|
| Positioning | General LLM application framework | Focused on workflow orchestration and state management |
| Core Capabilities | Model invocation, prompt management, tool integration | State graph, conditional routing, persistence |
| Use Cases | Simple chain calls | Complex multi-step workflows |
| State Management | Stateless | Stateful (supports Checkpointer) |
| Human-in-the-Loop | Not supported | Supported (interrupt/resume) |

### LangGraph Core Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| **StateGraph** | State graph, core container of workflow | `StateGraph(MyState)` |
| **State** | Workflow state, defined using TypedDict | `class MyState(TypedDict): ...` |
| **Node** | Node, function executing specific tasks | `def my_node(state): return {...}` |
| **Edge** | Edge, defines flow between nodes | `graph.add_edge("a", "b")` |
| **Conditional Edge** | Conditional edge, dynamic routing based on state | `graph.add_conditional_edges(...)` |
| **Checkpointer** | State persister | `MemorySaver()` / `MySQLSaver` |
| **interrupt** | Interrupt execution, wait for external input | `interrupt({"type": "approval"})` |
| **Command** | Command to resume execution | `Command(resume={...})` |

### Workflow Base Class Design

All workflows inherit from `BaseWorkflow` with unified interface:

```python
class BaseWorkflow(ABC):
    @abstractmethod
    def build(self) -> CompiledGraph: ...

    # Synchronous methods
    def invoke(self, inputs, config): ...
    def stream(self, inputs, config): ...

    # Asynchronous methods (recommended)
    async def ainvoke(self, inputs, config): ...
    async def astream(self, inputs, config): ...
```

### Provider Pattern (Tool Decoupling)

Tools support multiple data sources, decoupled through Provider pattern:

```
tools/weather/
├── base.py           # WeatherProvider (ABC)
├── mock_provider.py  # Mock implementation (for testing)
├── amap_provider.py  # Amap API implementation
└── __init__.py       # Factory function get_weather_provider()
```

### Smart Routing (LLM + Fallback)

Simple Router supports LLM semantic understanding + rule fallback:

```python
def router_node(state):
    if settings.has_valid_api_key():
        try:
            return _llm_routing(state["input"])  # LLM understands semantics
        except Exception:
            pass
    return _fallback_routing(state["input"])     # Rule fallback
```

## Core Features

- **Multiple Workflow Support**: Built-in 5 typical workflows (Simple Router, Customer Service, RAG Q&A, Multi-Agent Collaboration, Automated Approval)
- **State Persistence**: MySQL-based Checkpointer implementation, supporting workflow interrupt and resume
- **Human-in-the-Loop**: Support for manual approval, interrupt/resume and other interactive scenarios
- **Multiple LLM Providers**: Support for DeepSeek, Doubao, Alibaba Cloud and other mainstream models
- **Provider Pattern**: Decoupled tools and data sources, supporting Mock testing and real API switching
- **Streaming Output**: SSE streaming response support for better user experience
- **Unified Base Class**: All workflows inherit from `BaseWorkflow` with consistent interface
- **Docker Deployment**: Complete containerized deployment solution

## Project Structure

```
x-langgraph/
├── src/                          # Business code (source directory)
│   ├── api/                      # API service layer
│   │   ├── main.py               # FastAPI application entry
│   │   ├── schemas.py            # Data model definitions
│   │   └── routes/               # Route modules
│   │       ├── chat.py           # Chat endpoint
│   │       └── approval.py       # Approval endpoint
│   │
│   ├── config/                   # Configuration management
│   │   └── settings.py           # Environment variable config
│   │
│   ├── constants/                # Constant definitions
│   │   ├── develop.py            # Development constants
│   │   └── streaming_modes.py    # Streaming mode constants
│   │
│   ├── core/                     # Core functionality
│   │   ├── logger.py             # Logging module (loguru)
│   │   └── checkpointer.py       # MySQL state persistence
│   │
│   ├── llm/                      # LLM provider module
│   │   ├── providers.py          # LLM providers (DeepSeek/Doubao/Aliyun)
│   │   └── prompts.py            # Prompt template management
│   │
│   ├── tools/                    # Tool module
│   │   ├── base.py               # Tool base class
│   │   ├── search_tools.py       # Search tools
│   │   ├── calculation_tools.py  # Calculation tools
│   │   ├── weather_tools.py      # Weather tools
│   │   ├── data_tools.py         # Data processing tools
│   │   └── database_tools.py     # Database tools (Text2SQL)
│   │
│   └── workflows/                # Workflow module
│       ├── base.py               # Workflow base class (BaseWorkflow)
│       ├── simple_router/        # Simple router workflow
│       ├── customer_service/     # Customer service workflow
│       ├── rag_qa/               # RAG document Q&A workflow
│       ├── multi_agent/          # Multi-agent collaboration workflow
│       └── approval/             # Automated approval workflow
│
├── docker/                       # Docker configuration
│   └── mysql/
│       └── init.sql              # MySQL initialization script
│
├── examples/                     # Example code
│   ├── hello_world.py            # Basic example
│   ├── agent_workflow.py         # Basic workflow example
│   ├── demo_workflows.py         # Advanced workflow examples
│   └── langgraph_platform.py     # LangGraph Platform deployment example
│
├── tests/                        # Test code
├── .env                          # Environment variable config
├── .env.example                  # Environment variable template
├── Dockerfile                    # Docker image config
├── docker-compose.yml            # Docker compose config
├── langgraph.json                # LangGraph Platform config
└── pyproject.toml                # Project config
```

## System Architecture

### System Layered Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                    │
│                      Web / Mobile / Desktop Apps                         │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP / SSE
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Layer                                      │
│                        FastAPI Application                               │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐    │
│    │  POST /chat  │  │ POST /chat/  │  │  approval/resume         │    │
│    │              │  │   stream     │  │  approval/status/:id     │    │
│    └──────────────┘  └──────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Workflow Layer                                    │
│                           src/workflows/                                 │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────┐ ┌───────┐ │
│  │Simple Router│ │Customer Svc  │ │  RAG QA   │ │MultiAgent│ │Approval│ │
│  └─────────────┘ └──────────────┘ └───────────┘ └──────────┘ └───────┘ │
│                         BaseWorkflow (abstract base)                    │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐ ┌───────────────────┐ ┌────────────────────────┐
│    Tools Layer        │ │   LLM Provider    │ │   Persistence Layer    │
│     src/tools/        │ │     src/llm/      │ │      src/core/         │
│ ┌───────────────────┐ │ │ ┌───────────────┐ │ │ ┌────────────────────┐ │
│ │ search_tools      │ │ │ │ DeepSeek      │ │ │ │ checkpointer       │ │
│ │ calculation_tools │ │ │ │ Doubao        │ │ │ │ (MySQL)            │ │
│ │ weather_tools     │ │ │ │ Aliyun Qwen   │ │ │ │ logger             │ │
│ │ data_tools        │ │ │ └───────────────┘ │ │ └────────────────────┘ │
│ │ database_tools    │ │ │                   │ │                        │
│ └───────────────────┘ │ │                   │ │                        │
└───────────────────────┘ └───────────────────┘ └────────────────────────┘
                    │                 │                 │
                    ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Infrastructure Layer                              │
│    ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐    │
│    │ External API │    │    MySQL     │    │    Config/Logger     │    │
│    │ (Amap/Search)│    │  (Checkpoint)│    │                      │    │
│    └──────────────┘    └──────────────┘    └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Business Workflow Diagrams

#### 1. Simple Router Workflow

```
┌─────────┐    ┌──────────┐    ┌─────────────────────────────────┐
│  START  │───▶│  router  │───▶│        Conditional Route        │
└─────────┘    └──────────┘    └─────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌──────────┐     ┌───────────┐     ┌──────────┐
              │  search  │     │ calculate │     │ weather  │
              └────┬─────┘     └─────┬─────┘     └────┬─────┘
                   │                 │                 │
                   └─────────────────┼─────────────────┘
                                     ▼
                              ┌──────────┐
                              │   END    │
                              └──────────┘
```

**Core Features**: Conditional edge routing, tool calling, LLM semantic understanding + rule fallback

#### 2. Customer Service Workflow

```
┌─────────┐    ┌─────────┐    ┌───────────┐    ┌────────────────────┐
│  START  │───▶│ intake  │───▶│ classify  │───▶│   Conditional      │
└─────────┘    └─────────┘    └───────────┘    │       Route        │
                                                    └────────────────────┘
                                                     │
                    ┌────────────────┬───────────────┼───────────────┐
                    ▼                ▼               ▼               ▼
              ┌──────────┐    ┌───────────┐   ┌──────────┐   ┌──────────┐
              │ inquiry  │    │ complaint │   │technical │   │ billing  │
              └────┬─────┘    └─────┬─────┘   └────┬─────┘   └────┬─────┘
                   │                │              │               │
                   │                │         [interrupt]          │
                   │                │              │               │
                   └────────────────┴──────────────┴───────────────┘
                                           ▼
                                    ┌──────────┐
                                    │  review  │
                                    └────┬─────┘
                                         ▼
                                    ┌──────────┐
                                    │   END    │
                                    └──────────┘
```

**Core Features**: Multi-level conditional routing, Human-in-the-Loop, Checkpointer state persistence

#### 3. RAG Document Q&A Workflow

```
┌─────────┐    ┌────────┐    ┌────────────┐    ┌─────────────────┐
│  START  │───▶│  init  │───▶│  retrieve  │───▶│ Conditional     │
└─────────┘    └────────┘    └────────────┘    │     Route       │
                                                   └─────────────────┘
                                                   │
                              ┌────────────────────┼────────────────┐
                              ▼                                     ▼
                       ┌──────────────┐                    ┌───────────┐
                       │ build_context│                    │ generate  │
                       └──────┬───────┘                    └─────┬─────┘
                              │                                  │
                              └──────────────────────────────────┘
                                               ▼
                                        ┌───────────┐
                                        │  END      │
                                        └───────────┘
```

**Core Features**: Vector retrieval, context building, LLM generation, fallback handling

#### 4. Multi-Agent Collaboration Workflow

```
┌─────────┐    ┌─────────────┐    ┌──────────────────────────────┐
│  START  │───▶│ coordinator │───▶│        Task Routing          │
└─────────┘    └─────────────┘    └──────────────────────────────┘
                                         │
                                         ▼
                                 ┌───────────────┐
                                 │  researcher   │  ← Researcher
                                 └───────┬───────┘
                                         │
                                         ▼
                                 ┌───────────────┐
                                 │    writer     │  ← Writer
                                 └───────┬───────┘
                                         │
                                         ▼
                                 ┌───────────────┐
                                 │    editor     │  ← Editor
                                 └───────┬───────┘
                                         │
                                         ▼
                                 ┌───────────────┐
              ┌──────────────────│   reviewer    │  ← Reviewer
              │                  └───────────────┘
              │                         │
              │        ┌────────────────┴────────────────┐
              │        ▼                                  ▼
              │  [Needs Revision]                    [Approved]
              │        │                                  │
              └────────┤                                  ▼
                       │                           ┌──────────┐
                       └──────────────────────────▶│   END    │
                                                   └──────────┘
```

**Core Features**: Task decomposition, agent collaboration, iterative optimization, parallel execution

#### 5. Automated Approval Workflow

```
┌─────────┐    ┌─────────┐    ┌───────────┐    ┌────────────────┐
│  START  │───▶│ submit  │───▶│ evaluate  │───▶│  Conditional   │
└─────────┘    └─────────┘    └───────────┘    │     Route      │
                                                    └────────────────┘
                                                     │
                              ┌──────────────────────┼────────────────┐
                              ▼                                       ▼
                      ┌────────────────┐                     ┌──────────────┐
                      │  auto_approve  │                     │human_approval│
                      └───────┬────────┘                     │  [interrupt] │
                              │                              └───────┬──────┘
                              │                                      │
                              └──────────────────────────────────────┘
                                               ▼
                                        ┌───────────┐
                                        │  notify   │
                                        └─────┬─────┘
                                              ▼
                                        ┌──────────┐
                                        │   END    │
                                        └──────────┘
```

**Core Features**: Auto evaluation, risk assessment, Human-in-the-Loop, notification sending

### Module Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                            API Layer                                 │
│                    routes/chat.py, routes/approval.py               │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Workflow Layer                              │
│     simple_router / customer_service / rag_qa / multi_agent / etc.  │
│                                                                      │
│                    extends BaseWorkflow (base.py)                   │
└───────────┬─────────────────────────────────────────┬───────────────┘
            │                                         │
            ▼                                         ▼
┌───────────────────────┐               ┌───────────────────────────────┐
│      Tools Layer      │               │         LLM Layer             │
│ search / calc / weather│               │ providers.py (DeepSeek/etc.) │
│    data / database    │               │       prompts.py              │
└───────────────────────┘               └───────────────────────────────┘
            │                                         │
            └─────────────────┬───────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Core Layer                                  │
│           checkpointer.py (MySQL)  │  logger.py (loguru)            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Config Layer                                  │
│                    settings.py (Pydantic Settings)                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Environment Requirements

#### Windows

- Python 3.11+
- uv package manager ([Installation Guide](https://docs.astral.sh/uv/))
- Docker Desktop (optional, for containerized deployment)

```powershell
# Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
python --version
```

#### Linux / macOS

- Python 3.11+
- uv package manager
- Docker & Docker Compose (optional)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
python3 --version
```

### Clone Project

```bash
# Clone from Gitee
git clone https://gitee.com/chain-engine/x-langgraph.git
cd x-langgraph

# Or clone from GitHub
git clone https://github.com/yeyushilai/x-langgraph.git
cd x-langgraph
```

### Install Dependencies

```bash
# Install dependencies using uv (recommended)
uv sync

# Activate virtual environment
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### Create Configuration File

```bash
# Copy environment variable template
cp .env.example .env
```

Edit `.env` file and configure necessary parameters:

```bash
# LLM API Configuration (at least one required)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL_NAME=deepseek-chat

# Checkpoint Database Configuration (MySQL)
CHECKPOINT_DB_HOST=localhost
CHECKPOINT_DB_PORT=3306
CHECKPOINT_DB_USER=root
CHECKPOINT_DB_PASSWORD=123456
CHECKPOINT_DB_NAME=x-langgraph

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
```

### Start Service

#### Option 1: Docker One-Click Start (Recommended)

```bash
# One-click start (MySQL + API service)
docker-compose up -d

# View logs
docker-compose logs -f api

# Test service
curl http://localhost:8000/health
```

After service starts:
- API Address: http://localhost:8000
- API Documentation: http://localhost:8000/docs

#### Option 2: Local Development

```bash
# 1. Start MySQL (using Docker)
docker run -d \
  --name x-langgraph-mysql \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=x-langgraph \
  -p 3306:3306 \
  mysql:8.0

# 2. Start API service
uv run python -m api.main

# Or use uvicorn
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Run examples
uv run python -m examples.hello_world
```

### Common Commands

```bash
# Docker related
docker-compose up -d          # Start service
docker-compose down           # Stop service
docker-compose logs -f api    # View logs
docker-compose restart api    # Restart API

# Local development
uv run python -m api.main              # Start API
uv run python -m examples.hello_world  # Run example
uv run pytest tests/ -v                # Run tests

# Code quality
uv run black src/ tests/               # Code formatting
uv run ruff check src/ tests/          # Code linting
uv run mypy src/                       # Type checking
```

## Tech Stack

| Category | Technology | Description |
|----------|------------|-------------|
| **Web Framework** | FastAPI | High-performance async web framework |
| **ASGI Server** | Uvicorn | SSE streaming response support |
| **LLM Framework** | LangGraph | Workflow orchestration core |
| | LangChain | Model invocation, tool integration |
| **Data Storage** | MySQL | Checkpointer state persistence |
| | SQLAlchemy | ORM framework |
| **Data Validation** | Pydantic | Data models, configuration management |
| **Logging** | Loguru | Structured logging |
| **HTTP Client** | httpx | Async HTTP requests |
| **Deployment** | Docker | Containerized deployment |
| | Docker Compose | Multi-container orchestration |
| **Package Manager** | uv | Fast Python package manager |

## API Documentation

After service starts, access API documentation at:

| Documentation Type | Address | Description |
|--------------------|---------|-------------|
| Swagger UI | http://localhost:8000/docs | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | Read-only API documentation |
| OpenAPI JSON | http://localhost:8000/openapi.json | OpenAPI specification file |

### Core API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Health check |
| `/chat` | POST | Synchronous chat |
| `/chat/stream` | POST | Streaming chat (SSE) |
| `/approval/resume` | POST | Resume approval workflow |
| `/approval/status/{id}` | GET | Get approval status |

### API Examples

```bash
# Synchronous chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Beijing weather", "session_id": "test-123", "workflow": "simple_router"}'

# Streaming chat (SSE)
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test-456"}'
```

## Storage Configuration

### Local Storage (MySQL Checkpointer)

Used for LangGraph workflow state persistence, supports interrupt and resume:

```bash
# .env configuration
CHECKPOINT_DB_HOST=localhost
CHECKPOINT_DB_PORT=3306
CHECKPOINT_DB_USER=root
CHECKPOINT_DB_PASSWORD=123456
CHECKPOINT_DB_NAME=x-langgraph
```

### Object Storage (Optional)

For RAG document storage, configure object storage services (e.g., MinIO, Alibaba Cloud OSS).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## References

- [LangGraph Official Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [Python Official Documentation](https://docs.python.org/3/)
- [uv Package Manager](https://docs.astral.sh/uv/)

## Contact

- **Author**: John Young
- **Email**: john.young@foxmail.com
- **Gitee**: https://gitee.com/yeyushilai
- **GitHub**: https://github.com/yeyushilai

---

**Let's explore the infinite possibilities of LangGraph together!** 🚀
