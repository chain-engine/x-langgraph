# x-langgraph

## Project Introduction

**x-langgraph** is an enterprise-grade LangGraph workflow orchestration framework designed to help developers quickly build complex multi-step workflow applications based on large language models. This project adopts engineering and modular design, providing complete workflow examples and production-grade deployment solutions, suitable as a reference template for enterprise applications.

**Use Cases**:
- Intelligent customer service systems (multi-turn dialogue, intent recognition, ticket routing)
- RAG document Q&A (knowledge base retrieval, context building)
- Multi-agent collaboration (task decomposition, parallel execution, result aggregation)
- Automated approval workflows (risk assessment, human-machine interaction)
- Complex business process orchestration (conditional routing, state management)

**Visual Interface**: Provides a Vue 3-based workflow visualization editor with drag-and-drop node editing, conditional routing configuration, and real-time state monitoring.

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
| **Checkpointer** | State persister | `MemorySaver()` / `AsyncMySQLSaver` |
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
- **State Persistence**: MySQL-based Checkpointer implementation with automatic fallback to MemorySaver when MySQL is unavailable
- **Human-in-the-Loop**: Support for manual approval, interrupt/resume and other interactive scenarios
- **Multiple LLM Providers**: Support for DeepSeek, Doubao, Alibaba Cloud and other mainstream models
- **Provider Pattern**: Decoupled tools and data sources, supporting Mock testing and real API switching
- **Streaming Output**: SSE streaming response support for better user experience
- **Unified Base Class**: All workflows inherit from `BaseWorkflow` with consistent interface
- **Layered Architecture**: Standard five-layer business architecture (API → Service → Repository → Models → Infra)
- **IOC Container**: Dependency injection container for easy unit testing and module decoupling
- **API Security**: API Key authentication + rate limiting (60 requests/minute/IP)
- **Observability**: Request ID middleware, structured logging, health checks, Prometheus metrics
- **Docker Deployment**: Complete containerized deployment solution
- **Visual Editor**: Vue 3 + Vue Flow based workflow visualization editor with drag-and-drop, conditional routing configuration, and real-time state monitoring

## Project Structure

```
x-langgraph/
├── server/                           # Backend API Service
│   ├── src/                          # Python source directory
│   │   ├── api/                      # API Layer
│   │   │   ├── routes/               # Route modules (chat.py, approval.py, workflows.py)
│   │   │   └── router.py             # Route registration management
│   │   ├── core/                     # Core Support Layer (config, logger, container, middleware)
│   │   ├── services/                 # Business Logic Layer (chat_service, approval_service, workflow_service)
│   │   ├── repositories/             # Data Access Layer (workflow_repository, workflow_definition_repository)
│   │   ├── models/                   # ORM Entity Layer
│   │   ├── infras/                   # Infrastructure Layer (mysql, redis, http_client)
│   │   ├── schemas/                  # Data Model Layer (Pydantic Schema)
│   │   ├── llm/                      # LLM Provider Module
│   │   ├── tools/                    # Tool Module (weather, search, calculation)
│   │   ├── workflows/                # Workflow Module (simple_router, approval, compiler)
│   │   └── main.py                   # FastAPI application entry
│   ├── examples/                     # Example code
│   ├── tests/                        # Test code
│   ├── data/                         # Workflow definition files (JSON)
│   ├── Dockerfile                    # Docker image config
│   ├── docker-compose.yml            # Docker compose config
│   ├── pyproject.toml                # Python project config
│   └── .env.example                  # Environment variable template
│
├── web/                              # Frontend Visual Interface (Vue 3)
│   ├── src/
│   │   ├── components/               # Components
│   │   │   ├── graph/                # Graph components (WorkflowCanvas, WorkflowNode, WorkflowEdge)
│   │   │   └── panels/               # Panel components (PropertyPanel, StateInspector, ExecutionLog)
│   │   ├── stores/                   # Pinia state management (workflow, execution)
│   │   ├── api/                      # API clients (http, workflows, sse)
│   │   ├── types/                    # TypeScript type definitions
│   │   ├── views/                    # Page views (WorkflowList, WorkflowEditor)
│   │   └── router/                   # Vue Router
│   ├── package.json                  # Node.js dependency config
│   ├── vite.config.ts                # Vite build config
│   └── tailwind.config.js            # Tailwind CSS config
│
├── .trae/                            # Trae AI tool config
├── LICENSE                           # License
├── README.md                         # Chinese documentation
└── README.en.md                      # English documentation
```

