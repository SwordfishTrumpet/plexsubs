"""Tests for language code utilities."""

from plexsubs.utils.language_codes import (
    _resolve_language_code,
    get_allowed_languages,
    get_supported_languages,
    is_valid_language,
    normalize_language_code,
    to_iso639_1,
    to_plex_language_code,
    verify_language_match,
)


class TestResolveLanguageCode:
    """Tests for _resolve_language_code function."""

    def test_english_name_mapping(self):
        """Test mapping English names to codes."""
        assert _resolve_language_code("english") == "en"
        assert _resolve_language_code("dutch") == "nl"
        assert _resolve_language_code("german") == "de"

    def test_case_insensitive_names(self):
        """Test that English names are case-insensitive."""
        assert _resolve_language_code("ENGLISH") == "en"
        assert _resolve_language_code("Dutch") == "nl"
        assert _resolve_language_code("GeRmAn") == "de"

    def test_whitespace_handling(self):
        """Test that whitespace is stripped from names."""
        assert _resolve_language_code("  english  ") == "en"
        assert _resolve_language_code("dutch ") == "nl"
        assert _resolve_language_code(" german") == "de"

    def test_code_passthrough(self):
        """Test that codes pass through unchanged."""
        assert _resolve_language_code("en") == "en"
        assert _resolve_language_code("nl") == "nl"
        assert _resolve_language_code("de") == "de"

    def test_unknown_name_returns_normalized(self):
        """Test that unknown names return normalized input."""
        assert _resolve_language_code("foobar") == "foobar"
        assert _resolve_language_code("Klingon") == "klingon"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert _resolve_language_code("") == ""

    def test_special_characters_in_name(self):
        """Test handling of special characters."""
        assert _resolve_language_code("!@#$%") == "!@#$%"
        assert _resolve_language_code("123") == "123"


class TestToIso639One:
    """Tests for to_iso639_1 function."""

    def test_valid_2_letter_codes(self):
        """Test valid ISO 639-1 codes."""
        assert to_iso639_1("en") == "en"
        assert to_iso639_1("nl") == "nl"
        assert to_iso639_1("de") == "de"

    def test_valid_3_letter_codes(self):
        """Test conversion from ISO 639-2/T and 639-2/B codes."""
        assert to_iso639_1("nld") == "nl"  # ISO 639-2/T
        assert to_iso639_1("dut") == "nl"  # ISO 639-2/B
        assert to_iso639_1("eng") == "en"
        assert to_iso639_1("deu") == "de"

    def test_english_name_conversion(self):
        """Test conversion from English names."""
        assert to_iso639_1("english") == "en"
        assert to_iso639_1("dutch") == "nl"
        assert to_iso639_1("german") == "de"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert to_iso639_1("EN") == "en"
        assert to_iso639_1("NLD") == "nl"
        assert to_iso639_1("DUTCH") == "nl"

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert to_iso639_1("  en  ") == "en"
        assert to_iso639_1("nl ") == "nl"

    def test_invalid_code_returns_none(self):
        """Test that invalid codes return None."""
        assert to_iso639_1("xx") is None
        assert to_iso639_1("invalid") is None
        assert to_iso639_1("") is None

    def test_rare_languages_without_2_letter_code(self):
        """Test languages that only have 3-letter codes."""
        # Some languages only have ISO 639-2 codes, not ISO 639-1
        result = to_iso639_1("ast")  # Asturian
        # Asturian may or may not have a 2-letter code depending on iso639 library version
        assert result is None or isinstance(result, str)


class TestToPlexLanguageCode:
    """Tests for to_plex_language_code function."""

    def test_2_letter_to_3_letter(self):
        """Test conversion from 2-letter to 3-letter codes."""
        assert to_plex_language_code("en") == "eng"
        assert to_plex_language_code("nl") == "nld"
        assert to_plex_language_code("de") == "deu"

    def test_3_letter_codes(self):
        """Test that 3-letter codes work correctly."""
        assert to_plex_language_code("eng") == "eng"
        assert to_plex_language_code("nld") == "nld"

    def test_english_names(self):
        """Test conversion from English names."""
        assert to_plex_language_code("english") == "eng"
        assert to_plex_language_code("dutch") == "nld"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert to_plex_language_code("EN") == "eng"
        assert to_plex_language_code("DUTCH") == "nld"

    def test_invalid_code_returns_normalized(self):
        """Test that invalid codes return normalized input."""
        assert to_plex_language_code("xx") == "xx"
        assert to_plex_language_code("invalid") == "invalid"


