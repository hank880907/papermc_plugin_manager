"""
Unit tests for Modrinth API models.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from papermc_plugin_manager.connectors.modrinth_models import (
    ModrinthAPIConfig,
    Version,
    Project,
    SearchResponse,
    SearchHit,
    TeamMember,
    TeamMemberUser,
    VersionFile,
    VersionFileHash,
    License,
    ProjectType,
    VersionType,
    ProjectStatus,
)


# ============== Fixtures ==============

@pytest.fixture
def sample_version_data():
    """Sample version data from Modrinth API."""
    return {
        "id": "test_version_id",
        "project_id": "test_project_id",
        "author_id": "test_author_id",
        "featured": True,
        "name": "Test Version 1.0",
        "version_number": "1.0.0",
        "changelog": "Initial release",
        "changelog_url": None,
        "date_published": "2025-01-01T00:00:00Z",
        "downloads": 1000,
        "version_type": "release",
        "status": "approved",
        "requested_status": None,
        "files": [
            {
                "hashes": {
                    "sha512": "abc123",
                    "sha1": "def456"
                },
                "url": "https://cdn.modrinth.com/data/test/test.jar",
                "filename": "test-plugin-1.0.0.jar",
                "primary": True,
                "size": 1024000,
                "file_type": None
            }
        ],
        "dependencies": [],
        "game_versions": ["1.20.1", "1.20.2"],
        "loaders": ["paper", "spigot"]
    }


@pytest.fixture
def sample_project_data():
    """Sample project data from Modrinth API."""
    return {
        "id": "test_project_id",
        "slug": "test-plugin",
        "project_type": "plugin",
        "team": "team_id",
        "title": "Test Plugin",
        "description": "A test plugin",
        "body": "## Full description\nThis is a test plugin",
        "body_url": None,
        "published": "2025-01-01T00:00:00Z",
        "updated": "2025-01-02T00:00:00Z",
        "approved": "2025-01-01T00:00:00Z",
        "queued": None,
        "status": "approved",
        "requested_status": None,
        "moderator_message": None,
        "license": {
            "id": "MIT",
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        "client_side": "optional",
        "server_side": "required",
        "downloads": 50000,
        "followers": 1000,
        "categories": ["paper", "utility"],
        "additional_categories": [],
        "game_versions": ["1.20.1", "1.20.2"],
        "loaders": ["paper", "spigot"],
        "versions": ["version_id_1", "version_id_2"],
        "icon_url": "https://cdn.modrinth.com/icon.png",
        "gallery": [],
        "issues_url": "https://github.com/test/test/issues",
        "source_url": "https://github.com/test/test",
        "wiki_url": None,
        "discord_url": None,
        "donation_urls": [],
        "color": 0xFF5733,
        "thread_id": None,
        "monetization_status": None
    }


@pytest.fixture
def sample_search_data():
    """Sample search response data from Modrinth API."""
    return {
        "hits": [
            {
                "project_id": "search_result_1",
                "slug": "plugin-one",
                "project_type": "plugin",
                "title": "Plugin One",
                "description": "First plugin",
                "author": "TestAuthor",
                "categories": ["paper", "utility"],
                "display_categories": ["paper"],
                "versions": ["1.20.1"],
                "downloads": 10000,
                "follows": 500,
                "icon_url": "https://cdn.modrinth.com/icon1.png",
                "date_created": "2025-01-01T00:00:00Z",
                "date_modified": "2025-01-02T00:00:00Z",
                "latest_version": "version_1",
                "license": "MIT",
                "gallery": [],
                "featured_gallery": None,
                "color": None,
                "monetization_status": None,
                "client_side": "optional",
                "server_side": "required"
            },
            {
                "project_id": "search_result_2",
                "slug": "plugin-two",
                "project_type": "plugin",
                "title": "Plugin Two",
                "description": "Second plugin",
                "author": "TestAuthor2",
                "categories": ["paper", "combat"],
                "display_categories": ["paper"],
                "versions": ["1.20.1"],
                "downloads": 5000,
                "follows": 250,
                "icon_url": "https://cdn.modrinth.com/icon2.png",
                "date_created": "2025-01-01T00:00:00Z",
                "date_modified": "2025-01-02T00:00:00Z",
                "latest_version": "version_2",
                "license": "GPL-3.0",
                "gallery": [],
                "featured_gallery": None,
                "color": None,
                "monetization_status": None,
                "client_side": "optional",
                "server_side": "required"
            }
        ],
        "offset": 0,
        "limit": 10,
        "total_hits": 2
    }


@pytest.fixture
def sample_team_members_data():
    """Sample team members data from Modrinth API."""
    return [
        {
            "team_id": "team_id_1",
            "user": {
                "id": "user_1",
                "username": "owner_user",
                "name": "Owner User",
                "avatar_url": "https://cdn.modrinth.com/avatar1.png",
                "bio": "Project owner",
                "created": "2024-01-01T00:00:00Z",
                "role": "developer"
            },
            "role": "Owner",
            "permissions": None,
            "accepted": True,
            "payouts_split": None,
            "ordering": 0
        },
        {
            "team_id": "team_id_1",
            "user": {
                "id": "user_2",
                "username": "contributor",
                "name": "Contributor",
                "avatar_url": "https://cdn.modrinth.com/avatar2.png",
                "bio": "Contributor",
                "created": "2024-02-01T00:00:00Z",
                "role": "developer"
            },
            "role": "Member",
            "permissions": None,
            "accepted": True,
            "payouts_split": None,
            "ordering": 1
        }
    ]


# ============== ModrinthAPIConfig Tests ==============

class TestModrinthAPIConfig:
    """Tests for ModrinthAPIConfig class."""
    
    def test_set_user_agent(self):
        """Test setting custom User-Agent."""
        original_agent = ModrinthAPIConfig.HEADERS["User-Agent"]
        new_agent = "test-agent/1.0.0"
        
        ModrinthAPIConfig.set_user_agent(new_agent)
        assert ModrinthAPIConfig.HEADERS["User-Agent"] == new_agent
        
        # Reset to original
        ModrinthAPIConfig.set_user_agent(original_agent)
    
    @patch('papermc_plugin_manager.connectors.modrinth_models.requests.get')
    def test_api_get_success(self, mock_get):
        """Test successful API GET request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = ModrinthAPIConfig.api_get("/test")
        
        assert result == {"test": "data"}
        mock_get.assert_called_once()
        assert "/test" in mock_get.call_args[0][0]
    
    @patch('papermc_plugin_manager.connectors.modrinth_models.requests.get')
    def test_api_get_rate_limited(self, mock_get):
        """Test handling of rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"X-Ratelimit-Reset": "60"}
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Rate limited"):
            ModrinthAPIConfig.api_get("/test")
    
    @patch('papermc_plugin_manager.connectors.modrinth_models.requests.get')
    def test_api_get_with_params(self, mock_get):
        """Test API GET request with parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        params = {"query": "test", "limit": 5}
        ModrinthAPIConfig.api_get("/search", params=params)
        
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"] == params


