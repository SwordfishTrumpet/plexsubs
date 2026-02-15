"""Library discovery and path validation functionality."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from plexsubs.plex.client import LibrarySection, PlexClient
from plexsubs.utils.constants import COMMON_MEDIA_MOUNTS
from plexsubs.utils.env_utils import is_running_in_docker
from plexsubs.utils.logging_config import get_logger
from plexsubs.utils.path_utils import apply_path_mappings, check_file_permissions
from plexsubs.utils.xml_utils import MediaPartNavigator

logger = get_logger(__name__)


@dataclass
class PathTestResult:
    """Result of testing a single path mapping."""

    plex_path: str
    mapped_path: str
    exists: bool
    readable: bool
    writable: bool
    is_file: bool
    is_directory: bool
    error: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete path validation report."""

    valid: bool
    tests: list[PathTestResult]
    summary: dict[str, int] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class PathMappingSuggestion:
    """Suggested path mapping based on analysis."""

    plex_prefix: str
    suggested_local_prefix: str
    confidence: str  # 'high', 'medium', 'low'
    reason: str


class PathDiscovery:
    """Discovery and validation of Plex library paths."""

    def __init__(self, plex_client: PlexClient, path_mappings: dict[str, str]):
        self.plex_client = plex_client
        self.path_mappings = path_mappings

    def discover_libraries(self) -> list[LibrarySection]:
        """Get all Plex libraries with their configured paths.

        Returns:
            List of LibrarySection objects containing library metadata and paths.
        """
        logger.info("Discovering Plex libraries")
        return self.plex_client.get_library_sections()

    def validate_path_mappings(self, test_paths: Optional[list[str]] = None) -> ValidationReport:
        """Validate current path mappings by testing file accessibility.

        Args:
            test_paths: Optional list of specific Plex paths to test.
                       If None, will try to find sample files from libraries.

        Returns:
            ValidationReport with detailed test results and suggestions.
        """
        logger.info("Validating path mappings")
        tests = []
        suggestions = []

        # If no test paths provided, try to get sample from libraries
        if not test_paths:
            test_paths = self._get_sample_paths_from_libraries()

        if not test_paths:
            logger.warning("No test paths available for validation")
            suggestions.append(
                "No media files found in Plex libraries to test. "
                "Add some media to your libraries first."
            )
            return ValidationReport(
                valid=False,
                tests=[],
                summary={"total": 0, "passed": 0, "failed": 0},
                suggestions=suggestions,
            )

        # Test each path
        for plex_path in test_paths:
            result = self._test_single_path(plex_path)
            tests.append(result)

        # Generate summary
        passed = sum(1 for t in tests if t.exists and t.readable)
        failed = len(tests) - passed

        summary = {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "accessible": sum(1 for t in tests if t.exists),
            "readable": sum(1 for t in tests if t.readable),
            "writable": sum(1 for t in tests if t.writable),
        }

        # Generate suggestions based on results
        suggestions = self._generate_suggestions(tests)

        valid = failed == 0 and passed > 0

        return ValidationReport(
            valid=valid,
            tests=tests,
            summary=summary,
            suggestions=suggestions,
        )

    def _test_single_path(self, plex_path: str) -> PathTestResult:
        """Test a single Plex path with current mappings."""
        mapped_path = apply_path_mappings(plex_path, self.path_mappings)

        try:
            perms = check_file_permissions(mapped_path)

            error = None
            if not perms["exists"]:
                error = f"Path does not exist: {mapped_path}"

            return PathTestResult(
                plex_path=plex_path,
                mapped_path=mapped_path,
                exists=perms["exists"],
                readable=perms["readable"],
                writable=perms["writable"],
                is_file=perms.get("is_file", False),
                is_directory=perms.get("is_directory", False),
                error=error,
            )

        except Exception as e:
            return PathTestResult(
                plex_path=plex_path,
                mapped_path=mapped_path,
                exists=False,
                readable=False,
                writable=False,
                is_file=False,
                is_directory=False,
                error=f"Error testing path: {e}",
            )

    def _get_sample_paths_from_libraries(self) -> list[str]:
        """Try to get sample media file paths from Plex libraries."""
        sample_paths = []

        try:
            libraries = self.plex_client.get_library_sections()

            for library in libraries:
                # Only check movie and show libraries
                if library.type not in ("movie", "show"):
                    continue

                # Get first item from library to test
                try:
                    items = self._get_library_items(library.key)
                    if items:
                        # Take first few items as samples
                        sample_paths.extend(items[:3])
                except Exception as e:
                    logger.debug(f"Could not get items from library {library.title}: {e}")

        except Exception as e:
            logger.warning(f"Could not get sample paths from libraries: {e}")

        return sample_paths

    def _get_library_items(self, library_key: str) -> list[str]:
        """Get media file paths from a library using the fluent navigator."""
        try:
            response = self.plex_client.get(f"/library/sections/{library_key}/all")
            root = ET.fromstring(response.text)
            paths = []

            # Find Video elements (movies or episodes) and extract paths
            for video in root.findall(".//Video"):
                navigator = MediaPartNavigator(video)
                file_path = navigator.get_file_path()
                if file_path:
                    paths.append(file_path)

            return paths

        except Exception as e:
            logger.debug(f"Error getting library items: {e}")
            return []

    def _generate_suggestions(self, tests: list[PathTestResult]) -> list[str]:
        """Generate helpful suggestions based on test results."""
        suggestions = []

        # Check for common issues
        not_found = [t for t in tests if not t.exists]
        not_readable = [t for t in tests if t.exists and not t.readable]
        not_writable = [t for t in tests if t.exists and not t.writable]

        if not tests:
            suggestions.append("No test paths available. Ensure Plex has media in its libraries.")
            return suggestions

        if not_found:
            plex_prefixes = set()
            for test in not_found:
                # Extract prefix from Plex path (e.g., /media from /media/movies/...)
                parts = test.plex_path.strip("/").split("/")
                if parts:
                    plex_prefixes.add(f"/{parts[0]}")

            if plex_prefixes:
                prefixes_str = ", ".join(plex_prefixes)
                suggestions.append(
                    f"Mapped paths not found. Plex uses these prefixes: {prefixes_str}. "
                    f"Check your PLEX_PATH_MAPPINGS setting."
                )

            # Check if we're in Docker
            if is_running_in_docker():
                suggestions.append(
                    "Running in Docker container. Ensure your media volume is mounted correctly "
                    "and the container path matches your PLEX_PATH_MAPPINGS."
                )

        if not_readable:
            suggestions.append(
                "Some media files are not readable. Check file permissions and ensure "
                "the plexsubs process has read access to your media."
            )

        if not_writable:
            suggestions.append(
                "Some media directories are not writable. Subtitle downloads will fail. "
                "Ensure plexsubs has write permission to your media directories."
            )

        # If all tests passed
        if all(t.exists and t.readable for t in tests):
            suggestions.append("All path mappings are working correctly!")

            if all(t.writable for t in tests):
                suggestions.append(
                    "All media directories are writable. Subtitle downloads should work."
                )
            else:
                suggestions.append(
                    "Some directories are not writable. You may need to fix permissions "
                    "for subtitle downloads to work."
                )

        return suggestions

    def suggest_path_mappings(self) -> list[PathMappingSuggestion]:
        """Analyze Plex library paths and suggest appropriate local mappings.

        Returns:
            List of PathMappingSuggestion objects with confidence ratings.
        """
        logger.info("Analyzing library paths to suggest mappings")
        suggestions = []

        try:
            libraries = self.plex_client.get_library_sections()

            # Collect unique path prefixes from Plex
            plex_prefixes = set()
            for library in libraries:
                for location in library.locations:
                    path = location.path
                    # Extract root prefix (e.g., /media, M:\\Media, etc.)
                    if path.startswith("/"):
                        # Unix path
                        parts = path.strip("/").split("/")
                        if parts:
                            plex_prefixes.add(f"/{parts[0]}")
                    elif ":" in path:
                        # Windows path (e.g., M:\Media)
                        drive = path.split(":")[0]
                        plex_prefixes.add(f"{drive}:")

            # Analyze current environment
            in_docker = is_running_in_docker()

            for plex_prefix in plex_prefixes:
                suggestion = self._generate_mapping_suggestion(plex_prefix, in_docker)
                if suggestion:
                    suggestions.append(suggestion)

        except Exception as e:
            logger.error(f"Error generating path mapping suggestions: {e}")

        return suggestions

    def _generate_mapping_suggestion(
        self, plex_prefix: str, in_docker: bool
    ) -> Optional[PathMappingSuggestion]:
        """Generate a single path mapping suggestion."""
        import os

        # Check if this prefix is already mapped
        if plex_prefix in self.path_mappings:
            return None

        # Docker-specific suggestions
        if in_docker:
            # Check if common Docker mount points exist
            for mount in COMMON_MEDIA_MOUNTS:
                if os.path.exists(mount) and os.path.isdir(mount):
                    # Suggest mapping Plex prefix to this mount
                    return PathMappingSuggestion(
                        plex_prefix=plex_prefix,
                        suggested_local_prefix=mount,
                        confidence="medium",
                        reason=f"Found {mount} directory in Docker container. "
                        f"Common pattern: map Plex's '{plex_prefix}' to container's '{mount}'.",
                    )

            # Default Docker suggestion
            return PathMappingSuggestion(
                plex_prefix=plex_prefix,
                suggested_local_prefix="/mnt/library",
                confidence="low",
                reason=f"Running in Docker. Consider mounting your media to a container path "
                f"and mapping '{plex_prefix}' to that path.",
            )

        # Non-Docker suggestions
        else:
            # Check if Plex prefix exists locally
            if os.path.exists(plex_prefix) and os.path.isdir(plex_prefix):
                return PathMappingSuggestion(
                    plex_prefix=plex_prefix,
                    suggested_local_prefix=plex_prefix,
                    confidence="high",
                    reason=(
                        f"Path '{plex_prefix}' exists locally. If Plex and plexsubs are "
                        f"on the same machine with the same paths, use identity mapping."
                    ),
                )

            # Check common local mount points
            for mount in COMMON_MEDIA_MOUNTS:
                if os.path.exists(mount) and os.path.isdir(mount):
                    return PathMappingSuggestion(
                        plex_prefix=plex_prefix,
                        suggested_local_prefix=mount,
                        confidence="low",
                        reason=(
                            f"Path '{plex_prefix}' not found locally. "
                            f"Check if your media is mounted at {mount}."
                        ),
                    )

        return None
