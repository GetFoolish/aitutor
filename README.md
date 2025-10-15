# DASHSystem: Next Question Generator

A smart learning system that adapts to each student's progress using MongoDB and Python. It figures out what you need to practice next and picks the right questions for you.

## What this does

Think of it like a personal tutor that remembers everything you've learned and forgotten. It uses a memory model to track your skills and suggests what to practice next. The system gets smarter as you use it.

## Getting started

First, make sure you have MongoDB running on your machine:

**Option 1: Using Docker (easiest)**
```bash
docker run -d --name mongo -p 27017:27017 -v mongo-data:/data/db mongo:7
```

**Option 2: Install MongoDB locally**
```bash
# Ubuntu/Debian
sudo apt install mongodb
sudo systemctl start mongodb

# Or use your package manager
```

## Setup

1. **Install Python packages**
```bash
pip install -r requirements.txt
```

2. **Load some sample data**
```bash
python3 -m migrations.seed_skills
python3 -m migrations.seed_questions
```

3. **Try it out**
```bash
PYTHONPATH=. python3 -m src.demo_run
```

## How it works

The system has three main parts:

- **Skills**: What you can learn (like "multiplication" or "algebra")
- **Questions**: Practice problems for each skill
- **Users**: Your progress and what you've practiced

When you answer a question, the system updates your skill levels and decides what to show you next. It's designed to keep you challenged but not overwhelmed.

## Managing the curriculum

You can add new skills through a simple workflow:

```bash
# Propose a new skill
PYTHONPATH=. python3 -m src.workflow_cli propose division_basics "Division Basics" 3.2.2 0.25 0.09

# See what's pending
PYTHONPATH=. python3 -m src.workflow_cli list

# Approve it
PYTHONPATH=. python3 -m src.workflow_cli approve division_basics
```

## Testing

Run the tests to make sure everything works:

```bash
PYTHONPATH=. python3 -m pytest -v
```

## Project structure

```
src/dash_system/          # Main system code
├── db.py                 # Database connections
├── dash.py               # Core learning logic
├── skills_cache.py       # Fast skill lookups
├── workflow.py           # Curriculum management
└── llm.py                # AI tagging (optional)

migrations/               # Data loading scripts
tests/                    # Test files
```

## Configuration

Create a `.env` file if you want to change settings:

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=adaptive_learning_db
```

## What's included

- Smart question selection (picks unseen questions)
- Skill tracking with memory decay
- Human approval workflow for new content
- Easy data migration from existing systems
- Built-in testing

The system is ready to use and can handle real students learning real skills. It's designed to scale from a few users to thousands.

## Notes

- Skills are cached in memory for speed
- All updates are atomic (safe for multiple users)
- Questions are selected to avoid repeats
- The system learns from each interaction