# ============== Version Model Tests ==============

class TestVersion:
    """Tests for Version model."""
    
    def test_version_parsing(self, sample_version_data):
        """Test parsing version data into model."""
        version = Version(**sample_version_data)
        
        assert version.id == "test_version_id"
        assert version.project_id == "test_project_id"
        assert version.name == "Test Version 1.0"
        assert version.version_number == "1.0.0"
        assert version.version_type == VersionType.RELEASE
        assert len(version.files) == 1
        assert len(version.game_versions) == 2
    
    def test_primary_file_property(self, sample_version_data):
        """Test getting primary file."""
        version = Version(**sample_version_data)
        primary = version.primary_file
        
        assert primary is not None
        assert primary.primary is True
        assert primary.filename == "test-plugin-1.0.0.jar"
    
    def test_primary_file_fallback(self, sample_version_data):
        """Test primary file fallback when no file is marked primary."""
        sample_version_data["files"][0]["primary"] = False
        version = Version(**sample_version_data)
        
        # Should return first file even if not marked primary
        primary = version.primary_file
        assert primary is not None
        assert primary.filename == "test-plugin-1.0.0.jar"
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_get_version(self, mock_api_get, sample_version_data):
        """Test Version.get() class method."""
        mock_api_get.return_value = sample_version_data
        
        version = Version.get("test_version_id")
        
        assert version.id == "test_version_id"
        mock_api_get.assert_called_once_with("/version/test_version_id")
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_get_version_by_hash(self, mock_api_get, sample_version_data):
        """Test Version.get_by_hash() class method."""
        mock_api_get.return_value = sample_version_data
        
        version = Version.get_by_hash("def456", algorithm="sha1")
        
        assert version.id == "test_version_id"
        mock_api_get.assert_called_once_with(
            "/version_file/def456",
            params={"algorithm": "sha1"}
        )
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_list_for_project(self, mock_api_get, sample_version_data):
        """Test Version.list_for_project() class method."""
        mock_api_get.return_value = [sample_version_data, sample_version_data]
        
        versions = Version.list_for_project(
            "test_project",
            loaders=["paper"],
            game_versions=["1.20.1"],
            featured=True
        )
        
        assert len(versions) == 2
        assert all(isinstance(v, Version) for v in versions)
        
        # Check that parameters were properly formatted
        call_args = mock_api_get.call_args
        params = call_args[1]["params"]
        assert json.loads(params["loaders"]) == ["paper"]
        assert json.loads(params["game_versions"]) == ["1.20.1"]
        assert params["featured"] == "true"
    
    def test_version_with_listed_status(self, sample_version_data):
        """Test parsing version with 'listed' status (real API response)."""
        # Modrinth API sometimes returns 'listed' as a status
        sample_version_data["status"] = "listed"
        version = Version(**sample_version_data)
        
        assert version.status == ProjectStatus.LISTED
        assert version.id == "test_version_id"
    
    @patch('papermc_plugin_manager.connectors.modrinth_models.requests.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_primary_file(self, mock_file, mock_get, sample_version_data):
        """Test downloading primary file."""
        version = Version(**sample_version_data)
        
        # Mock the download response
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"test data"]
        mock_response.status_code = 200
        mock_get.return_value.__enter__.return_value = mock_response
        
        filepath = version.download_primary_file(dest_dir="/tmp/plugins")
        
        assert filepath == "/tmp/plugins/test-plugin-1.0.0.jar"
        mock_get.assert_called_once()
        mock_file.assert_called_once_with("/tmp/plugins/test-plugin-1.0.0.jar", "wb")
    
    def test_download_primary_file_no_files(self, sample_version_data):
        """Test error when no primary file exists."""
        sample_version_data["files"] = []
        version = Version(**sample_version_data)
        
        with pytest.raises(ValueError, match="No primary file found"):
            version.download_primary_file()


