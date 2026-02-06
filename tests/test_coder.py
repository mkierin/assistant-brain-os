"""
Tests for the Coding Agent - tools, project writer, and execution flow.

Run with: cd /root/assistant-brain-os && python -m pytest tests/test_coder.py -v
"""

import pytest
import os
import sys
import json
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.project_writer import ProjectWriter
from common.contracts import ProjectManifest, SkillMeta, Skill


# ============================================================
# ProjectWriter tests
# ============================================================
class TestProjectWriter:
    """Tests for the ProjectWriter that manages output files."""

    @pytest.fixture
    def temp_output_dir(self, monkeypatch):
        tmpdir = tempfile.mkdtemp()
        monkeypatch.setattr("common.project_writer.CODER_OUTPUT_DIR", tmpdir)
        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_creates_project_directory(self, temp_output_dir):
        """ProjectWriter should create the project directory on init."""
        writer = ProjectWriter("test_project_001", task="Test task")
        assert os.path.isdir(writer.project_dir)
        assert writer.project_dir.endswith("test_project_001")

    def test_write_file_creates_file(self, temp_output_dir):
        """write_file() should create the file with correct content."""
        writer = ProjectWriter("test_write", task="Test")
        path = writer.write_file("hello.txt", "Hello World!", "A greeting file")

        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "Hello World!"

    def test_write_file_creates_subdirectories(self, temp_output_dir):
        """write_file() should auto-create parent directories."""
        writer = ProjectWriter("test_subdirs", task="Test")
        path = writer.write_file("src/models/fact_orders.qvs", "LOAD * FROM orders;", "Fact table")

        assert os.path.exists(path)
        assert "src/models" in path

    def test_write_file_tracks_manifest(self, temp_output_dir):
        """Each written file should be tracked in the manifest."""
        writer = ProjectWriter("test_manifest", task="Test")
        writer.write_file("file1.txt", "content1", "First file")
        writer.write_file("file2.txt", "content2", "Second file")

        assert writer.get_file_count() == 2
        assert writer.manifest.files[0]["path"] == "file1.txt"
        assert writer.manifest.files[1]["path"] == "file2.txt"
        assert writer.manifest.files[0]["size"] == len("content1")

    def test_write_file_prevents_path_traversal(self, temp_output_dir):
        """write_file() should reject paths with '..'."""
        writer = ProjectWriter("test_traversal", task="Test")
        with pytest.raises(ValueError, match="Path traversal"):
            writer.write_file("../../../etc/passwd", "malicious", "")

    def test_write_file_strips_leading_slashes(self, temp_output_dir):
        """write_file() should strip leading slashes from paths."""
        writer = ProjectWriter("test_slash", task="Test")
        path = writer.write_file("/leading/slash.txt", "content", "Test")
        assert os.path.exists(path)
        assert "leading/slash.txt" in path

    def test_finalize_creates_manifest_json(self, temp_output_dir):
        """finalize() should write manifest.json with all file info."""
        writer = ProjectWriter("test_finalize", task="Build something")
        writer.write_file("code.py", "print('hi')", "Main script")
        manifest_path = writer.finalize()

        assert os.path.exists(manifest_path)
        with open(manifest_path) as f:
            data = json.load(f)

        assert data["project_id"] == "test_finalize"
        assert data["task"] == "Build something"
        assert len(data["files"]) == 1
        assert data["completed_at"] is not None

    def test_get_file_count(self, temp_output_dir):
        """get_file_count() should return accurate count."""
        writer = ProjectWriter("test_count", task="Test")
        assert writer.get_file_count() == 0
        writer.write_file("a.txt", "a", "")
        assert writer.get_file_count() == 1
        writer.write_file("b.txt", "b", "")
        assert writer.get_file_count() == 2


# ============================================================
# Coder agent module import tests
# ============================================================
class TestCoderAgentImport:
    """Tests that the coder agent module loads correctly."""

    def test_coder_module_imports(self):
        """agents/coder.py should import without errors."""
        import agents.coder as coder
        assert hasattr(coder, 'execute')
        assert hasattr(coder, 'coder_agent')
        assert callable(coder.execute)

    def test_coder_has_all_tools(self):
        """The coder agent should have all 6 tools registered."""
        import agents.coder as coder
        # Check the tool functions exist
        assert hasattr(coder, 'find_skills')
        assert hasattr(coder, 'load_skill')
        assert hasattr(coder, 'create_plan')
        assert hasattr(coder, 'write_file')
        assert hasattr(coder, 'write_summary')
        assert hasattr(coder, 'search_knowledge')

    def test_coder_execute_signature(self):
        """execute() should accept a topic string."""
        import inspect
        import agents.coder as coder
        sig = inspect.signature(coder.execute)
        params = list(sig.parameters.keys())
        assert "topic" in params


