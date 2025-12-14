# Quick Start Guide

Get up and running with Deep Research POC in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))
- Terminal/command line access

## Step-by-Step Setup

### 1. Install `uv` (Fast Python Package Manager)

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or use pip:
```bash
pip install uv
```

### 2. Clone or Download the Project

```bash
cd /path/to/deep-research-poc
```

### 3. Run the Setup Script

```bash
./setup.sh
```

This will:
- Create `.env` file from template
- Install all dependencies
- Set up the project structure

### 4. Configure Your API Key

Edit `.env` file:
```bash
nano .env  # or use your favorite editor
```

Add your OpenAI API key:
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

Save and exit.

### 5. Install Temporal CLI

**macOS:**
```bash
brew install temporal
```

**Linux:**
```bash
curl -sSf https://temporal.download/cli.sh | sh
```

**Windows:**
Download from [Temporal releases](https://github.com/temporalio/cli/releases)

### 6. Start Temporal Server

Open a new terminal window:
```bash
temporal server start-dev
```

Keep this running. You should see:
```
Temporal server is running on localhost:7233
```

### 7. Start the Worker

Open another terminal window:
```bash
cd /path/to/deep-research-poc
uv run python -m deep_research_poc.worker
```

You should see:
```
[INFO] worker_started task_queue=deep-research-queue
```

### 8. Run Your First Research!

In a third terminal:
```bash
cd /path/to/deep-research-poc
uv run python -m deep_research_poc.starter "What are the key features of Python 3.12?"
```

## What Just Happened?

1. **Starter** sent your research question to Temporal
2. **Temporal** created a new workflow instance
3. **Worker** picked up the workflow and started executing
4. **AI Agent** used OpenAI to research your question
5. **Results** were synthesized and displayed

## Terminal Layout

For the best experience, arrange your terminals like this:

```
┌────────────────────┬────────────────────┐
│   Temporal Server  │    Worker          │
│   (Terminal 1)     │   (Terminal 2)     │
│                    │                    │
│  temporal server   │  python -m         │
│  start-dev         │  deep_research...  │
│                    │                    │
├────────────────────┴────────────────────┤
│           Your Commands                 │
│           (Terminal 3)                  │
│                                         │
│  python -m deep_research_poc.starter... │
└─────────────────────────────────────────┘
```

## Using the Makefile (Optional)

If you prefer using Make:

```bash
# Terminal 1
make run-temporal

# Terminal 2
make run-worker

# Terminal 3
make run-example
```

## Testing the Human-in-the-Loop

### Start a research that requires approval:

```bash
uv run python -m deep_research_poc.starter "Explain quantum computing"
```

### You'll see an approval request in the worker terminal:

```
================================================================================
HUMAN APPROVAL REQUIRED
================================================================================
Request ID: 550e8400-e29b-41d4-a716-446655440000
Workflow ID: research-abc123...
Question: Explain quantum computing
Confidence: 0.85
...
```

### Copy the workflow ID and request ID, then approve:

```bash
uv run python -m deep_research_poc.starter \
  --approve research-abc123 550e8400-e29b-41d4-a716-446655440000
```

When prompted:
```
Approve this research? (y/n): y
```

## Common Issues

### "temporal: command not found"
**Solution**: Install Temporal CLI (see Step 5)

### "Connection refused to localhost:7233"
**Solution**: Start Temporal server (Step 6)

### "OPENAI_API_KEY not found"
**Solution**: Add your API key to `.env` file (Step 4)

### "ModuleNotFoundError: No module named 'deep_research_poc'"
**Solution**: Run `uv sync` to install dependencies

### Worker not picking up work
**Solution**: 
1. Check Temporal server is running
2. Check worker is running
3. Verify task queue name matches in `.env`

## Next Steps

Now that you have it running:

1. **Read the README**: `README.md` for detailed documentation
2. **Check examples**: `examples/example_usage.py` for programmatic usage
3. **Explore code**: Start with `src/deep_research_poc/workflows.py`
4. **Run tests**: `make test` or `uv run pytest`
5. **Review architecture**: `docs/ARCHITECTURE.md` for system design

## Quick Reference Commands

```bash
# Start everything
make run-temporal        # Terminal 1
make run-worker         # Terminal 2

# Run research
uv run python -m deep_research_poc.starter "Your question"

# Check workflow status
uv run python -m deep_research_poc.starter --status <workflow-id>

# Send approval
uv run python -m deep_research_poc.starter --approve <workflow-id> <request-id>

# Run tests
make test

# Format code
make format

# Type check
make type-check
```

## Getting Help

- Check the [README](../README.md) for detailed docs
- Review [ARCHITECTURE](./ARCHITECTURE.md) for system design
- Look at [examples](../examples/) for code samples
- Open an issue on GitHub

## Troubleshooting Checklist

- [ ] Python 3.10+ installed (`python --version`)
- [ ] `uv` installed (`uv --version`)
- [ ] Temporal CLI installed (`temporal --version`)
- [ ] OpenAI API key set in `.env`
- [ ] Dependencies installed (`uv sync`)
- [ ] Temporal server running (Terminal 1)
- [ ] Worker running (Terminal 2)
- [ ] No firewall blocking localhost:7233

---

**Ready to research? Start with a simple question and watch the magic happen! 🚀**
