"""Semantic version parsing and comparison utilities."""

import re
from dataclasses import dataclass

from .exceptions import InvalidVersionException


@dataclass
class SemanticVersion:
    """Represents a semantic version with major, minor, patch, pre-release, and build metadata."""

    major: int
    minor: int = 0
    patch: int = 0
    pre_release: str | None = None
    build_metadata: str | None = None

    def __str__(self) -> str:
        """String representation of the version."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            version += f"-{self.pre_release}"
        if self.build_metadata:
            version += f"+{self.build_metadata}"
        return version

    def __lt__(self, other: "SemanticVersion") -> bool:
        """Compare if this version is less than another."""
        # Compare major, minor, patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # If versions are equal, check pre-release
        # Version without pre-release is greater than with pre-release
        if self.pre_release is None and other.pre_release is not None:
            return False
        if self.pre_release is not None and other.pre_release is None:
            return True

        # Both have pre-release, compare them
        if self.pre_release and other.pre_release:
            return self._compare_pre_release(self.pre_release, other.pre_release)

        return False

    def __le__(self, other: "SemanticVersion") -> bool:
        """Compare if this version is less than or equal to another."""
        return self < other or self == other

    def __gt__(self, other: "SemanticVersion") -> bool:
        """Compare if this version is greater than another."""
        return not self <= other

    def __ge__(self, other: "SemanticVersion") -> bool:
        """Compare if this version is greater than or equal to another."""
        return not self < other

    def __eq__(self, other: object) -> bool:
        """Compare if this version equals another."""
        if not isinstance(other, SemanticVersion):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.pre_release == other.pre_release
        )

    @staticmethod
    def _compare_pre_release(pre1: str, pre2: str) -> bool:
        """Compare pre-release versions according to semver rules."""
        parts1 = pre1.split(".")
        parts2 = pre2.split(".")

        for p1, p2 in zip(parts1, parts2, strict=False):
            # Try to compare as integers first
            try:
                n1 = int(p1)
                n2 = int(p2)
                if n1 != n2:
                    return n1 < n2
            except ValueError:
                # Compare as strings if not integers
                if p1 != p2:
                    return p1 < p2

        # If all compared parts are equal, shorter is less
        return len(parts1) < len(parts2)


def parse_version(version_str: str) -> SemanticVersion:
    """Parse a version string into a SemanticVersion object.

    Supports various formats:
    - Standard semver: 1.2.3, 1.2.3-beta.1, 1.2.3+build.123
    - With 'v' prefix: v1.2.3
    - Two-part versions: 1.2
    - Snapshot/beta tags: 1.2.3-SNAPSHOT, 1.2.3-beta1

    Args:
        version_str: Version string to parse

    Returns:
        SemanticVersion object

    Raises:
        InvalidVersionException: If version string cannot be parsed
    """
    if not version_str:
        raise InvalidVersionException(version_str, "Version string is empty")

    # Remove 'v' prefix if present
    version_str = version_str.lstrip("vV")

    # Regex pattern for semantic versioning
    # Matches: major.minor.patch[-pre-release][+build]
    pattern = r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z\-\.]+))?(?:\+([0-9A-Za-z\-\.]+))?$"

    match = re.match(pattern, version_str)
    if not match:
        raise InvalidVersionException(version_str, "Invalid semantic version format")

    major, minor, patch, pre_release, build = match.groups()

    try:
        return SemanticVersion(
            major=int(major),
            minor=int(minor) if minor else 0,
            patch=int(patch) if patch else 0,
            pre_release=pre_release,
            build_metadata=build,
        )
    except ValueError as e:
        raise InvalidVersionException(version_str, f"Failed to parse version components: {e}")


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings.

    Args:
        version1: First version string
        version2: Second version string

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2

    Raises:
        InvalidVersionException: If either version string is invalid
    """
    try:
        v1 = parse_version(version1)
        v2 = parse_version(version2)

        if v1 < v2:
            return -1
        if v1 > v2:
            return 1
        return 0
    except InvalidVersionException:
        # If parsing fails, fall back to string comparison
        if version1 < version2:
            return -1
        if version1 > version2:
            return 1
        return 0


def is_newer_version(current: str, candidate: str) -> bool:
    """Check if candidate version is newer than current version.

    Args:
        current: Current version string
        candidate: Candidate version string to compare

    Returns:
        True if candidate is newer than current, False otherwise
    """
    try:
        return compare_versions(current, candidate) < 0
    except InvalidVersionException:
        return False


def is_compatible_version(version: str, requirement: str) -> bool:
    """Check if a version satisfies a requirement.

    Currently supports simple equality checks.
    Future: Support for version ranges (^1.2.3, ~1.2.3, >=1.0.0)

    Args:
        version: Version to check
        requirement: Required version or range

    Returns:
        True if version satisfies requirement, False otherwise
    """
    try:
        return compare_versions(version, requirement) == 0
    except InvalidVersionException:
        return version == requirement
