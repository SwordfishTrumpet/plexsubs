"""Tests for configuration validators."""

import pytest

from plexsubs.config.validators import (
    parse_language_codes,
    validate_boolean,
    validate_language_code,
    validate_log_level,
    validate_non_empty_string,
    validate_path_mappings,
    validate_port,
    validate_positive_integer,
    validate_regex_pattern,
    validate_token,
    validate_url,
)


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert validate_url("http://localhost:32400") == "http://localhost:32400"
        assert validate_url("http://example.com") == "http://example.com"

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://plex.example.com") == "https://plex.example.com"
        assert validate_url("https://192.168.1.1:32400") == "https://192.168.1.1:32400"

    def test_url_without_protocol_fails(self):
        """Test URL without protocol fails."""
        with pytest.raises(ValueError, match="must start with http:// or https://"):
            validate_url("localhost:32400")
        with pytest.raises(ValueError, match="must start with http:// or https://"):
            validate_url("example.com")
        with pytest.raises(ValueError, match="must start with http:// or https://"):
            validate_url("ftp://example.com")

    def test_empty_url_fails(self):
        """Test empty URL fails."""
        with pytest.raises(ValueError, match="is required"):
            validate_url("")
        with pytest.raises(ValueError, match="is required"):
            validate_url(None)

    def test_whitespace_only_url_fails(self):
        """Test whitespace-only URL fails - EDGE CASE.

        Whitespace-only strings are not caught by 'not url' check,
        so they fail at the protocol validation step instead.
        """
        with pytest.raises(ValueError, match="must start with http:// or https://"):
            validate_url("   ")

    def test_custom_field_name_in_error(self):
        """Test custom field name appears in error."""
        with pytest.raises(ValueError, match="PLEX_URL is required"):
            validate_url("", field_name="PLEX_URL")


class TestValidateToken:
    """Tests for validate_token function."""

    def test_valid_token(self):
        """Test valid token passes."""
        token = "x" * 20
        assert validate_token(token) == token

    def test_token_minimum_length(self):
        """Test token meets minimum length."""
        min_token = "x" * 10
        assert validate_token(min_token, min_length=10) == min_token

    def test_token_too_short_fails(self):
        """Test token too short fails."""
        with pytest.raises(ValueError, match="must be at least 10 characters"):
            validate_token("short")
        with pytest.raises(ValueError, match="must be at least 20 characters"):
            validate_token("x" * 15, min_length=20)

    def test_empty_token_fails(self):
        """Test empty token fails."""
        with pytest.raises(ValueError, match="is required"):
            validate_token("")
        with pytest.raises(ValueError, match="is required"):
            validate_token(None)

    def test_custom_min_length(self):
        """Test custom minimum length."""
        assert validate_token("abc", min_length=3) == "abc"
        with pytest.raises(ValueError, match="must be at least 5 characters"):
            validate_token("abc", min_length=5)

    def test_plex_token_field_name(self):
        """Test with PLEX_TOKEN field name."""
        with pytest.raises(ValueError, match="PLEX_TOKEN"):
            validate_token("", field_name="PLEX_TOKEN")


