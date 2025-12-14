# Architecture Documentation

## System Overview

The Deep Research POC implements a durable, AI-powered research system using a **microservices architecture** with **event-driven workflows** and **human-in-the-loop** patterns.

## Component Architecture

### 1. Core Components

#### ResearchAgent (`agent.py`)
- **Purpose**: AI-powered research execution using pydantic-ai and OpenAI
- **Responsibilities**:
  - Conduct iterative research on questions
  - Generate structured research findings
  - Synthesize multiple research steps
  - Maintain confidence scoring
- **External Dependencies**: OpenAI API (GPT-4)
- **Pattern**: Facade Pattern (simplifies pydantic-ai usage)

#### Temporal Workflows (`workflows.py`)
- **Purpose**: Orchestrate long-running research processes
- **Key Features**:
  - Durable execution (survives worker crashes)
  - State persistence
  - Signal handling (for human approval)
  - Query support (for status inspection)
- **Pattern**: Workflow Pattern, State Machine Pattern

#### Temporal Activities (`activities.py`)
- **Purpose**: Execute side-effect operations
- **Activities**:
  - `conduct_research_activity`: Execute AI research
  - `synthesize_findings_activity`: Create final summary
  - `log_approval_request_activity`: Handle approval notifications
  - `validate_approval_response_activity`: Validate human input
- **Pattern**: Activity Pattern, Circuit Breaker (via retries)

### 2. Data Flow

```
┌─────────────┐
│   Starter   │
│   (Client)  │
└──────┬──────┘
       │ 1. Start Workflow
       ▼
┌─────────────────┐
│  Temporal       │
│  Server         │◄────── 2. Store Workflow State
└──────┬──────────┘
       │ 3. Schedule Activities
       ▼
┌─────────────────┐
│    Worker       │
│  (Executes      │
│   Workflow)     │
└──────┬──────────┘
       │ 4. Execute Activities
       ▼
┌─────────────────┐
│  Activities     │
│  - Research     │
│  - Synthesis    │
│  - Approval     │
└──────┬──────────┘
       │ 5. Call AI Agent
       ▼
┌─────────────────┐
│ ResearchAgent   │
│  (pydantic-ai)  │
└──────┬──────────┘
       │ 6. API Call
       ▼
┌─────────────────┐
│   OpenAI API    │
│   (GPT-4)       │
└─────────────────┘
```

### 3. Human-in-the-Loop Pattern

```
Workflow Execution
      │
      ▼
┌──────────────────┐
│ Research Step    │
│ Completed        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Create Approval  │
│ Request          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Log Request      │◄────── Activity (sends notifications)
│ (Activity)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Wait for Signal  │◄────── Temporal Signal Mechanism
│ with Timeout     │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐  ┌────────┐
│Approved│  │Timeout │
└───┬────┘  └───┬────┘
    │           │
    ▼           ▼
Continue    Fallback
Research    Behavior
```

### 4. Data Models

All data models use **Pydantic v2** for:
- Type validation
- Serialization/deserialization
- Documentation
- JSON schema generation

Key Models:
- `ResearchQuery`: Input specification
- `ResearchStep`: Single iteration result
- `ResearchResult`: Final workflow output
- `HumanApprovalRequest`: Approval request data
- `HumanApprovalResponse`: Approval decision
- `WorkflowInput/Output`: Workflow boundaries

### 5. Error Handling Strategy

#### Activity Level
```python
@activity.defn
async def conduct_research_activity(...):
    try:
        # Execute research
        result = await agent.research(...)
        return result
    except Exception as e:
        logger.error("research_failed", error=str(e))
        # Return degraded result instead of failing
        return ResearchStep(
            confidence=0.0,
            findings=f"Research failed: {str(e)}",
            requires_followup=False,
        )
```

**Strategy**: Graceful degradation over failure

#### Workflow Level
```python
try:
    # Execute workflow logic
    for iteration in range(max_iterations):
        step = await conduct_research(...)
        # ...
except Exception as e:
    result.status = ResearchStatus.FAILED
    result.error_message = str(e)
```

**Strategy**: Capture errors, continue execution when possible