## System Architecture

### Standard Five-Layer Business Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        API Layer (api)                                   │
│         chat.py | approval.py | health.py | metrics.py                    │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    Business Logic Layer (services)                        │
│              ChatService | ApprovalService                                │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                     Data Access Layer (repositories)                      │
│                        WorkflowRepository                                │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────────┐ ┌───────────────────┐ ┌──────────────────────┐
│    ORM Entity Layer       │ │ Infrastructure    │ │   Core Support Layer │
│      (models)             │ │     Layer (infra)  │ │      (core)          │
│ ┌─────────────────────┐   │ │ ┌───────────────┐ │ │ ┌──────────────────┐ │
│ │ Workflow Model      │   │ │ │ MySQL Session  │ │ │ │ config.py        │ │
│ └─────────────────────┘   │ │ │ Redis Client   │ │ │ │ logger.py        │ │
│                           │ │ │ HTTP Client    │ │ │ │ middleware.py    │ │
│                           │ │ └───────────────┘ │ │ │ container.py     │ │
│                           │ │                   │ │ │ exceptions.py    │ │
│                           │ │                   │ │ └──────────────────┘ │
└───────────────────────────┘ └───────────────────┘ └──────────────────────┘
```

### Layer Dependency Rules

```
api → service → repository
                repository → models
                repository → infras
```

- **API Layer**: Only responsible for parameter receiving, authentication, forwarding calls, standardized returns. No business logic, no data operations.
- **Service Layer**: Handles business rules, transaction orchestration, multi-repository coordination, complex business calculations.
- **Repository Layer**: Encapsulates business CRUD, multi-table queries, pagination, conditional queries. Depends on infras for database sessions.
- **Models Layer**: Pure data table mapping models. Only defines fields and table relationships. No queries or business logic.
- **Infra Layer**: Encapsulates third-party middleware, clients, connection lifecycle, underlying resource management. **Never depends on repository/service/api**.

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
# Application Configuration
APP_NAME=x-langgraph
APP_ENVIRONMENT=development
APP_DEBUG=true

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database Configuration (Shared for Business Data + LangGraph State Persistence)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=langgraph

# API Security Configuration
API_KEY=your-api-key-here          # API access key (leave empty to disable auth)

# LLM API Configuration (at least one required)
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL_NAME=deepseek-chat

DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_API_BASE=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL_NAME=your-doubao-model

ALIYUN_API_KEY=your_aliyun_api_key
ALIYUN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
ALIYUN_MODEL_NAME=qwen-turbo

# Third-party API Configuration
AMAP_API_KEY=your-amap-api-key     # Amap API key (weather query)
SEARCH_API_KEY=your-search-api-key
SEARCH_API_URL=https://api.search.com/v1/search
```

### Start Service

#### Option 1: Docker One-Click Start (Recommended)

```bash
# Enter backend directory
cd server

# One-click start (MySQL + API service)
docker-compose up -d

# View logs
docker-compose logs -f api

# Test service
curl http://localhost:8000/health/live
```

After service starts:
- API Address: http://localhost:8000
- API Documentation: http://localhost:8000/docs

#### Option 2: Local Development

```bash
# 1. Enter backend directory
cd server

# 2. Start MySQL (using Docker)
docker run -d \
  --name x-langgraph-mysql \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=x-langgraph \
  -p 3306:3306 \
  mysql:8.0

# 3. Start API service (recommended)
uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 4. Run examples
uv run python -m examples.hello_world
```

### Start Frontend Visual Interface

```bash
# Enter frontend directory
cd web

# Install dependencies (first time)
npm install

# Start development server
npm run dev
```

After frontend starts:
- Visual Interface: http://localhost:5173
- Workflow Editor: http://localhost:5173/editor/simple_router

### Common Commands

