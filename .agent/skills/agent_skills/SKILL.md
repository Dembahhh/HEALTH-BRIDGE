---
name: Project Bootstrapper
description: A skill to initialize and structure projects according to the 3-layer architecture (Directives, Orchestration, Execution).
---

# Project Bootstrapper Skill

Use this skill when the user asks you to "initialize the project", "set up the agent structure", or "prepare the repo" for a new or existing project.

## Workflow

### 1. Analyze Context

First, understand what the project is about and what already exists.

- Read `README.md`, `docs/`, or any other high-level documentation in the root.
- List the current directory to see if standard folders (`directives`, `execution`, `.tmp`) already exist.
- **Pitfall Check**: Look for existing "messy" scripts in the root that should be moved to `execution/`.
- **Pitfall Check**: Check if `.gitignore` exists and if it excludes `.tmp/` and `.env`.

### 2. Propose Initialization Plan

Before creating any files, form a mental plan or a scratchpad plan.

- **Architecture**: We want the 3-Layer Architecture:
  - `directives/`: Markdown SOPs (Standard Operating Procedures).
  - `execution/`: Python scripts (tools).
  - `.tmp/`: Intermediate files (ignored by git).
  - `AGENTS.md` (or similar): The instructions you are reading now, mirrored for the project context.
- **Task Tracking**: We want `task.md` and `implementation_plan.md` in the brain/artifacts directory (which you manage automatically), but we also want a project-level `task.md` if the user prefers it there. *Default to using the agent brain artifacts for active tracking, but maybe create a project root `b_plan.md` or similar if requested.*
- **Pitfall Check**: If the project is NOT Python-based (e.g., purely Node.js), adapt the `execution/` folder expectation (e.g., `execution/` can contain `.js` or `.ts` scripts).

### 3. User Confirmation

**CRITICAL**: You must ask the user for confirmation if you are about to make significant structural changes or if you found potential pitfalls.

- Use `notify_user` to present a brief summary:
  - "I found a README describing X."
  - "I plan to create `directives/` and `execution/`."
  - "I noticed strict `.env` usage is missing in `.gitignore`, I will add it."
  - "Do you want me to proceed?"

### 4. Execution

Once confirmed (or if the user gave a "Do whatever is needed" mandate):

#### A. Create Directories

```bash
mkdir -p directives execution .tmp
```

#### B. Create/Update .gitignore

Ensure the following are ignored:

```text
.tmp/
.env
__pycache__/
*.pyc
.DS_Store
```

#### C. Create Initial Directive

Create `directives/00_master_directive.md` (or similar) that serves as the entry point.

- Content should briefly explain how to use this project's specific agents/tools.

#### D. Create AGENTS.md

Create a file named `AGENTS.md` in the root (if it doesn't exist) with the standard 3-layer architecture instructions. This ensures that *any* AI agent opening this repo knows how to behave.

- *Tip*: You can copy the content from `AGENTS.md` if you have it in your knowledge base, or write a concise version explaining the `Directive -> Orchestration -> Execution` flow.

#### E. Move/Refactor Existing Code

If you found loose scripts in the root that fit the "Execution" layer, move them to `execution/` and update references.

### 5. Final Report

Report back to the user:

- "Project initialized."
- "Created `directives/`, `execution/`."
- "Added `AGENTS.md` for context."
- "Ready to start working on tasks."