# ============== Project Model Tests ==============

class TestProject:
    """Tests for Project model."""
    
    def test_project_parsing(self, sample_project_data):
        """Test parsing project data into model."""
        project = Project(**sample_project_data)
        
        assert project.id == "test_project_id"
        assert project.slug == "test-plugin"
        assert project.title == "Test Plugin"
        assert project.project_type == ProjectType.PLUGIN
        assert project.downloads == 50000
        assert project.followers == 1000
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_get_project(self, mock_api_get, sample_project_data):
        """Test Project.get() class method."""
        mock_api_get.return_value = sample_project_data
        
        project = Project.get("test-plugin")
        
        assert project.slug == "test-plugin"
        mock_api_get.assert_called_once_with("/project/test-plugin")
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_get_multiple_projects(self, mock_api_get, sample_project_data):
        """Test Project.get_multiple() class method."""
        mock_api_get.return_value = [sample_project_data, sample_project_data]
        
        projects = Project.get_multiple(["project1", "project2"])
        
        assert len(projects) == 2
        assert all(isinstance(p, Project) for p in projects)
        
        # Check that IDs were properly formatted
        call_args = mock_api_get.call_args
        params = call_args[1]["params"]
        assert json.loads(params["ids"]) == ["project1", "project2"]
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_get_versions_instance_method(self, mock_api_get, sample_project_data, sample_version_data):
        """Test project.get_versions() instance method."""
        project = Project(**sample_project_data)
        mock_api_get.return_value = [sample_version_data]
        
        versions = project.get_versions(loaders=["paper"])
        
        assert len(versions) == 1
        assert isinstance(versions[0], Version)
        mock_api_get.assert_called_once()
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_get_team_members_instance_method(self, mock_api_get, sample_project_data, sample_team_members_data):
        """Test project.get_team_members() instance method."""
        project = Project(**sample_project_data)
        mock_api_get.return_value = sample_team_members_data
        
        members = project.get_team_members()
        
        assert len(members) == 2
        assert all(isinstance(m, TeamMember) for m in members)
        mock_api_get.assert_called_once_with(f"/project/{project.id}/members")


# ============== SearchResponse Model Tests ==============

