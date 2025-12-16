"""Unit tests for version_utils module."""

import pytest
from papermc_plugin_manager.version_utils import (
    SemanticVersion,
    parse_version,
    compare_versions,
    is_newer_version,
    is_compatible_version,
)
from papermc_plugin_manager.exceptions import InvalidVersionException


class TestSemanticVersion:
    """Test SemanticVersion class."""
    
    def test_string_representation(self):
        """Test string representation of versions."""
        v = SemanticVersion(1, 2, 3)
        assert str(v) == "1.2.3"
        
        v_pre = SemanticVersion(1, 2, 3, pre_release="beta.1")
        assert str(v_pre) == "1.2.3-beta.1"
        
        v_build = SemanticVersion(1, 2, 3, build_metadata="build.123")
        assert str(v_build) == "1.2.3+build.123"
    
    def test_version_comparison(self):
        """Test version comparison operators."""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)
        v3 = SemanticVersion(1, 1, 0)
        v4 = SemanticVersion(1, 0, 1)
        
        assert v1 < v2
        assert v1 < v3
        assert v1 < v4
        assert v2 > v1
        assert v3 > v1
        assert v4 > v1
        assert v1 == SemanticVersion(1, 0, 0)
    
    def test_pre_release_comparison(self):
        """Test pre-release version comparison."""
        v_release = SemanticVersion(1, 0, 0)
        v_beta = SemanticVersion(1, 0, 0, pre_release="beta")
        v_alpha = SemanticVersion(1, 0, 0, pre_release="alpha")
        
        # Release is greater than pre-release
        assert v_beta < v_release
        assert v_alpha < v_release
        
        # Alpha-beta comparison (alphabetical)
        assert v_alpha < v_beta


class TestParseVersion:
    """Test version parsing."""
    
    def test_parse_standard_semver(self):
        """Test parsing standard semantic versions."""
        v = parse_version("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release is None
    
    def test_parse_with_v_prefix(self):
        """Test parsing versions with 'v' prefix."""
        v = parse_version("v1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
    
    def test_parse_two_part_version(self):
        """Test parsing two-part versions."""
        v = parse_version("1.2")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 0
    
    def test_parse_with_pre_release(self):
        """Test parsing versions with pre-release tags."""
        v = parse_version("1.2.3-beta.1")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release == "beta.1"
    
    def test_parse_with_build_metadata(self):
        """Test parsing versions with build metadata."""
        v = parse_version("1.2.3+build.123")
        assert v.major == 1
        assert v.build_metadata == "build.123"
    
    def test_parse_snapshot(self):
        """Test parsing SNAPSHOT versions."""
        v = parse_version("1.2.3-SNAPSHOT")
        assert v.pre_release == "SNAPSHOT"
    
    def test_parse_invalid_version(self):
        """Test parsing invalid version strings."""
        with pytest.raises(InvalidVersionException):
            parse_version("")
        
        with pytest.raises(InvalidVersionException):
            parse_version("not-a-version")
        
        with pytest.raises(InvalidVersionException):
            parse_version("1.2.3.4.5")


class TestCompareVersions:
    """Test version comparison functions."""
    
    def test_compare_equal_versions(self):
        """Test comparing equal versions."""
        assert compare_versions("1.2.3", "1.2.3") == 0
        assert compare_versions("v1.2.3", "1.2.3") == 0
    
    def test_compare_different_versions(self):
        """Test comparing different versions."""
        assert compare_versions("1.0.0", "2.0.0") < 0
        assert compare_versions("2.0.0", "1.0.0") > 0
        assert compare_versions("1.0.0", "1.1.0") < 0
        assert compare_versions("1.1.0", "1.0.1") > 0
    
    def test_is_newer_version(self):
        """Test is_newer_version function."""
        assert is_newer_version("1.0.0", "1.1.0") is True
        assert is_newer_version("1.1.0", "1.0.0") is False
        assert is_newer_version("1.0.0", "1.0.0") is False
    
    def test_is_compatible_version(self):
        """Test is_compatible_version function."""
        assert is_compatible_version("1.2.3", "1.2.3") is True
        assert is_compatible_version("1.2.3", "1.2.4") is False


class TestRealWorldVersions:
    """Test with real-world plugin version strings."""
    
    def test_minecraft_versions(self):
        """Test Minecraft version comparison."""
        assert compare_versions("1.20.1", "1.21.1") < 0
        assert compare_versions("1.21.1", "1.20.1") > 0
        assert compare_versions("1.20", "1.20.1") < 0
    
    def test_plugin_versions(self):
        """Test typical plugin version comparison."""
        assert is_newer_version("5.0.0", "5.1.0") is True
        assert is_newer_version("5.1.0", "5.1.1") is True
        assert is_newer_version("4.9.9", "5.0.0") is True
