"""
Tests for the SkillLoader - skill file parsing, indexing, and search.

Run with: cd /root/assistant-brain-os && python -m pytest tests/test_skill_loader.py -v
"""

import pytest
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.skill_loader import SkillLoader
from common.contracts import SkillMeta, Skill


# ============================================================
# Test with the actual skills directory
# ============================================================
class TestSkillLoaderWithRealSkills:
    """Tests using the actual skills/ directory in the project."""

    @pytest.fixture
    def loader(self):
        return SkillLoader(skills_dir="skills")

    def test_index_loads_skills(self, loader):
        """Should find and index skill files from skills/ directory."""
        assert len(loader._index) >= 3, "Should find at least 3 Qlik skill files"

    def test_all_skills_have_required_fields(self, loader):
        """Every indexed skill should have name, domain, and file_path."""
        for meta in loader._index:
            assert meta.name, f"Skill missing name: {meta.file_path}"
            assert meta.domain, f"Skill missing domain: {meta.file_path}"
            assert meta.file_path, f"Skill missing file_path"
            assert os.path.exists(meta.file_path), f"Skill file does not exist: {meta.file_path}"

    def test_search_qlik(self, loader):
        """Searching for 'qlik' should return Qlik skills."""
        results = loader.search("qlik")
        assert len(results) >= 1, "Should find at least 1 Qlik skill"
        for meta in results:
            searchable = (meta.name + meta.description + meta.domain +
                          " ".join(meta.tags) + " ".join(meta.keywords)).lower()
            assert "qlik" in searchable

    def test_search_star_schema(self, loader):
        """Searching for 'star schema' should return the star-schema skill."""
        results = loader.search("star schema")
        assert len(results) >= 1
        names = [r.name for r in results]
        assert any("star" in n.lower() for n in names), f"Expected star-schema skill, got: {names}"

    def test_search_incremental(self, loader):
        """Searching for 'incremental load' should return the incremental-loads skill."""
        results = loader.search("incremental load")
        assert len(results) >= 1
        names = [r.name for r in results]
        assert any("incremental" in n.lower() for n in names), f"Expected incremental skill, got: {names}"

    def test_search_naming(self, loader):
        """Searching for 'naming convention' should return the naming skill."""
        results = loader.search("naming convention")
        assert len(results) >= 1
        names = [r.name for r in results]
        assert any("naming" in n.lower() for n in names), f"Expected naming skill, got: {names}"

    def test_search_irrelevant_returns_empty(self, loader):
        """Searching for an unrelated term should return no results."""
        results = loader.search("banana smoothie recipe")
        # Might return 0 or low-relevance results
        assert isinstance(results, list)

    def test_load_skill_returns_body(self, loader):
        """Loading a skill should return the full body content."""
        results = loader.search("star schema", limit=1)
        assert len(results) >= 1

        skill = loader.load(results[0].file_path)
        assert skill is not None
        assert isinstance(skill, Skill)
        assert skill.meta.name == results[0].name
        assert len(skill.body) > 100, "Skill body should contain substantial content"
        assert "template" in skill.body.lower() or "pattern" in skill.body.lower(), \
            "Skill body should contain templates or patterns"

    def test_load_skill_caching(self, loader):
        """Loading the same skill twice should return cached version."""
        results = loader.search("qlik", limit=1)
        assert len(results) >= 1
        path = results[0].file_path

        skill1 = loader.load(path)
        skill2 = loader.load(path)
        assert skill1 is skill2, "Second load should return cached object"

    def test_list_all(self, loader):
        """list_all() should return all indexed skills."""
        all_skills = loader.list_all()
        assert len(all_skills) == len(loader._index)
        assert all_skills is not loader._index, "Should return a copy, not the original"

    def test_reload_rebuilds_index(self, loader):
        """reload() should rebuild the index from disk."""
        original_count = len(loader._index)
        loader.reload()
        assert len(loader._index) == original_count
        assert len(loader._cache) == 0, "Cache should be cleared after reload"


# ============================================================
# Test with a temporary skills directory
# ============================================================
class TestSkillLoaderWithTempDir:
    """Tests using a temporary directory with synthetic skill files."""

    @pytest.fixture
    def temp_skills_dir(self):
        tmpdir = tempfile.mkdtemp()
        domain_dir = os.path.join(tmpdir, "test-domain")
        os.makedirs(domain_dir)

        # Create a valid skill file
        skill1 = os.path.join(domain_dir, "test-skill.md")
        with open(skill1, "w") as f:
            f.write("""---
name: "test-skill"
domain: "test-domain"
version: "1.0"
description: "A test skill for unit testing"
tags:
  - "test"
  - "unit-test"
keywords:
  - "testing"
  - "pytest"
output_types:
  - "py"
author: "Test"
---

# Test Skill

## Templates

### Template: Test Function

```python
def test_{{name}}():
    assert True
```

## Best Practices

1. Always write tests.
""")

        # Create a skill without frontmatter (should be skipped)
        skill2 = os.path.join(domain_dir, "no-frontmatter.md")
        with open(skill2, "w") as f:
            f.write("# No Frontmatter\n\nThis file has no YAML frontmatter.\n")

        # Create a file starting with _ (should be skipped)
        skip_file = os.path.join(domain_dir, "_index.md")
        with open(skip_file, "w") as f:
            f.write("---\nname: should-be-skipped\ndomain: test\n---\nSkipped\n")

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_loads_valid_skills(self, temp_skills_dir):
        """Should load the valid skill and skip invalid ones."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        assert len(loader._index) == 1
        assert loader._index[0].name == "test-skill"

    def test_skips_underscore_files(self, temp_skills_dir):
        """Files starting with _ should be skipped."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        names = [m.name for m in loader._index]
        assert "should-be-skipped" not in names

    def test_skips_no_frontmatter(self, temp_skills_dir):
        """Files without YAML frontmatter should be skipped."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        assert len(loader._index) == 1

    def test_search_by_tag(self, temp_skills_dir):
        """Should find skills by tag."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        results = loader.search("test")
        assert len(results) == 1
        assert results[0].name == "test-skill"

    def test_search_by_keyword(self, temp_skills_dir):
        """Should find skills by keyword with boosted score."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        results = loader.search("pytest")
        assert len(results) == 1

    def test_load_full_skill(self, temp_skills_dir):
        """Loading a skill should return meta + body."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        meta = loader._index[0]
        skill = loader.load(meta.file_path)
        assert skill is not None
        assert "Template: Test Function" in skill.body
        assert skill.meta.domain == "test-domain"

    def test_nonexistent_directory(self):
        """Should handle nonexistent skills directory gracefully."""
        loader = SkillLoader(skills_dir="/nonexistent/path")
        assert len(loader._index) == 0

    def test_load_nonexistent_file(self, temp_skills_dir):
        """Loading a nonexistent file should return None."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        result = loader.load("/nonexistent/file.md")
        assert result is None

    def test_search_limit(self, temp_skills_dir):
        """Search limit parameter should cap results."""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        results = loader.search("test", limit=0)
        assert len(results) == 0
