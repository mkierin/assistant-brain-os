"""
Coding Agent - Autonomous code generation using skill files.

Reads skill files (Markdown + YAML frontmatter) from the skills/ directory,
plans tasks, generates code and documentation, and writes output files
to a project directory.
"""

from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import AgentResponse
from common.config import CODER_MODEL
from common.llm import get_pydantic_ai_model
from common.skill_loader import SkillLoader
from common.project_writer import ProjectWriter
from datetime import datetime
from typing import Optional
import uuid
import json

# Use a more capable model for code generation
model = get_pydantic_ai_model()

# Module-level state (reset per execute() call)
_skill_loader: Optional[SkillLoader] = None
_project_writer: Optional[ProjectWriter] = None
_plan_steps: list = []

def _get_skill_loader() -> SkillLoader:
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader


# Coding agent
coder_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You are an expert coding agent that generates complete, production-ready projects.

Your workflow:
1. FIRST: Call find_skills() to discover relevant skill files for the task
2. SECOND: Call load_skill() to read the full content of matching skills (templates, patterns, best practices)
3. THIRD: Call create_plan() with a detailed step-by-step execution plan
4. FOURTH: For each step, call write_file() to generate code following the skill patterns and templates
5. FINALLY: Call write_summary() to create the project README and finalize

IMPORTANT RULES:
- Always search for and load skills before generating any code
- Follow the templates and patterns from skill files exactly
- Apply all best practices and avoid all anti-patterns listed in skills
- Generate complete, working files - never use placeholders like "TODO" or "..."
- Write clear comments and documentation in every file
- Create a logical directory structure (src/, config/, docs/)
- Name files according to skill naming conventions
- Each write_file() call should produce a complete, standalone file
- Use search_knowledge() if you need context about the user's existing data or preferences