#### Retry Policies
All activities use exponential backoff:
- Initial interval: 1 second
- Maximum interval: 30 seconds
- Maximum attempts: 3
- Backoff coefficient: 2.0

### 6. Configuration Management

**Pattern**: Settings Pattern (Pydantic BaseSettings)

```python
class Settings(BaseSettings):
    # Automatically loads from:
    # 1. Environment variables
    # 2. .env file
    # 3. Default values
    
    openai_api_key: str
    temporal_address: str = "localhost:7233"
    # ...
```

**Benefits**:
- Type-safe configuration
- Environment variable validation
- Easy testing (override settings)
- Documentation via Field()

### 7. Logging Strategy

**Pattern**: Structured Logging (structlog)

```python
logger.info(
    "research_completed",
    iteration=iteration,
    confidence=step.confidence,
    requires_followup=step.requires_followup,
)
```

**Benefits**:
- Machine-readable logs
- Easy filtering and searching
- Contextual information
- Integration with monitoring systems

### 8. Testing Strategy

#### Unit Tests
- Mock external dependencies (OpenAI, Temporal)
- Test business logic in isolation
- Fast execution

#### Integration Tests
- Use Temporal's `WorkflowEnvironment` for testing
- Test workflow execution end-to-end
- Verify signal/query behavior

#### Test Organization
```
tests/
├── conftest.py           # Pytest configuration
├── test_agent.py         # Agent unit tests
└── test_workflows.py     # Workflow integration tests
```

## Design Patterns Used

### 1. Repository Pattern
Separation between data access and business logic
- Activities = data access layer
- Workflows = business logic layer

### 2. Facade Pattern
`ResearchAgent` simplifies pydantic-ai complexity

### 3. Strategy Pattern
Different research strategies can be plugged in

### 4. Observer Pattern
Temporal signals for human approval

### 5. Saga Pattern
Long-running transactions with compensation

### 6. Circuit Breaker
Retry policies prevent cascade failures

## Scalability Considerations

### Horizontal Scaling
- **Workers**: Run multiple worker processes
- **Activities**: Stateless, can be distributed
- **Workflows**: Temporal handles distribution

### Vertical Scaling
- **OpenAI API**: Rate limiting and quotas
- **Temporal Server**: Resource allocation

### Performance Optimization
- **Caching**: Cache research results (future)
- **Batching**: Batch multiple research steps (future)
- **Parallelization**: Run independent steps concurrently (future)

## Security Considerations

### API Keys
- Store in environment variables
- Never commit to version control
- Use secrets management in production

### Data Privacy
- Research data may contain sensitive information
- Implement encryption at rest (production)
- Audit logging for compliance

### Access Control
- Temporal namespace isolation
- API authentication for production
- Role-based approval workflows

## Production Deployment Checklist

- [ ] Use Temporal Cloud or self-hosted cluster
- [ ] Implement secrets management (AWS Secrets Manager, etc.)
- [ ] Set up monitoring and alerting
- [ ] Configure logging aggregation (ELK, Splunk, etc.)
- [ ] Implement rate limiting for OpenAI API
- [ ] Add authentication and authorization
- [ ] Set up CI/CD pipeline
- [ ] Configure auto-scaling for workers
- [ ] Implement backup and disaster recovery
- [ ] Add health checks and metrics endpoints
- [ ] Set up distributed tracing (OpenTelemetry)
- [ ] Configure resource limits (memory, CPU)

## Future Enhancements

1. **Multi-Model Support**: Support multiple AI providers (Anthropic, Google, etc.)
2. **Web Interface**: Dashboard for managing research workflows
3. **API Layer**: REST/GraphQL API for integration
4. **Advanced Approval**: Multi-level approval chains
5. **Research Templates**: Pre-configured research strategies
6. **Result Persistence**: Store results in database
7. **Notification System**: Email, Slack, MS Teams integration
8. **Analytics**: Research quality metrics and insights
9. **Version Control**: Track research iterations over time
10. **Collaboration**: Multi-user approval and feedback

## References

- [Temporal Documentation](https://docs.temporal.io/)
- [pydantic-ai Documentation](https://ai.pydantic.dev/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Structlog Documentation](https://www.structlog.org/)