# ============================================================
# Coder agent tool unit tests (mocked)
# ============================================================
class TestCoderTools:
    """Unit tests for individual coder agent tools."""

    @pytest.fixture(autouse=True)
    def setup_project_writer(self, monkeypatch):
        """Set up a temporary project writer for tool tests."""
        self.tmpdir = tempfile.mkdtemp()
        monkeypatch.setattr("common.project_writer.CODER_OUTPUT_DIR", self.tmpdir)

        import agents.coder as coder
        coder._project_writer = ProjectWriter("test_tools", task="Tool test")
        coder._plan_steps = []
        yield
        coder._project_writer = None
        coder._plan_steps = []
        shutil.rmtree(self.tmpdir)

    @pytest.mark.asyncio
    async def test_find_skills_returns_results(self):
        """find_skills() should return matching skill metadata."""
        import agents.coder as coder
        result = await coder.find_skills(None, "qlik star schema")
        assert "Found" in result or "No matching" in result

    @pytest.mark.asyncio
    async def test_find_skills_no_match(self):
        """find_skills() with irrelevant query should handle gracefully."""
        import agents.coder as coder
        result = await coder.find_skills(None, "xyzzy_nonexistent_technology_abc123")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_load_skill_valid(self):
        """load_skill() should return full skill content for a valid path."""
        import agents.coder as coder
        loader = coder._get_skill_loader()
        results = loader.search("star schema", limit=1)
        if results:
            result = await coder.load_skill(None, results[0].file_path)
            assert "SKILL:" in result
            assert "FULL INSTRUCTIONS" in result

    @pytest.mark.asyncio
    async def test_load_skill_invalid_path(self):
        """load_skill() with invalid path should return error message."""
        import agents.coder as coder
        result = await coder.load_skill(None, "/nonexistent/skill.md")
        assert "Could not load" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_create_plan(self):
        """create_plan() should register execution steps."""
        import agents.coder as coder
        steps = json.dumps([
            {"step": 1, "action": "Create fact table", "output": "fact_orders.qvs"},
            {"step": 2, "action": "Create dimension", "output": "dim_customers.qvs"}
        ])
        result = await coder.create_plan(None, "Build data model", steps)
        assert "Plan registered" in result
        assert len(coder._plan_steps) == 2

    @pytest.mark.asyncio
    async def test_create_plan_invalid_json(self):
        """create_plan() with invalid JSON should return error."""
        import agents.coder as coder
        result = await coder.create_plan(None, "Bad plan", "not valid json")
        assert "Invalid JSON" in result

    @pytest.mark.asyncio
    async def test_write_file_tool(self):
        """write_file() tool should create file and track it."""
        import agents.coder as coder
        result = await coder.write_file(None, "test_output.qvs", "LOAD * FROM table;", "Test load script")
        assert "File written" in result
        assert "test_output.qvs" in result
        assert coder._project_writer.get_file_count() == 1

    @pytest.mark.asyncio
    async def test_write_file_path_traversal(self):
        """write_file() should reject path traversal attempts."""
        import agents.coder as coder
        result = await coder.write_file(None, "../../../etc/evil.txt", "bad", "")
        assert "Invalid file path" in result or "Path traversal" in result

    @pytest.mark.asyncio
    async def test_write_summary_tool(self):
        """write_summary() should create README and manifest."""
        import agents.coder as coder
        # Write a file first
        await coder.write_file(None, "code.qvs", "LOAD 1 as Num;", "Test code")

        result = await coder.write_summary(None, "Test Project", "A test project summary", "Star schema design")
        assert "Project finalized" in result
        assert "Test Project" in result

        # Verify README exists
        readme_path = os.path.join(coder._project_writer.project_dir, "README.md")
        assert os.path.exists(readme_path)

        # Verify manifest exists
        manifest_path = os.path.join(coder._project_writer.project_dir, "manifest.json")
        assert os.path.exists(manifest_path)


