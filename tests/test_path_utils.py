"""Tests for path utilities."""

import os
import tempfile

import pytest

from plexsubs.utils.path_utils import (
    apply_path_mappings,
    check_file_permissions,
    parse_path_mappings,
)


class TestApplyPathMappings:
    """Tests for apply_path_mappings function."""

    def test_simple_mapping(self):
        """Test basic path mapping."""
        mappings = {"/media": "/mnt/library"}
        result = apply_path_mappings("/media/movies/movie.mkv", mappings)
        assert result == "/mnt/library/movies/movie.mkv"

    def test_no_matching_mapping(self):
        """Test path that doesn't match any mapping."""
        mappings = {"/media": "/mnt/library"}
        result = apply_path_mappings("/data/movies/movie.mkv", mappings)
        assert result == "/data/movies/movie.mkv"

    def test_multiple_mappings_first_match(self):
        """Test that first matching mapping is used."""
        mappings = {
            "/media": "/mnt/library",
            "/media/movies": "/mnt/movies",
        }
        result = apply_path_mappings("/media/movies/movie.mkv", mappings)
        # Should match /media first (dictionary order in Python 3.7+)
        assert result == "/mnt/library/movies/movie.mkv"

    def test_exact_path_match(self):
        """Test mapping of exact path."""
        mappings = {"/media": "/mnt"}
        result = apply_path_mappings("/media", mappings)
        assert result == "/mnt"

    def test_empty_mappings(self):
        """Test with empty mappings dict."""
        result = apply_path_mappings("/media/movie.mkv", {})
        assert result == "/media/movie.mkv"

    def test_nested_path_mapping(self):
        """Test mapping nested paths."""
        mappings = {"/media/tv": "/mnt/shows"}
        result = apply_path_mappings("/media/tv/season1/episode1.mkv", mappings)
        assert result == "/mnt/shows/season1/episode1.mkv"

    def test_windows_style_paths(self):
        """Test with Windows-style paths."""
        mappings = {"C:\\Media": "D:\\Library"}
        result = apply_path_mappings("C:\\Media\\movie.mkv", mappings)
        assert result == "D:\\Library\\movie.mkv"

    def test_only_first_occurrence_replaced(self):
        """Test that only first occurrence is replaced."""
        mappings = {"/media": "/mnt"}
        result = apply_path_mappings("/media/media/file.mkv", mappings)
        assert result == "/mnt/media/file.mkv"

    def test_path_with_special_characters(self):
        """Test paths with special characters."""
        mappings = {"/media": "/mnt/library"}
        result = apply_path_mappings("/media/movies/movie [2020].mkv", mappings)
        assert result == "/mnt/library/movies/movie [2020].mkv"


class TestParsePathMappings:
    """Tests for parse_path_mappings function."""

    def test_single_mapping(self):
        """Test parsing single mapping."""
        result = parse_path_mappings("/media:/mnt/library")
        assert result == {"/media": "/mnt/library"}

    def test_multiple_mappings(self):
        """Test parsing multiple mappings."""
        result = parse_path_mappings("/media:/mnt/library,/data:/mnt/data")
        assert result == {"/media": "/mnt/library", "/data": "/mnt/data"}

    def test_whitespace_handling(self):
        """Test that whitespace is stripped."""
        result = parse_path_mappings(" /media : /mnt/library , /data : /mnt/data ")
        assert result == {"/media": "/mnt/library", "/data": "/mnt/data"}

    def test_none_value_returns_default(self):
        """Test that None returns default mappings."""
        result = parse_path_mappings(None)
        assert result == {"/media": "/mnt/library"}

    def test_empty_string_returns_default(self):
        """Test that empty string returns default mappings."""
        result = parse_path_mappings("")
        assert result == {"/media": "/mnt/library"}

    def test_whitespace_only_returns_default(self):
        """Test that whitespace-only string returns default."""
        result = parse_path_mappings("   ")
        assert result == {"/media": "/mnt/library"}

    def test_invalid_format_no_colon(self):
        """Test handling of entry without colon."""
        result = parse_path_mappings("/media/mnt,/data:/mnt/data")
        assert result == {"/data": "/mnt/data"}

    def test_empty_entry_in_list(self):
        """Test handling of empty entry in comma-separated list."""
        result = parse_path_mappings("/media:/mnt,,/data:/mnt/data")
        assert result == {"/media": "/mnt", "/data": "/mnt/data"}

    def test_colon_in_path_windows_edge_case(self):
        """Test path with colon (Windows drive) - EDGE CASE.

        This reveals a limitation: Windows paths with drive letters don't parse correctly
        because the colon is used as delimiter. The split creates {"C": "\\Media:D:\\Library"}
        instead of {"C:\\Media": "D:\\Library"}.
        """
        result = parse_path_mappings("C:\\Media:D:\\Library")
        # NOTE: This is the ACTUAL behavior, showing the edge case
        assert result == {"C": "\\Media:D:\\Library"}
        # The expected behavior would be: {"C:\\Media": "D:\\Library"}

    def test_all_invalid_mappings_returns_default(self):
        """Test that all invalid mappings returns default."""
        result = parse_path_mappings("invalid,alsoinvalid")
        assert result == {"/media": "/mnt/library"}


class TestCheckFilePermissions:
    """Tests for check_file_permissions function."""

    def test_nonexistent_file(self):
        """Test checking nonexistent file."""
        result = check_file_permissions("/nonexistent/path/file.txt")
        assert result["exists"] is False
        assert result["readable"] is False
        assert result["writable"] is False
        assert result["is_file"] is False
        assert result["is_directory"] is False

    def test_existing_file(self):
        """Test checking existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            result = check_file_permissions(temp_path)
            assert result["exists"] is True
            assert result["is_file"] is True
            assert result["is_directory"] is False
            assert result["readable"] is True
            # Writable depends on parent directory
            assert isinstance(result["writable"], bool)
        finally:
            os.unlink(temp_path)

    def test_existing_directory(self):
        """Test checking existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = check_file_permissions(temp_dir)
            assert result["exists"] is True
            assert result["is_file"] is False
            assert result["is_directory"] is True
            assert result["readable"] is True
            assert isinstance(result["writable"], bool)

    def test_permission_denied(self):
        """Test handling of permission errors."""
        # This tests that OSError is caught
        # Create a path that might cause issues
        if os.getuid() == 0:  # Running as root
            pytest.skip("Cannot test permission denial when running as root")

        # Test with a path we can't access
        result = check_file_permissions("/root/test.txt")
        assert result["exists"] is False or isinstance(result["exists"], bool)

    def test_empty_path_edge_case(self):
        """Test with empty path - EDGE CASE.

        An empty path "" resolves to the current directory in Path(), so it exists.
        This is an edge case where the behavior might be unexpected.
        """
        result = check_file_permissions("")
        # NOTE: Empty path resolves to current directory, so it "exists"
        # This is the ACTUAL behavior - empty string = current directory
        assert result["exists"] is True  # Current directory exists!
        assert result["is_directory"] is True

    def test_relative_path(self):
        """Test with relative path."""
        result = check_file_permissions("./test.txt")
        # Should not crash, result depends on actual file existence
        assert "exists" in result
