"""Response personality layer. Transforms robotic agent outputs into natural conversation.

This is purely deterministic - no LLM calls. All decision-making already happened in the agents.
We're only softening delivery here.
"""
import re
import random


def format_for_human(agent_name: str, raw_output: str, source: str = "web") -> str:
    """Post-process agent output for natural, conversational delivery."""
    if not raw_output:
        return raw_output

    formatter = _FORMATTERS.get(agent_name)
    if formatter:
        return formatter(raw_output, source)
    return raw_output


def _format_archivist(output: str, source: str) -> str:
    """Soften archivist search/save outputs."""
    # Save confirmations
    if output.startswith("Saved!"):
        tags_match = re.search(r'Tagged as:\s*(.+)', output)
        if tags_match:
            tags = tags_match.group(1).strip()
            responses = [
                f"Got it, saved to your brain! {tags} — you can search for it anytime.",
                f"Done! Saved and tagged with {tags} so you'll find it later.",
                f"Noted! I've filed that away with {tags}.",
            ]
            return random.choice(responses)
        return "Got it, saved to your brain!"

    # Search results - soften the header
    found_match = re.match(r"Found (\d+) results? about '(.+?)':", output)
    if found_match:
        count = found_match.group(1)
        topic = found_match.group(2)
        rest = output[found_match.end():]
        if count == "1":
            header = f"Here's what I have on {topic}:"
        else:
            headers = [
                f"Here's what I found about {topic}:",
                f"I've got {count} things about {topic}:",
                f"Found some stuff on {topic}:",
            ]
            header = random.choice(headers)
        return header + rest

    # No results
    if "don't have anything saved about" in output:
        topic_match = re.search(r"about '(.+?)'", output)
        topic = topic_match.group(1) if topic_match else "that"
        responses = [
            f"Nothing saved about {topic} yet. Want me to look it up on the web instead?",
            f"I don't have anything on {topic} in your brain yet. Try saving some notes about it!",
            f"Hmm, nothing on {topic}. Would you like me to research it?",
        ]
        return random.choice(responses)

    return output


def _format_content_saver(output: str, source: str) -> str:
    """Merge content saver's multi-line output into natural sentences."""
    if "Saved" in output and len(output.split('\n')) > 2:
        lines = output.strip().split('\n')
        title = ""
        tags = ""
        connected = ""
        for line in lines:
            line = line.strip()
            if line.startswith("Saved") or line.startswith("\u2705"):
                title = re.sub(r'^(Saved!?|\u2705\s*Saved:?)\s*', '', line).strip()
            elif "tag" in line.lower() or line.startswith("#"):
                tags = line.strip()
            elif "connect" in line.lower() or "related" in line.lower():
                connected = line.strip()

        parts = []
        if title:
            parts.append(f'Saved "{title}" to your brain')
        else:
            parts.append("Saved to your brain")
        if tags:
            parts.append(f"tagged with {tags}")
        if connected:
            parts.append(connected.lower())

        return ". ".join(parts) + "." if parts else output

    return output


def _format_researcher(output: str, source: str) -> str:
    """Researcher already uses LLM synthesis. Just clean up edge cases."""
    output = re.sub(r'\n{3,}', '\n\n', output)
    return output


def _format_task_manager(output: str, source: str) -> str:
    """Task manager is already pretty natural. Minor touches."""
    return output


def _format_journal(output: str, source: str) -> str:
    """Journal responses - keep them warm."""
    if output.startswith("Journal entry saved"):
        return output.replace("Journal entry saved", "Journaled") + " \u270d\ufe0f"
    return output


_FORMATTERS = {
    "archivist": _format_archivist,
    "content_saver": _format_content_saver,
    "researcher": _format_researcher,
    "task_manager": _format_task_manager,
    "journal": _format_journal,
}