class TestSearchResponse:
    """Tests for SearchResponse model."""
    
    def test_search_response_parsing(self, sample_search_data):
        """Test parsing search response data."""
        response = SearchResponse(**sample_search_data)
        
        assert len(response.hits) == 2
        assert response.offset == 0
        assert response.limit == 10
        assert response.total_hits == 2
        assert all(isinstance(hit, SearchHit) for hit in response.hits)
    
    def test_search_hit_parsing(self, sample_search_data):
        """Test parsing individual search hits."""
        hit_data = sample_search_data["hits"][0]
        hit = SearchHit(**hit_data)
        
        assert hit.project_id == "search_result_1"
        assert hit.title == "Plugin One"
        assert hit.author == "TestAuthor"
        assert hit.downloads == 10000
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_search_basic(self, mock_api_get, sample_search_data):
        """Test SearchResponse.search() class method."""
        mock_api_get.return_value = sample_search_data
        
        results = SearchResponse.search(
            query="test",
            facets=[["project_type:plugin"]],
            index="downloads",
            limit=5
        )
        
        assert len(results.hits) == 2
        assert results.total_hits == 2
        
        # Check parameters
        call_args = mock_api_get.call_args
        params = call_args[1]["params"]
        assert params["query"] == "test"
        assert params["index"] == "downloads"
        assert params["limit"] == 5
        assert json.loads(params["facets"]) == [["project_type:plugin"]]
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_search_plugins(self, mock_api_get, sample_search_data):
        """Test SearchResponse.search_plugins() convenience method."""
        mock_api_get.return_value = sample_search_data
        
        results = SearchResponse.search_plugins(
            query="worldedit",
            loader="paper",
            game_version="1.20.1",
            limit=10
        )
        
        assert len(results.hits) == 2
        
        # Check that proper facets were added
        call_args = mock_api_get.call_args
        params = call_args[1]["params"]
        facets = json.loads(params["facets"])
        assert ["project_type:plugin"] in facets
        assert ["categories:paper"] in facets
        assert ["versions:1.20.1"] in facets
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_search_limit_capping(self, mock_api_get, sample_search_data):
        """Test that search limit is capped at 100."""
        mock_api_get.return_value = sample_search_data
        
        SearchResponse.search(query="test", limit=150)
        
        call_args = mock_api_get.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 100  # Should be capped


# ============== TeamMember Model Tests ==============

class TestTeamMember:
    """Tests for TeamMember model."""
    
    def test_team_member_parsing(self, sample_team_members_data):
        """Test parsing team member data."""
        member_data = sample_team_members_data[0]
        member = TeamMember(**member_data)
        
        assert member.team_id == "team_id_1"
        assert member.user.username == "owner_user"
        assert member.role == "Owner"
        assert member.accepted is True
    
    def test_is_owner_property(self, sample_team_members_data):
        """Test is_owner property."""
        owner = TeamMember(**sample_team_members_data[0])
        contributor = TeamMember(**sample_team_members_data[1])
        
        assert owner.is_owner is True
        assert contributor.is_owner is False
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_list_for_project(self, mock_api_get, sample_team_members_data):
        """Test TeamMember.list_for_project() class method."""
        mock_api_get.return_value = sample_team_members_data
        
        members = TeamMember.list_for_project("test_project")
        
        assert len(members) == 2
        assert all(isinstance(m, TeamMember) for m in members)
        mock_api_get.assert_called_once_with("/project/test_project/members")


# ============== Integration Tests ==============

class TestIntegration:
    """Integration tests combining multiple models."""
    
    @patch.object(ModrinthAPIConfig, 'api_get')
    def test_full_workflow(self, mock_api_get, sample_search_data, sample_project_data, sample_version_data):
        """Test a complete workflow: search -> get project -> get versions."""
        
        # First call: search
        mock_api_get.return_value = sample_search_data
        search_results = SearchResponse.search_plugins("test")
        assert len(search_results.hits) > 0
        
        # Second call: get project details
        project_id = search_results.hits[0].project_id
        mock_api_get.return_value = sample_project_data
        project = Project.get(project_id)
        assert project.id is not None
        
        # Third call: get versions
        mock_api_get.return_value = [sample_version_data]
        versions = project.get_versions(loaders=["paper"])
        assert len(versions) > 0
        assert versions[0].project_id == sample_version_data["project_id"]