class TestValidateLanguageCode:
    """Tests for validate_language_code function."""

    def test_valid_2_letter_codes(self):
        """Test valid 2-letter codes."""
        assert validate_language_code("en") == "en"
        assert validate_language_code("nl") == "nl"
        assert validate_language_code("de") == "de"

    def test_invalid_code_fails(self):
        """Test invalid codes fail."""
        with pytest.raises(ValueError, match="Invalid language code"):
            validate_language_code("xx")
        with pytest.raises(ValueError, match="Invalid language code"):
            validate_language_code("invalid")

    def test_empty_code_fails(self):
        """Test empty code fails."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_language_code("")
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_language_code("   ")

    def test_case_normalization(self):
        """Test codes are normalized to lowercase."""
        assert validate_language_code("EN") == "en"
        assert validate_language_code("Nl") == "nl"

    def test_whitespace_trimming(self):
        """Test whitespace is trimmed."""
        assert validate_language_code("  en  ") == "en"


class TestParseLanguageCodes:
    """Tests for parse_language_codes function."""

    def test_single_language(self):
        """Test single language code."""
        assert parse_language_codes("en") == ["en"]
        assert parse_language_codes("nl") == ["nl"]

    def test_multiple_languages(self):
        """Test multiple comma-separated languages."""
        assert parse_language_codes("en,nl,de") == ["en", "nl", "de"]

    def test_whitespace_handling(self):
        """Test whitespace around codes is trimmed."""
        assert parse_language_codes("en , nl , de") == ["en", "nl", "de"]
        assert parse_language_codes("  en  ") == ["en"]

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert parse_language_codes("EN,NL") == ["en", "nl"]

    def test_empty_string_defaults_to_english(self):
        """Test empty string returns default English."""
        assert parse_language_codes("") == ["en"]
        assert parse_language_codes("   ") == ["en"]
        assert parse_language_codes(None) == ["en"]

    def test_invalid_codes_filtered_out(self):
        """Test invalid codes are filtered out."""
        assert parse_language_codes("en,xx,nl") == ["en", "nl"]
        assert parse_language_codes("xx,yy,zz") == ["en"]  # All invalid defaults to en

    def test_all_invalid_returns_default(self):
        """Test all invalid codes returns default."""
        assert parse_language_codes("invalid,alsoinvalid") == ["en"]

    def test_empty_entries_filtered(self):
        """Test empty entries in comma list are filtered."""
        assert parse_language_codes("en,,nl") == ["en", "nl"]
        assert parse_language_codes(",en,") == ["en"]


class TestValidatePort:
    """Tests for validate_port function."""

    def test_valid_ports(self):
        """Test valid port numbers."""
        assert validate_port(1) == 1
        assert validate_port(80) == 80
        assert validate_port(32400) == 32400
        assert validate_port(65535) == 65535

    def test_port_too_low_fails(self):
        """Test port below 1 fails."""
        with pytest.raises(ValueError, match="between 1 and 65535"):
            validate_port(0)
        with pytest.raises(ValueError, match="between 1 and 65535"):
            validate_port(-1)
        with pytest.raises(ValueError, match="between 1 and 65535"):
            validate_port(-100)

    def test_port_too_high_fails(self):
        """Test port above 65535 fails."""
        with pytest.raises(ValueError, match="between 1 and 65535"):
            validate_port(65536)
        with pytest.raises(ValueError, match="between 1 and 65535"):
            validate_port(100000)

    def test_string_port_converted(self):
        """Test string port numbers are converted."""
        assert validate_port("8080") == 8080
        assert validate_port("32400") == 32400

    def test_invalid_string_fails(self):
        """Test invalid string fails."""
        with pytest.raises(ValueError, match="must be a valid integer"):
            validate_port("abc")
        with pytest.raises(ValueError, match="must be a valid integer"):
            validate_port("12.34")


class TestValidatePositiveInteger:
    """Tests for validate_positive_integer function."""

    def test_valid_positive_integers(self):
        """Test valid positive integers."""
        assert validate_positive_integer(1) == 1
        assert validate_positive_integer(100) == 100
        assert validate_positive_integer(999999) == 999999

    def test_zero_fails(self):
        """Test zero fails."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_positive_integer(0)

    def test_negative_fails(self):
        """Test negative numbers fail."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_positive_integer(-1)
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_positive_integer(-100)

    def test_string_converted(self):
        """Test string numbers are converted."""
        assert validate_positive_integer("5") == 5
        assert validate_positive_integer("100") == 100

    def test_invalid_string_fails(self):
        """Test invalid string fails."""
        with pytest.raises(ValueError, match="must be a valid integer"):
            validate_positive_integer("abc")


class TestValidatePathMappings:
    """Tests for validate_path_mappings function."""

    def test_single_mapping(self):
        """Test single path mapping."""
        result = validate_path_mappings("/media:/mnt/library")
        assert result == {"/media": "/mnt/library"}

    def test_multiple_mappings(self):
        """Test multiple path mappings."""
        result = validate_path_mappings("/media:/mnt/library,/data:/mnt/data")
        assert result == {"/media": "/mnt/library", "/data": "/mnt/data"}

    def test_whitespace_trimmed(self):
        """Test whitespace is trimmed."""
        result = validate_path_mappings(" /media : /mnt/library ")
        assert result == {"/media": "/mnt/library"}

    def test_none_returns_empty_dict(self):
        """Test None returns empty dict."""
        assert validate_path_mappings(None) == {}

    def test_empty_string_returns_empty_dict(self):
        """Test empty string returns empty dict."""
        assert validate_path_mappings("") == {}

    def test_whitespace_only_returns_empty_dict(self):
        """Test whitespace-only returns empty dict."""
        assert validate_path_mappings("   ") == {}

    def test_missing_colon_fails(self):
        """Test missing colon fails."""
        with pytest.raises(ValueError, match="Invalid path mapping format"):
            validate_path_mappings("/media/mnt")

    def test_empty_source_path_fails(self):
        """Test empty source path fails."""
        with pytest.raises(ValueError, match="empty path"):
            validate_path_mappings(":/mnt/library")

    def test_empty_dest_path_fails(self):
        """Test empty destination path fails."""
        with pytest.raises(ValueError, match="empty path"):
            validate_path_mappings("/media:")

    def test_whitespace_only_paths_fails(self):
        """Test whitespace-only paths fail."""
        with pytest.raises(ValueError, match="empty path"):
            validate_path_mappings("   :/mnt")
        with pytest.raises(ValueError, match="empty path"):
            validate_path_mappings("/media:   ")

    def test_empty_entries_ignored(self):
        """Test empty entries in comma list are ignored."""
        result = validate_path_mappings("/media:/mnt,,/data:/data")
        assert result == {"/media": "/mnt", "/data": "/data"}

    def test_windows_paths(self):
        """Test Windows-style paths."""
        # EDGE CASE: This reveals the Windows drive letter issue!
        result = validate_path_mappings("C:\\Media:D:\\Library")
        # Due to split on first colon, this creates {"C": "\Media:D:\\Library"}
        # This is a BUG - Windows paths with drive letters don't work correctly
        assert result == {"C": r"\Media:D:\Library"}  # Documented edge case

    def test_complex_paths(self):
        """Test complex paths with spaces."""
        result = validate_path_mappings("/media/my movies:/mnt/movies")
        assert result == {"/media/my movies": "/mnt/movies"}


class TestValidateLogLevel:
    """Tests for validate_log_level function."""

    def test_valid_levels(self):
        """Test valid log levels."""
        assert validate_log_level("DEBUG") == "DEBUG"
        assert validate_log_level("INFO") == "INFO"
        assert validate_log_level("WARNING") == "WARNING"
        assert validate_log_level("ERROR") == "ERROR"
        assert validate_log_level("CRITICAL") == "CRITICAL"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert validate_log_level("debug") == "DEBUG"
        assert validate_log_level("Info") == "INFO"
        assert validate_log_level("ERROR") == "ERROR"

    def test_whitespace_trimmed(self):
        """Test whitespace is trimmed."""
        assert validate_log_level("  info  ") == "INFO"

    def test_invalid_level_fails(self):
        """Test invalid log level fails."""
        with pytest.raises(ValueError, match="Invalid log level"):
            validate_log_level("VERBOSE")
        with pytest.raises(ValueError, match="Invalid log level"):
            validate_log_level("TRACE")

    def test_error_lists_valid_options(self):
        """Test error message lists valid options."""
        with pytest.raises(ValueError) as exc_info:
            validate_log_level("INVALID")
        # Check that all valid levels are mentioned (order may vary since it's a set)
        message = str(exc_info.value)
        assert "Must be one of:" in message
        assert "DEBUG" in message
        assert "INFO" in message
        assert "WARNING" in message
        assert "ERROR" in message
        assert "CRITICAL" in message


class TestValidateBoolean:
    """Tests for validate_boolean function."""

    def test_true_boolean(self):
        """Test actual boolean True."""
        assert validate_boolean(True) is True

    def test_false_boolean(self):
        """Test actual boolean False."""
        assert validate_boolean(False) is False

    def test_string_true_values(self):
        """Test string representations of True."""
        assert validate_boolean("true") is True
        assert validate_boolean("True") is True
        assert validate_boolean("TRUE") is True
        assert validate_boolean("1") is True
        assert validate_boolean("yes") is True
        assert validate_boolean("YES") is True
        assert validate_boolean("on") is True
        assert validate_boolean("ON") is True

    def test_string_false_values(self):
        """Test string representations of False."""
        assert validate_boolean("false") is False
        assert validate_boolean("False") is False
        assert validate_boolean("FALSE") is False
        assert validate_boolean("0") is False
        assert validate_boolean("no") is False
        assert validate_boolean("NO") is False
        assert validate_boolean("off") is False
        assert validate_boolean("OFF") is False

    def test_integer_values(self):
        """Test integer conversions."""
        assert validate_boolean(1) is True
        assert validate_boolean(0) is False
        assert validate_boolean(42) is True  # Non-zero is truthy
        assert validate_boolean(-5) is True  # Negative non-zero is truthy

    def test_whitespace_trimmed(self):
        """Test whitespace is trimmed."""
        assert validate_boolean("  true  ") is True
        assert validate_boolean("  false  ") is False

    def test_invalid_string_fails(self):
        """Test invalid string values fail."""
        with pytest.raises(ValueError, match="must be a boolean value"):
            validate_boolean("maybe")
        with pytest.raises(ValueError, match="must be a boolean value"):
            validate_boolean("enabled")

    def test_none_fails(self):
        """Test None fails."""
        with pytest.raises(ValueError, match="must be a boolean value"):
            validate_boolean(None)

    def test_list_fails(self):
        """Test list fails."""
        with pytest.raises(ValueError, match="must be a boolean value"):
            validate_boolean([True])


class TestValidateRegexPattern:
    """Tests for validate_regex_pattern function."""

    def test_valid_patterns(self):
        """Test valid regex patterns."""
        assert validate_regex_pattern(".*") == ".*"
        assert validate_regex_pattern("^test$") == "^test$"
        assert validate_regex_pattern(r"\d+") == r"\d+"

    def test_complex_pattern(self):
        """Test complex regex patterns."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        assert validate_regex_pattern(pattern) == pattern

    def test_empty_pattern_fails(self):
        """Test empty pattern fails."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_regex_pattern("")

    def test_invalid_regex_fails(self):
        """Test invalid regex fails."""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            validate_regex_pattern("[invalid")
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            validate_regex_pattern("(unclosed")
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            validate_regex_pattern("*invalid")


class TestValidateNonEmptyString:
    """Tests for validate_non_empty_string function."""

    def test_valid_string(self):
        """Test valid non-empty string."""
        assert validate_non_empty_string("hello") == "hello"
        assert validate_non_empty_string("  hello  ") == "hello"  # trimmed

    def test_whitespace_trimmed(self):
        """Test whitespace is trimmed."""
        assert validate_non_empty_string("  test  ") == "test"
        assert validate_non_empty_string("\t\nhello\t\n") == "hello"

    def test_none_fails(self):
        """Test None fails."""
        with pytest.raises(ValueError, match="is required"):
            validate_non_empty_string(None)

    def test_empty_string_fails(self):
        """Test empty string fails."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_non_empty_string("")

    def test_whitespace_only_fails(self):
        """Test whitespace-only string fails after trimming."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_non_empty_string("   ")
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_non_empty_string("\t\n  \t\n")

    def test_non_string_fails(self):
        """Test non-string values fail."""
        with pytest.raises(ValueError, match="must be a string"):
            validate_non_empty_string(123)
        with pytest.raises(ValueError, match="must be a string"):
            validate_non_empty_string(["hello"])
        with pytest.raises(ValueError, match="must be a string"):
            validate_non_empty_string({"key": "value"})

    def test_custom_field_name(self):
        """Test custom field name in error."""
        with pytest.raises(ValueError, match="USERNAME"):
            validate_non_empty_string("", field_name="USERNAME")