Be thorough and professional. Generate code that follows industry standards."""
)


@coder_agent.tool
async def find_skills(ctx: RunContext[None], query: str) -> str:
    """
    Search the skills directory for relevant skill files.
    Returns matching skill names, descriptions, and file paths.
    Use this FIRST to discover what skills are available for the task.

    Args:
        query: Search terms related to the task (e.g., "qlik data model star schema")
    """
    try:
        loader = _get_skill_loader()
        results = loader.search(query, limit=10)

        if not results:
            return "No matching skills found. You'll need to generate code from general knowledge."

        output = f"Found {len(results)} matching skills:\n\n"
        for i, meta in enumerate(results, 1):
            output += f"{i}. **{meta.name}** (domain: {meta.domain})\n"
            output += f"   Description: {meta.description}\n"
            output += f"   Tags: {', '.join(meta.tags)}\n"
            output += f"   Keywords: {', '.join(meta.keywords[:5])}\n"
            output += f"   Output types: {', '.join(meta.output_types)}\n"
            output += f"   File: {meta.file_path}\n\n"

        output += "Call load_skill() with the file path to read the full skill content."
        return output

    except Exception as e:
        return f"Error searching skills: {str(e)}"


@coder_agent.tool
async def load_skill(ctx: RunContext[None], file_path: str) -> str:
    """
    Load the full content of a skill file including templates, patterns, and best practices.
    Call this after find_skills() to get detailed instructions for code generation.

    Args:
        file_path: The file path returned by find_skills()
    """
    try:
        loader = _get_skill_loader()
        skill = loader.load(file_path)

        if not skill:
            return f"Could not load skill from: {file_path}"

        output = f"=== SKILL: {skill.meta.name} ===\n"
        output += f"Domain: {skill.meta.domain}\n"
        output += f"Description: {skill.meta.description}\n"
        output += f"Output types: {', '.join(skill.meta.output_types)}\n\n"
        output += "--- FULL INSTRUCTIONS ---\n\n"
        output += skill.body
        output += "\n\n=== END SKILL ==="

        return output

    except Exception as e:
        return f"Error loading skill: {str(e)}"


@coder_agent.tool
async def create_plan(ctx: RunContext[None], task: str, steps_json: str) -> str:
    """
    Register an execution plan for the coding task.
    Call this AFTER loading skills but BEFORE writing any files.

    Args:
        task: A one-line description of the overall task
        steps_json: JSON array of step objects, each with "step" (number), "action" (what to do), and "output" (expected file or result)
    """
    global _plan_steps

    try:
        steps = json.loads(steps_json)
        _plan_steps = steps

        output = f"Plan registered: {task}\n\n"
        output += f"Steps ({len(steps)}):\n"
        for step in steps:
            output += f"  {step.get('step', '?')}. {step.get('action', 'Unknown action')}\n"
            output += f"     Output: {step.get('output', 'N/A')}\n"

        output += "\nPlan is locked. Now execute each step by calling write_file()."
        return output

    except json.JSONDecodeError as e:
        return f"Invalid JSON in steps_json: {str(e)}. Please provide a valid JSON array."
    except Exception as e:
        return f"Error creating plan: {str(e)}"


@coder_agent.tool
async def write_file(ctx: RunContext[None], file_path: str, content: str, description: str = "") -> str:
    """
    Write a generated file to the project output directory.
    The file_path is relative to the project root (e.g., "src/models/fact_orders.qvs").

    Args:
        file_path: Relative path within the project (e.g., "src/models/fact_orders.qvs")
        content: The complete file content to write
        description: Brief description of what this file does
    """
    global _project_writer

    try:
        if _project_writer is None:
            return "Error: Project writer not initialized. This is an internal error."

        abs_path = _project_writer.write_file(file_path, content, description)
        file_count = _project_writer.get_file_count()

        return f"File written: {file_path} ({len(content)} chars)\nTotal files in project: {file_count}\nPath: {abs_path}"

    except ValueError as e:
        return f"Invalid file path: {str(e)}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@coder_agent.tool
async def write_summary(ctx: RunContext[None], project_name: str, summary: str, architecture_notes: str = "") -> str:
    """
    Finalize the project by creating README.md and manifest.json.
    Call this as the LAST step after all files have been written.

    Args:
        project_name: Human-readable project name
        summary: Overview of what was generated and why
        architecture_notes: Technical notes about the architecture and design decisions
    """
    global _project_writer

    try:
        if _project_writer is None:
            return "Error: Project writer not initialized."

        # Build README content
        readme = f"# {project_name}\n\n"
        readme += f"Generated by Assistant Brain OS Coding Agent\n"
        readme += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        readme += f"## Summary\n\n{summary}\n\n"

        if architecture_notes:
            readme += f"## Architecture\n\n{architecture_notes}\n\n"

        # List all generated files
        readme += "## Generated Files\n\n"
        for file_entry in _project_writer.manifest.files:
            path = file_entry.get('path', '')
            desc = file_entry.get('description', '')
            size = file_entry.get('size', 0)
            readme += f"- `{path}` - {desc} ({size} chars)\n"

        readme += f"\n## Plan\n\n"
        if _plan_steps:
            for step in _plan_steps:
                readme += f"{step.get('step', '?')}. {step.get('action', '')}\n"

        # Write README
        _project_writer.write_file("README.md", readme, "Project overview and documentation")

        # Finalize (writes manifest.json)
        manifest_path = _project_writer.finalize()

        file_count = _project_writer.get_file_count()
        project_dir = _project_writer.project_dir

        return (
            f"Project finalized!\n"
            f"Name: {project_name}\n"
            f"Files: {file_count}\n"
            f"Directory: {project_dir}\n"
            f"Manifest: {manifest_path}\n\n"
            f"The project is complete and ready to use."
        )

    except Exception as e:
        return f"Error finalizing project: {str(e)}"


@coder_agent.tool
async def search_knowledge(ctx: RunContext[None], query: str) -> str:
    """
    Search the existing knowledge base for context relevant to the coding task.
    Use this to find user preferences, past projects, or domain-specific information.

    Args:
        query: What to search for in the knowledge base
    """
    try:
        results = db.search_knowledge(query, limit=3)

        if not results['documents'][0]:
            return "Nothing relevant found in the knowledge base."

        output = "Found in knowledge base:\n\n"
        for i, doc in enumerate(results['documents'][0][:3], 1):
            preview = doc[:400] + "..." if len(doc) > 400 else doc
            output += f"{i}. {preview}\n\n"

        return output

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"


async def execute(payload) -> AgentResponse:
    """
    Main execution function for the coding agent.
    Generates a complete project based on the given task description.
    Accepts full payload dict or plain string.
    """
    global _project_writer, _plan_steps

    topic = payload.get("text", "") if isinstance(payload, dict) else payload
    print(f"🛠️ Coding Agent activated for: {topic}")

    # Reset state for this execution
    _plan_steps = []

    # Create project writer with unique ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_id = f"{timestamp}_{uuid.uuid4().hex[:8]}"
    _project_writer = ProjectWriter(project_id, task=topic)

    try:
        # Run the agent
        result = await coder_agent.run(
            f"Complete this coding task autonomously. Generate all necessary files.\n\nTask: {topic}"
        )
        output = result.output

        # Save a summary to the knowledge base
        try:
            from common.contracts import KnowledgeEntry
            summary_text = (
                f"# Coding Project: {topic}\n\n"
                f"Project ID: {project_id}\n"
                f"Output directory: {_project_writer.project_dir}\n"
                f"Files generated: {_project_writer.get_file_count()}\n\n"
                f"Agent output:\n{output[:500]}"
            )
            entry = KnowledgeEntry(
                text=summary_text,
                tags=["coding-project", "generated"],
                source="coder",
                metadata={
                    "project_id": project_id,
                    "task": topic,
                    "file_count": _project_writer.get_file_count(),
                    "saved_at": datetime.now().isoformat()
                }
            )
            db.add_knowledge(entry)
        except Exception as e:
            print(f"Warning: Could not save project summary to knowledge base: {e}")

        return AgentResponse(
            success=True,
            output=output,
            agent="coder"
        )

    except Exception as e:
        error_msg = f"Error in coding agent: {str(e)}"
        print(f"❌ {error_msg}")
        return AgentResponse(
            success=False,
            output=error_msg,
            agent="coder"
        )
    finally:
        # Clean up module-level state
        _project_writer = None
        _plan_steps = []