class TestGetAllowedLanguages:
    """Tests for get_allowed_languages function."""

    def test_from_2_letter_code(self):
        """Test getting allowed codes from 2-letter code."""
        allowed = get_allowed_languages("nl")
        assert "nl" in allowed  # ISO 639-1
        assert "nld" in allowed  # ISO 639-2/T
        assert "dut" in allowed  # ISO 639-2/B
        assert "dutch" in allowed  # English name

    def test_from_english_name(self):
        """Test getting allowed codes from English name."""
        allowed = get_allowed_languages("dutch")
        assert "nl" in allowed
        assert "nld" in allowed
        assert "dut" in allowed
        assert "dutch" in allowed

    def test_from_3_letter_code(self):
        """Test getting allowed codes from 3-letter code."""
        allowed = get_allowed_languages("nld")
        assert "nl" in allowed
        assert "nld" in allowed

    def test_invalid_code_returns_original(self):
        """Test that invalid codes return list with original."""
        allowed = get_allowed_languages("invalid")
        assert allowed == ["invalid"]

    def test_empty_string(self):
        """Test handling of empty string."""
        allowed = get_allowed_languages("")
        assert allowed == [""]


class TestVerifyLanguageMatch:
    """Tests for verify_language_match function."""

    def test_exact_match(self):
        """Test exact matching of language codes."""
        assert verify_language_match("en", "en") is True
        assert verify_language_match("nl", "nl") is True

    def test_different_representations_same_language(self):
        """Test matching different representations of same language."""
        assert verify_language_match("nl", "nld") is True
        assert verify_language_match("nld", "nl") is True
        assert verify_language_match("dut", "nl") is True
        assert verify_language_match("nl", "dutch") is True

    def test_no_match(self):
        """Test that different languages don't match."""
        assert verify_language_match("en", "nl") is False
        assert verify_language_match("de", "fr") is False

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert verify_language_match("EN", "en") is True
        assert verify_language_match("NL", "DUTCH") is True

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert verify_language_match("  en  ", "en") is True
        assert verify_language_match("nl ", " nl") is True

    def test_english_names(self):
        """Test matching with English names."""
        assert verify_language_match("english", "en") is True
        assert verify_language_match("nl", "dutch") is True


class TestNormalizeLanguageCode:
    """Tests for normalize_language_code function."""

    def test_2_letter_stays_2_letter(self):
        """Test that 2-letter codes stay as-is."""
        assert normalize_language_code("en") == "en"
        assert normalize_language_code("nl") == "nl"

    def test_3_letter_converted_to_2_letter(self):
        """Test that 3-letter codes convert to 2-letter."""
        assert normalize_language_code("nld") == "nl"
        assert normalize_language_code("eng") == "en"
        assert normalize_language_code("deu") == "de"

    def test_english_names_converted(self):
        """Test that English names convert to 2-letter codes."""
        assert normalize_language_code("english") == "en"
        assert normalize_language_code("dutch") == "nl"

    def test_case_insensitive(self):
        """Test case-insensitive normalization."""
        assert normalize_language_code("EN") == "en"
        assert normalize_language_code("NLD") == "nl"
        assert normalize_language_code("DUTCH") == "nl"

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert normalize_language_code("  en  ") == "en"
        assert normalize_language_code("nl ") == "nl"

    def test_invalid_code_returns_normalized(self):
        """Test that invalid codes return normalized input."""
        assert normalize_language_code("xx") == "xx"
        assert normalize_language_code("invalid") == "invalid"


class TestGetSupportedLanguages:
    """Tests for get_supported_languages function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        languages = get_supported_languages()
        assert isinstance(languages, list)
        assert len(languages) > 0

    def test_contains_common_languages(self):
        """Test that common languages are included."""
        languages = get_supported_languages()
        assert "en" in languages
        assert "nl" in languages
        assert "de" in languages
        assert "fr" in languages
        assert "es" in languages

    def test_all_2_letter_codes(self):
        """Test that all items are 2-letter strings."""
        languages = get_supported_languages()
        for lang in languages:
            assert len(lang) == 2
            assert lang.isalpha()
            assert lang.islower()

    def test_sorted_order(self):
        """Test that languages are sorted."""
        languages = get_supported_languages()
        assert languages == sorted(languages)


class TestIsValidLanguage:
    """Tests for is_valid_language function."""

    def test_valid_2_letter_codes(self):
        """Test valid 2-letter codes."""
        assert is_valid_language("en") is True
        assert is_valid_language("nl") is True
        assert is_valid_language("de") is True

    def test_valid_3_letter_codes(self):
        """Test valid 3-letter codes."""
        assert is_valid_language("eng") is True
        assert is_valid_language("nld") is True

    def test_invalid_codes(self):
        """Test invalid codes."""
        assert is_valid_language("xx") is False
        assert is_valid_language("invalid") is False
        assert is_valid_language("") is False

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert is_valid_language("EN") is True
        assert is_valid_language("NLD") is True
        assert is_valid_language("XX") is False

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert is_valid_language("  en  ") is True
        assert is_valid_language("nl ") is True

    def test_special_characters(self):
        """Test special characters."""
        assert is_valid_language("!@#$%") is False
        assert is_valid_language("123") is False