```bash
# Backend commands (in server/ directory)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload  # Start API (recommended)
uv run python -m examples.hello_world                            # Run example
uv run pytest tests/ -v                                           # Run tests

# Frontend commands (in web/ directory)
npm run dev                          # Start development server
npm run build                        # Build production version
npm run check                        # TypeScript type checking
npm run lint                         # Code linting

# Docker commands (in server/ directory)
docker-compose up -d                 # Start service
docker-compose down                  # Stop service
docker-compose logs -f api           # View logs
docker-compose restart api           # Restart API

# Code quality (backend)
uv run black src/ tests/             # Code formatting
uv run ruff check src/ tests/        # Code linting
uv run mypy src/                     # Type checking
```

## Tech Stack

### Backend Tech Stack

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

### Frontend Tech Stack

| Category | Technology | Description |
|----------|------------|-------------|
| **Frontend Framework** | Vue 3 | Progressive JavaScript framework |
| **Build Tool** | Vite | Fast development build tool |
| **State Management** | Pinia | Vue official state management |
| **Routing** | Vue Router | Vue routing management |
| **Graph Visualization** | Vue Flow | Vue-based node graph visualization library |
| **UI Framework** | Tailwind CSS | Atomic CSS framework |
| **Icons** | Lucide Vue | Beautiful icon library |
| **Language** | TypeScript | Type-safe JavaScript |

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
| `/health/live` | GET | Liveness check (service running) |
| `/health/ready` | GET | Readiness check (dependencies ready) |
| `/metrics` | GET | Prometheus metrics |
| `/chat` | POST | Synchronous chat |
| `/chat/stream` | POST | Streaming chat (SSE) |
| `/approval/resume` | POST | Resume approval workflow |
| `/approval/status/{session_id}` | GET | Get approval status |
| `/workflows` | GET | Get workflow list |
| `/workflows/{name}` | GET | Get workflow definition |
| `/workflows/{name}` | POST | Create workflow |
| `/workflows/{name}` | PUT | Update workflow |
| `/workflows/{name}` | DELETE | Delete workflow |
| `/workflows/{name}/execute` | POST | Execute workflow (sync) |
| `/workflows/{name}/stream` | POST | Execute workflow (streaming SSE) |

### API Authentication

When `API_KEY` is configured, all `/chat` and `/approval` endpoints require an API Key in the request header:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"message": "Hello", "session_id": "test-123"}'
```

### Rate Limiting

- Default: 60 requests per minute per IP
- Returns HTTP 429 when exceeded

### API Examples

```bash
# Synchronous chat (with auth)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"message": "Beijing weather", "session_id": "test-123", "workflow": "simple_router"}'

# Streaming chat (SSE)
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"message": "Hello", "session_id": "test-456"}'

# Health check (Readiness)
curl http://localhost:8000/health/ready

# Get metrics
curl http://localhost:8000/metrics

# Resume approval workflow
curl -X POST http://localhost:8000/approval/resume \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"session_id": "test-123", "approved": true, "comments": "Approved"}'

# Get approval status
curl http://localhost:8000/approval/status/test-123 \
  -H "X-API-Key: your-api-key-here"
```

## Configuration Management

### Configuration Loading Priority

Three loading methods are supported, with priority from high to low:

1. **Environment variables**: e.g., `SERVER_PORT=8080`
2. **YAML configuration file**: `config.yaml` (root directory)
3. **Default configuration**: Default values in code

### YAML Configuration File Example (`config.yaml`)

```yaml
app:
  name: x-langgraph
  environment: development
  debug: true

server:
  host: 0.0.0.0
  port: 8000
  reload: true

logging:
  level: INFO
  file_path: logs/x-langgraph.log
  rotation: 1 day
  retention: 7 days

checkpoint_db:
  host: localhost
  port: 3306
  user: root
  password: your-password
  name: x-langgraph

llm:
  temperature: 0.0
  structured: false

deepseek:
  api_key: your-deepseek-api-key
  api_base: https://api.deepseek.com/v1
  model_name: deepseek-chat

doubao:
  api_key: your-doubao-api-key
  api_base: https://ark.cn-beijing.volces.com/api/v3
  model_name: your-doubao-model