# ============================================================
# Integration: routing tests
# ============================================================
class TestCoderRouting:
    """Tests that coder-related messages get routed correctly."""

    def test_web_routing_create_data_model(self):
        """'create a data model' should route to coder in web backend."""
        # Read and check the web backend routing function
        backend_path = "/root/brain-web-interface/backend/main.py"
        with open(backend_path) as f:
            content = f.read()

        assert "coder" in content, "Web backend should reference coder agent"
        assert "data model" in content, "Web backend should route 'data model' to coder"

    def test_web_routing_generate(self):
        """'generate' keyword should be in coder routing."""
        backend_path = "/root/brain-web-interface/backend/main.py"
        with open(backend_path) as f:
            content = f.read()

        assert "generate" in content, "Web backend should route 'generate' to coder"

    def test_telegram_routing_has_coder(self):
        """main.py router prompt should include coder agent."""
        main_path = "/root/assistant-brain-os/main.py"
        with open(main_path) as f:
            content = f.read()

        assert "coder" in content, "main.py should include coder in routing"
        assert "code generation" in content or "code project" in content.lower() or "scaffold" in content, \
            "main.py should describe coder capabilities"

    def test_telegram_action_keywords_include_coder_terms(self):
        """main.py action_keywords should include coder-related terms."""
        main_path = "/root/assistant-brain-os/main.py"
        with open(main_path) as f:
            content = f.read()

        for keyword in ["create", "build", "generate", "scaffold"]:
            assert f'"{keyword}"' in content, f"Action keyword '{keyword}' should be in main.py"

    def test_telegram_natural_responses_include_coder(self):
        """main.py should have natural response messages for coder agent."""
        main_path = "/root/assistant-brain-os/main.py"
        with open(main_path) as f:
            content = f.read()

        assert '"coder"' in content, "main.py should have coder in natural_responses dict"

    def test_agents_command_includes_coder(self):
        """The /agents command text should mention the coder agent."""
        main_path = "/root/assistant-brain-os/main.py"
        with open(main_path) as f:
            content = f.read()

        assert "CODER" in content, "/agents command should list the coder agent"
        assert "find_skills" in content, "/agents should mention find_skills tool"


# ============================================================
# Contracts tests
# ============================================================
class TestCoderContracts:
    """Tests for new Pydantic models added for the coding agent."""

    def test_skill_meta_creation(self):
        """SkillMeta should be creatable with required fields."""
        meta = SkillMeta(name="test", domain="testing")
        assert meta.name == "test"
        assert meta.domain == "testing"
        assert meta.tags == []
        assert meta.keywords == []

    def test_skill_meta_full(self):
        """SkillMeta should accept all optional fields."""
        meta = SkillMeta(
            name="qlik-star-schema",
            domain="qlik-data-modeling",
            version="2.0",
            description="Star schema patterns",
            tags=["qlik", "data-modeling"],
            keywords=["fact table", "dimension"],
            output_types=["qvs"],
            author="Test",
            file_path="/path/to/skill.md"
        )
        assert meta.version == "2.0"
        assert len(meta.tags) == 2
        assert meta.output_types == ["qvs"]

    def test_skill_creation(self):
        """Skill should combine meta and body."""
        meta = SkillMeta(name="test", domain="testing")
        skill = Skill(meta=meta, body="# Test Skill\n\nBody content here.")
        assert skill.meta.name == "test"
        assert "Body content" in skill.body

    def test_project_manifest_creation(self):
        """ProjectManifest should have auto-generated timestamps."""
        manifest = ProjectManifest(project_id="proj_001", task="Build something")
        assert manifest.project_id == "proj_001"
        assert manifest.task == "Build something"
        assert manifest.created_at is not None
        assert manifest.completed_at is None
        assert manifest.files == []

    def test_project_manifest_with_files(self):
        """ProjectManifest should track file entries."""
        manifest = ProjectManifest(project_id="proj_002")
        manifest.files.append({
            "path": "src/main.py",
            "description": "Entry point",
            "size": 1234
        })
        assert len(manifest.files) == 1
        assert manifest.files[0]["path"] == "src/main.py"


# ============================================================
# Config tests
# ============================================================
class TestCoderConfig:
    """Tests for coding agent configuration constants."""

    def test_skills_dir_exists(self):
        """SKILLS_DIR config should be importable."""
        from common.config import SKILLS_DIR
        assert SKILLS_DIR is not None
        assert isinstance(SKILLS_DIR, str)

    def test_coder_output_dir_exists(self):
        """CODER_OUTPUT_DIR config should be importable."""
        from common.config import CODER_OUTPUT_DIR
        assert CODER_OUTPUT_DIR is not None
        assert isinstance(CODER_OUTPUT_DIR, str)

    def test_coder_model_exists(self):
        """CODER_MODEL config should be importable."""
        from common.config import CODER_MODEL
        assert CODER_MODEL is not None
        assert isinstance(CODER_MODEL, str)

    def test_skills_directory_on_disk(self):
        """The skills/ directory should exist with skill files."""
        from common.config import SKILLS_DIR
        assert os.path.isdir(SKILLS_DIR), f"Skills directory should exist: {SKILLS_DIR}"

        # Should have at least the Qlik skills
        md_files = []
        for root, dirs, files in os.walk(SKILLS_DIR):
            for f in files:
                if f.endswith(".md") and not f.startswith("_"):
                    md_files.append(os.path.join(root, f))

        assert len(md_files) >= 3, f"Should have at least 3 skill files, found {len(md_files)}"
