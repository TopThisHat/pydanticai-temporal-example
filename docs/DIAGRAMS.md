# System Diagrams

## High-Level System Architecture

```
                                 ┌───────────────────┐
                                 │   User / Client   │
                                 └─────────┬─────────┘
                                           │
                                           │ CLI / API
                                           ▼
                                 ┌───────────────────┐
                                 │  Starter Script   │
                                 │   (starter.py)    │
                                 └─────────┬─────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
            ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
            │ Start        │      │ Send         │      │ Query        │
            │ Workflow     │      │ Approval     │      │ Status       │
            └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
                   │                     │                     │
                   └──────────────────┬──┴─────────────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │   Temporal Server      │
                          │  (Workflow Engine)     │
                          │                        │
                          │  • State Management    │
                          │  • Event History       │
                          │  • Signal Routing      │
                          │  • Query Handling      │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │    Worker Process      │
                          │    (worker.py)         │
                          │                        │
                          │  • Execute Workflows   │
                          │  • Run Activities      │
                          │  • Handle Signals      │
                          └───────────┬────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
         ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
         │  Workflow        │ │   Activities     │ │  Research       │
         │  Orchestration   │ │   Execution      │ │  Agent          │
         │  (workflows.py)  │ │  (activities.py) │ │  (agent.py)     │
         │                  │ │                  │ │                 │
         │ • Iteration Loop │ │ • Research       │ │ • pydantic-ai   │
         │ • Approval Gates │ │ • Synthesis      │ │ • OpenAI API    │
         │ • State Tracking │ │ • Logging        │ │ • Prompting     │
         └──────────────────┘ └─────────┬────────┘ └────────┬────────┘
                                        │                   │
                                        └───────┬───────────┘
                                                │
                                                ▼
                                   ┌──────────────────────┐
                                   │    OpenAI API        │
                                   │    (GPT-4)           │
                                   │                      │
                                   │  • LLM Inference     │
                                   │  • Structured Output │
                                   └──────────────────────┘
```

## Research Workflow State Machine

```
                           ┌─────────────┐
                           │   START     │
                           └──────┬──────┘
                                  │
                                  ▼
                       ┌────────────────────┐
                       │  PENDING           │
                       │  (Initialize)      │
                       └──────┬─────────────┘
                              │
                              ▼
                   ┌────────────────────────┐
                   │  IN_PROGRESS           │
                   │  (Execute Research)    │
                   └──────┬─────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐  ┌──────────────┐  ┌──────────┐
    │ Iteration│  │   Approval   │  │  Error   │
    │ Complete │  │   Required?  │  │ Occurred │
    └────┬─────┘  └──────┬───────┘  └────┬─────┘
         │               │                │
         │        ┌──────┴──────┐         │
         │        │             │         │
         │        ▼             ▼         │
         │   ┌─────────┐  ┌─────────┐    │
         │   │ AWAIT   │  │ TIMEOUT │    │
         │   │APPROVAL │  └────┬────┘    │
         │   └────┬────┘       │         │
         │        │             │         │
         │   ┌────┴────┐        │         │
         │   │         │        │         │
         │   ▼         ▼        │         │
         │┌────────┐┌────────┐ │         │
         ││APPROVED││REJECTED│ │         │
         │└───┬────┘└───┬────┘ │         │
         │    │         │      │         │
         └────┼─────────┘      │         │
              │                │         │
    ┌─────────┴────────┐       │         │
    │                  │       │         │
    ▼                  ▼       ▼         ▼
┌─────────┐      ┌──────────────────────────┐
│Continue │      │      Terminal States     │
│ Next    │      │                          │
│Iteration│      │  • COMPLETED             │
└────┬────┘      │  • REJECTED              │
     │           │  • FAILED                │
     └───────────┤                          │
                 └──────────────────────────┘
```

## Human-in-the-Loop Sequence Diagram

