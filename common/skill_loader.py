"""
Skill Loader - Parses and searches skill markdown files with YAML frontmatter.

Skills are stored as .md files in the skills/ directory (configurable via SKILLS_DIR).
Each file has YAML frontmatter with metadata and a markdown body with instructions,
templates, best practices, and code patterns.
"""

import os
import re
import yaml
from typing import List, Optional, Dict
from pathlib import Path
from common.config import SKILLS_DIR
from common.contracts import SkillMeta, Skill


class SkillLoader:
    """Loads and searches skill files from the skills directory."""

    def __init__(self, skills_dir: str = None):
        self.skills_dir = skills_dir or SKILLS_DIR
        self._cache: Dict[str, Skill] = {}
        self._index: List[SkillMeta] = []
        self._build_index()

    def _build_index(self):
        """Scan skills directory and build metadata index."""
        self._index = []
        skills_path = Path(self.skills_dir)

        if not skills_path.exists():
            print(f"Skills directory not found: {self.skills_dir}")
            return

        for md_file in skills_path.rglob("*.md"):
            # Skip files that start with _ (like _index.md)
            if md_file.name.startswith("_"):
                continue
            try:
                meta = self._parse_frontmatter(str(md_file))
                if meta:
                    meta.file_path = str(md_file)
                    self._index.append(meta)
            except Exception as e:
                print(f"Error parsing skill {md_file}: {e}")

        print(f"Loaded {len(self._index)} skill files from {self.skills_dir}")

    def _parse_frontmatter(self, file_path: str) -> Optional[SkillMeta]:
        """Parse YAML frontmatter from a markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match YAML frontmatter between --- delimiters
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return None

        yaml_str = match.group(1)
        data = yaml.safe_load(yaml_str)

        if not data or not isinstance(data, dict):
            return None

        return SkillMeta(**data)

    def search(self, query: str, limit: int = 5) -> List[SkillMeta]:
        """
        Search skills by matching query against name, description,
        tags, keywords, and domain.

        Returns skills sorted by relevance score (highest first).
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for meta in self._index:
            score = 0.0
            searchable = (
                meta.name + " " +
                meta.description + " " +
                meta.domain + " " +
                " ".join(meta.tags) + " " +
                " ".join(meta.keywords)
            ).lower()

            for word in query_words:
                if word in searchable:
                    score += 1
                # Boost for keyword match
                if word in [k.lower() for k in meta.keywords]:
                    score += 2
                # Boost for tag match
                if word in [t.lower() for t in meta.tags]:
                    score += 1.5
                # Boost for domain match
                if word in meta.domain.lower():
                    score += 1.5

            if score > 0:
                scored.append((score, meta))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [meta for _, meta in scored[:limit]]

    def load(self, file_path: str) -> Optional[Skill]:
        """Load the full skill content from a file."""
        if file_path in self._cache:
            return self._cache[file_path]

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split frontmatter and body
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
            if not match:
                return None

            yaml_str = match.group(1)
            body = match.group(2)
            data = yaml.safe_load(yaml_str)

            meta = SkillMeta(**data, file_path=file_path)
            skill = Skill(meta=meta, body=body)

            self._cache[file_path] = skill
            return skill

        except Exception as e:
            print(f"Error loading skill {file_path}: {e}")
            return None

    def list_all(self) -> List[SkillMeta]:
        """Return all indexed skill metadata."""
        return self._index.copy()

    def reload(self):
        """Reload the skill index (e.g., after adding new skill files)."""
        self._cache = {}
        self._build_index()