aliyun:
  api_key: your-aliyun-api-key
  api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
  model_name: qwen-turbo

third_party:
  amap_api_key: your-amap-api-key
  search_api_key: your-search-api-key
  search_api_url: https://api.search.com/v1/search
  api_key: your-api-key-here
```

### Configuration Class Structure

The configuration system uses dataclass hierarchical management:

```
Settings
├── server          (ServerConfig)       - Server configuration
├── logging         (LoggingConfig)      - Logging configuration
├── cors            (CORSConfig)         - CORS configuration
├── rate_limit      (RateLimitConfig)    - Rate limiting configuration
├── database        (DatabaseConfig)     - Business database configuration
├── checkpoint_db   (CheckpointDBConfig) - Checkpoint database configuration
├── redis           (RedisConfig)        - Redis configuration
├── security        (SecurityConfig)     - Security configuration
├── api_docs        (ApiDocsConfig)      - API documentation configuration
├── llm             (LLMConfig)          - LLM general configuration
├── deepseek        (DeepSeekConfig)     - DeepSeek configuration
├── doubao          (DoubaoConfig)       - Doubao configuration
├── aliyun          (AliyunConfig)       - Alibaba Cloud configuration
└── third_party     (ThirdPartyConfig)   - Third-party API configuration
```

## Visual Interface

### Overview

The workflow visualization editor provides graphical workflow design and management capabilities, helping developers intuitively understand and operate LangGraph workflows.

**Core Features**:
- **Workflow List Management**: View, search, create, and delete workflow definitions
- **Visual Canvas**: Vue Flow-based node graph editor with drag-and-drop, zoom, and pan support
- **Node Editing**: Add, edit, and delete nodes; configure node properties (type, Handler, position, config)
- **Edge Management**: Create, edit, and delete edges; supports normal edges and conditional edges (conditional routing)
- **Real-time State Monitoring**: Real-time display of node status and edge flow during workflow execution
- **Execution Logs**: View complete execution log records

### Interface Layout

The visualization editor adopts a three-panel layout:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Top Toolbar                                 │
│  ← Back  │  Workflow Name  │  Save Button                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌───────────────────────────┐  ┌─────────────┐  │
│  │   Left      │  │         Middle Canvas      │  │   Right     │  │
│  │   Panel     │  │                           │  │   Panel     │  │
│  │             │  │   [START]  →  [router]    │  │             │  │
│  │ • State     │  │             ↓    ↓    ↓    │  │ • Property  │  │
│  │   Schema    │  │        [search] [calc]    │  │ • State     │  │
│  │             │  │             ↓    ↓        │  │ • Execution │  │
│  │ • Node List │  │         [END]             │  │   Logs      │  │
│  │             │  │                           │  │             │  │
│  └─────────────┘  └───────────────────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                         Bottom Execution Bar                        │
│  Input Message │ Session ID │ Execute │ Stream Execute │ Stop       │
└─────────────────────────────────────────────────────────────────────┘
```

### Node Types

| Type | Color | Icon | Description |
|------|-------|------|-------------|
| **router** | Purple | 🔀 | Routing node, routes to different branches based on conditions |
| **processor** | Cyan | ⚙️ | Processing node, executes business logic |
| **tool** | Green | 🛠️ | Tool node, calls external tools (search, calculation, weather) |
| **unknown** | Red | ❓ | Unknown node, handles unrecognized requests |
| **end** | Gray | ⏹️ | End node, workflow termination point |

### Edge Types

| Type | Style | Description |
|------|-------|-------------|
| **normal** | Solid line | Normal edge, direct flow |
| **conditional** | Dashed line | Conditional edge, routes based on state field values |

### Access

1. Start the backend API service (port 8000)
2. Start the frontend development server (port 5173)
3. Open browser: http://localhost:5173

### Usage Flow

```
1. Enter workflow list page → View all workflows
   ↓
2. Click workflow card → Enter editor
   ↓
3. View nodes and edges on canvas
   ↓
4. Click node/edge → Edit properties in right panel
   ↓
5. Input message at bottom → Click execute to run workflow
   ↓
6. View real-time status updates and execution logs
```

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