```
Starter          Temporal         Worker          Activity        Agent          Human
  │                 │               │                │              │              │
  │ Start Workflow  │               │                │              │              │
  ├────────────────>│               │                │              │              │
  │                 │               │                │              │              │
  │                 │  Execute      │                │              │              │
  │                 ├──────────────>│                │              │              │
  │                 │               │                │              │              │
  │                 │               │ Run Research   │              │              │
  │                 │               ├───────────────>│              │              │
  │                 │               │                │              │              │
  │                 │               │                │ Call OpenAI  │              │
  │                 │               │                ├─────────────>│              │
  │                 │               │                │<─────────────┤              │
  │                 │               │<───────────────┤   Results    │              │
  │                 │               │                │              │              │
  │                 │               │ Log Approval   │              │              │
  │                 │               ├───────────────>│              │              │
  │                 │               │                │              │              │
  │                 │               │                │ Print/Notify │              │
  │                 │               │                ├──────────────┼─────────────>│
  │                 │               │                │              │              │
  │                 │               │ Wait Signal... │              │              │
  │                 │               │ (timeout)      │              │              │
  │                 │               │                │              │              │
  │                 │               │                │              │ Review &     │
  │                 │               │                │              │ Decide       │
  │                 │               │                │              │              │
  │ Send Approval   │               │                │              │              │
  │<────────────────┼───────────────┼────────────────┼──────────────┼──────────────┤
  │                 │               │                │              │              │
  ├────────────────>│ Signal        │                │              │              │
  │                 ├──────────────>│                │              │              │
  │                 │               │                │              │              │
  │                 │               │ Continue...    │              │              │
  │                 │               ├───────────────>│              │              │
  │                 │               │                │              │              │
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                              │
└────┬─────────────────────────────────────────────────────────┬───┘
     │                                                         │
     ▼                                                         ▼
┌─────────────┐                                      ┌─────────────┐
│ Research    │                                      │   Human     │
│ Query       │                                      │  Approval   │
│             │                                      │  Response   │
│ • query     │                                      │             │
│ • max_iter  │                                      │ • approved  │
│ • metadata  │                                      │ • feedback  │
└─────┬───────┘                                      └──────┬──────┘
      │                                                     │
      │ ┌───────────────────────────────────────────────────┘
      │ │
      ▼ ▼
┌──────────────────────────────────────────────────────────────────┐
│                     PROCESSING LAYER                             │
│                                                                  │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐        │
│  │  Workflow  │─────>│ Activities │─────>│   Agent    │        │
│  │            │      │            │      │            │        │
│  │ • Loop     │      │ • Research │      │ • Prompt   │        │
│  │ • State    │      │ • Synth    │      │ • Parse    │        │
│  │ • Signals  │      │ • Log      │      │ • Validate │        │
│  └────────────┘      └────────────┘      └────────────┘        │
│                                                                  │
└─────┬────────────────────────────────────────────────────────┬──┘
      │                                                        │
      ▼                                                        ▼
┌─────────────┐                                      ┌─────────────┐
│ Research    │                                      │   Approval  │
│ Steps       │                                      │   Requests  │
│             │                                      │             │
│ • iteration │                                      │ • request   │
│ • findings  │                                      │ • context   │
│ • sources   │                                      │ • timestamp │
│ • followup  │                                      └─────────────┘
└─────┬───────┘
      │
      ▼
┌──────────────────────────────────────────────────────────────────┐
│                        OUTPUT LAYER                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           Research Result                            │       │
│  │                                                      │       │
│  │  • status (COMPLETED/REJECTED/FAILED)                │       │
│  │  • steps (all research iterations)                   │       │
│  │  • final_summary (synthesized findings)              │       │
│  │  • approval_responses (human feedback)               │       │
│  │  • metadata (timing, iterations, etc.)               │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Component Dependencies

```
                    ┌──────────────┐
                    │  config.py   │
                    │  (Settings)  │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐   ┌──────────┐
    │agent.py  │    │worker.py │   │starter.py│
    │          │    │          │   │          │
    └────┬─────┘    └────┬─────┘   └────┬─────┘
         │               │              │
         │               ▼              │
         │        ┌──────────────┐      │
         │        │workflows.py  │      │
         │        │              │      │
         │        └──────┬───────┘      │
         │               │              │
         │               ▼              │
         │        ┌──────────────┐      │
         │        │activities.py │      │
         │        │              │      │
         │        └──────┬───────┘      │
         │               │              │
         └───────────────┼──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  models.py   │
                  │  (Pydantic)  │
                  └──────────────┘
```

## Deployment Architecture (Production)

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
      ┌───────────┐  ┌───────────┐  ┌───────────┐
      │ Worker 1  │  │ Worker 2  │  │ Worker N  │
      └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                           ▼
                ┌────────────────────┐
                │ Temporal Cloud     │
                │ (Managed Service)  │
                └──────────┬─────────┘
                           │
                ┌──────────┼──────────┐
                │          │          │
                ▼          ▼          ▼
         ┌──────────┐ ┌─────────┐ ┌──────────┐
         │ Postgres │ │  Redis  │ │ S3       │
         │ (State)  │ │ (Cache) │ │ (Results)│
         └──────────┘ └─────────┘ └──────────┘

         ┌────────────────────────────────────┐
         │        External Services           │
         │                                    │
         │  • OpenAI API (Research)           │
         │  • Slack/Email (Notifications)     │
         │  • DataDog (Monitoring)            │
         │  • Sentry (Error Tracking)         │
         └────────────────────────────────────┘
```

## Testing Pyramid

```
                    ┌──────────────┐
                    │  Manual/E2E  │
                    │    Tests     │
                    └──────┬───────┘
                           │
                 ┌─────────┴─────────┐
                 │   Integration     │
                 │     Tests         │
                 │ (test_workflows)  │
                 └─────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              │     Unit Tests          │
              │   (test_agent)          │
              │   - Mocked OpenAI       │
              │   - Isolated logic      │
              └─────────────────────────┘
```

---

These diagrams illustrate the complete system architecture, data flow, and component relationships in the Deep Research POC.
