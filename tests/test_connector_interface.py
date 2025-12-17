"""Unit tests for connector_interface module."""

from datetime import datetime

import pytest
from semantic_version import Version

from papermc_plugin_manager.connector_interface import FileInfo, ProjectInfo


class TestProjectInfoGetLatestRelease:
    """Tests for ProjectInfo.get_latest_release() method."""

    def test_no_versions_returns_none(self):
        """Test that get_latest_release returns None when there are no versions."""
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={},
        )
        assert project.get_latest_release() is None

    def test_no_release_versions_returns_none(self):
        """Test that get_latest_release returns None when there are no release versions."""
        beta_version = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="1.0.0-beta",
            version_type="BETA",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        alpha_version = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="1.0.0-alpha",
            version_type="ALPHA",
            release_date=datetime(2025, 1, 2),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": beta_version, "v2": alpha_version},
        )
        assert project.get_latest_release() is None

    def test_single_release_version(self):
        """Test that get_latest_release returns the only release version."""
        release_version = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="1.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": release_version},
        )
        assert project.get_latest_release() == release_version

    def test_multiple_releases_semantic_versioning(self):
        """Test that get_latest_release returns the highest semantic version."""
        v1 = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="1.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        v2 = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="2.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 2),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        v1_5 = FileInfo(
            version_id="v3",
            project_id="test-project",
            version_name="1.5.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 3),
            game_versions=["1.21"],
            sha1="ghi789",
            url="https://example.com/v3.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": v1, "v2": v2, "v3": v1_5},
        )
        assert project.get_latest_release() == v2

    def test_unparseable_versions_use_date_fallback(self):
        """Test that unparseable version names fall back to date comparison."""
        older = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="release-2025-01-01",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        newer = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="release-2025-01-15",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 15),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": older, "v2": newer},
        )
        assert project.get_latest_release() == newer

    def test_mixed_parseable_and_unparseable_versions(self):
        """Test handling of mixed parseable and unparseable version names."""
        parseable = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="2.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        unparseable_older = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="custom-build-jan",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 5),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        unparseable_newer = FileInfo(
            version_id="v3",
            project_id="test-project",
            version_name="custom-build-feb",
            version_type="RELEASE",
            release_date=datetime(2025, 2, 1),
            game_versions=["1.21"],
            sha1="ghi789",
            url="https://example.com/v3.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": parseable, "v2": unparseable_older, "v3": unparseable_newer},
        )
        # Should return the newest by date when mixing parseable and unparseable
        result = project.get_latest_release()
        assert result == unparseable_newer

    def test_case_insensitive_version_type(self):
        """Test that version type matching is case-insensitive."""
        release_lower = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="1.0.0",
            version_type="release",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        release_upper = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="2.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 2),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        release_mixed = FileInfo(
            version_id="v3",
            project_id="test-project",
            version_name="3.0.0",
            version_type="Release",
            release_date=datetime(2025, 1, 3),
            game_versions=["1.21"],
            sha1="ghi789",
            url="https://example.com/v3.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": release_lower, "v2": release_upper, "v3": release_mixed},
        )
        assert project.get_latest_release() == release_mixed

    def test_semantic_version_with_prerelease_tag(self):
        """Test semantic versioning with prerelease tags in RELEASE versions."""
        v1 = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="1.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        v2_prerelease = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="2.0.0-rc.1",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 2),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": v1, "v2": v2_prerelease},
        )
        # 2.0.0-rc.1 should be considered greater than 1.0.0 in semantic versioning
        assert project.get_latest_release() == v2_prerelease

    def test_filters_non_release_versions(self):
        """Test that non-release versions are properly filtered out."""
        release = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="1.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        beta_newer = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="2.0.0-beta",
            version_type="BETA",
            release_date=datetime(2025, 1, 15),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": release, "v2": beta_newer},
        )
        # Should return the release version even though beta has a higher version number
        assert project.get_latest_release() == release

    def test_version_with_v_prefix(self):
        """Test that versions with 'v' prefix are handled correctly."""
        v1 = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="v1.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        v2 = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="v2.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 2),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": v1, "v2": v2},
        )
        assert project.get_latest_release() == v2

    def test_mixed_v_prefix_and_no_prefix(self):
        """Test that mixed versions with and without 'v' prefix are compared correctly."""
        with_prefix = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="v2.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        without_prefix = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="1.5.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 2),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": with_prefix, "v2": without_prefix},
        )
        # v2.0.0 should be greater than 1.5.0
        assert project.get_latest_release() == with_prefix

    def test_uppercase_v_prefix(self):
        """Test that uppercase 'V' prefix is also handled."""
        v1 = FileInfo(
            version_id="v1",
            project_id="test-project",
            version_name="V1.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 1),
            game_versions=["1.21"],
            sha1="abc123",
            url="https://example.com/v1.jar",
        )
        v2 = FileInfo(
            version_id="v2",
            project_id="test-project",
            version_name="V2.0.0",
            version_type="RELEASE",
            release_date=datetime(2025, 1, 2),
            game_versions=["1.21"],
            sha1="def456",
            url="https://example.com/v2.jar",
        )
        project = ProjectInfo(
            source="test",
            project_id="test-project",
            name="Test Project",
            author="Test Author",
            description="Test Description",
            downloads=0,
            versions={"v1": v1, "v2": v2},
        )
        assert project.get_latest_release() == v2
