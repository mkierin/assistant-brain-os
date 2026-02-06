"""
Project Writer - Manages output directory creation and file writing
for the coding agent's generated projects.
"""

import os
import json
from datetime import datetime
from common.config import CODER_OUTPUT_DIR
from common.contracts import ProjectManifest


class ProjectWriter:
    """Manages writing generated files to a project output directory."""

    def __init__(self, project_id: str, task: str = ""):
        self.project_id = project_id
        self.project_dir = os.path.join(CODER_OUTPUT_DIR, project_id)
        self.manifest = ProjectManifest(project_id=project_id, task=task)

        # Create the project directory
        os.makedirs(self.project_dir, exist_ok=True)

    def write_file(self, relative_path: str, content: str, description: str = "") -> str:
        """
        Write a file to the project directory.

        Args:
            relative_path: Path relative to project root (e.g., "src/models/fact.qvs")
            content: File content
            description: Description for the manifest

        Returns:
            Absolute path to the written file
        """
        # Sanitize path (prevent directory traversal)
        relative_path = relative_path.lstrip("/").lstrip("\\")
        if ".." in relative_path:
            raise ValueError(f"Path traversal not allowed: {relative_path}")

        full_path = os.path.join(self.project_dir, relative_path)

        # Create parent directories
        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # Write the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Add to manifest
        self.manifest.files.append({
            "path": relative_path,
            "description": description,
            "size": len(content),
            "written_at": datetime.now().isoformat()
        })

        return full_path

    def finalize(self) -> str:
        """
        Write the manifest.json and mark project as complete.

        Returns:
            Path to the manifest file
        """
        self.manifest.completed_at = datetime.now().isoformat()

        manifest_path = os.path.join(self.project_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest.model_dump(), f, indent=2)

        return manifest_path

    def get_file_count(self) -> int:
        """Return number of files written so far."""
        return len(self.manifest.files)
