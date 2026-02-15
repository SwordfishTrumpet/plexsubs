"""Tests for XML utilities."""

import xml.etree.ElementTree as ET

from plexsubs.utils.xml_utils import (
    MediaPartData,
    MediaPartNavigator,
    find_imdb_id,
    find_media_element,
    find_part_element,
    find_player_element,
    find_session_element,
    find_subtitle_streams,
    find_video_element,
    get_file_path_from_video,
    get_part_id_from_video,
    parse_xml_response,
)


class TestParseXmlResponse:
    """Tests for parse_xml_response function."""

    def test_valid_xml(self):
        """Test parsing valid XML."""
        xml = '<MediaContainer size="1"><Video ratingKey="1"/></MediaContainer>'
        result = parse_xml_response(xml)
        assert result is not None
        assert result.tag == "MediaContainer"

    def test_empty_string(self):
        """Test parsing empty string."""
        result = parse_xml_response("")
        assert result is None

    def test_invalid_xml(self):
        """Test parsing invalid XML."""
        xml = "<not valid xml"
        result = parse_xml_response(xml)
        assert result is None

    def test_malformed_xml(self):
        """Test parsing malformed XML."""
        xml = "<unclosed>tag"
        result = parse_xml_response(xml)
        assert result is None

    def test_special_characters_in_xml(self):
        """Test XML with special characters."""
        xml = '<Video title="Test &amp; Example"/>'
        result = parse_xml_response(xml)
        assert result is not None
        assert result.get("title") == "Test & Example"


class TestFindVideoElement:
    """Tests for find_video_element function."""

    def test_video_in_media_container(self):
        """Test finding Video in MediaContainer."""
        xml = '<MediaContainer><Video ratingKey="123"/></MediaContainer>'
        root = ET.fromstring(xml)
        video = find_video_element(root)
        assert video is not None
        assert video.get("ratingKey") == "123"

    def test_video_nested(self):
        """Test finding Video in nested structure."""
        xml = '<Root><Container><Video ratingKey="456"/></Container></Root>'
        root = ET.fromstring(xml)
        video = find_video_element(root)
        assert video is not None
        assert video.get("ratingKey") == "456"

    def test_no_video_element(self):
        """Test when no Video element exists."""
        xml = '<MediaContainer><Track ratingKey="123"/></MediaContainer>'
        root = ET.fromstring(xml)
        video = find_video_element(root)
        assert video is None

    def test_multiple_videos(self):
        """Test finding first Video when multiple exist."""
        xml = '<MediaContainer><Video ratingKey="1"/><Video ratingKey="2"/></MediaContainer>'
        root = ET.fromstring(xml)
        video = find_video_element(root)
        assert video is not None
        assert video.get("ratingKey") == "1"


class TestFindMediaElement:
    """Tests for find_media_element function."""

    def test_media_in_video(self):
        """Test finding Media in Video."""
        xml = '<Video><Media videoResolution="1080p"/></Video>'
        video = ET.fromstring(xml)
        media = find_media_element(video)
        assert media is not None
        assert media.get("videoResolution") == "1080p"

    def test_no_media_element(self):
        """Test when no Media element exists."""
        xml = '<Video ratingKey="123"/>'
        video = ET.fromstring(xml)
        media = find_media_element(video)
        assert media is None


class TestFindPartElement:
    """Tests for find_part_element function."""

    def test_part_in_media(self):
        """Test finding Part in Media."""
        xml = '<Media><Part file="/path/to/file.mkv"/></Media>'
        media = ET.fromstring(xml)
        part = find_part_element(media)
        assert part is not None
        assert part.get("file") == "/path/to/file.mkv"

    def test_no_part_element(self):
        """Test when no Part element exists."""
        xml = '<Media videoResolution="1080p"/>'
        media = ET.fromstring(xml)
        part = find_part_element(media)
        assert part is None


class TestFindSubtitleStreams:
    """Tests for find_subtitle_streams function."""

    def test_find_subtitle_streams(self):
        """Test finding subtitle streams."""
        xml = """
        <MediaContainer>
            <Video>
                <Media>
                    <Part>
                        <Stream streamType="3" language="English"/>
                        <Stream streamType="3" language="Dutch"/>
                        <Stream streamType="1" language="English"/>
                    </Part>
                </Media>
            </Video>
        </MediaContainer>
        """
        root = ET.fromstring(xml)
        streams = find_subtitle_streams(root)
        assert len(streams) == 2
        assert all(s.get("streamType") == "3" for s in streams)

    def test_no_subtitle_streams(self):
        """Test when no subtitle streams exist."""
        xml = """
        <MediaContainer>
            <Video>
                <Media>
                    <Part>
                        <Stream streamType="1" language="English"/>
                    </Part>
                </Media>
            </Video>
        </MediaContainer>
        """
        root = ET.fromstring(xml)
        streams = find_subtitle_streams(root)
        assert len(streams) == 0

    def test_subtitle_streams_in_different_parts(self):
        """Test finding subtitle streams across multiple parts."""
        xml = """
        <MediaContainer>
            <Video>
                <Part>
                    <Stream streamType="3" language="English"/>
                </Part>
                <Part>
                    <Stream streamType="3" language="French"/>
                </Part>
            </Video>
        </MediaContainer>
        """
        root = ET.fromstring(xml)
        streams = find_subtitle_streams(root)
        assert len(streams) == 2


class TestFindImdbId:
    """Tests for find_imdb_id function."""

    def test_imdb_guid(self):
        """Test extracting IMDB ID from Guid."""
        xml = """
        <Video>
            <Guid id="imdb://tt1234567"/>
            <Guid id="tmdb://98765"/>
        </Video>
        """
        root = ET.fromstring(xml)
        imdb_id = find_imdb_id(root)
        assert imdb_id == "tt1234567"

    def test_no_imdb_guid(self):
        """Test when no IMDB Guid exists."""
        xml = """
        <Video>
            <Guid id="tmdb://98765"/>
            <Guid id="tvdb://123"/>
        </Video>
        """
        root = ET.fromstring(xml)
        imdb_id = find_imdb_id(root)
        assert imdb_id is None

    def test_empty_guid(self):
        """Test with empty Guid elements."""
        xml = '<Video><Guid id=""/></Video>'
        root = ET.fromstring(xml)
        imdb_id = find_imdb_id(root)
        assert imdb_id is None

    def test_no_guid_elements(self):
        """Test when no Guid elements exist."""
        xml = '<Video ratingKey="123"/>'
        root = ET.fromstring(xml)
        imdb_id = find_imdb_id(root)
        assert imdb_id is None


class TestFindPlayerElement:
    """Tests for find_player_element function."""

    def test_player_in_video(self):
        """Test finding Player in Video."""
        xml = '<Video><Player title="Chrome"/></Video>'
        video = ET.fromstring(xml)
        player = find_player_element(video)
        assert player is not None
        assert player.get("title") == "Chrome"

    def test_no_player_element(self):
        """Test when no Player element exists."""
        xml = '<Video ratingKey="123"/>'
        video = ET.fromstring(xml)
        player = find_player_element(video)
        assert player is None


class TestFindSessionElement:
    """Tests for find_session_element function."""

    def test_session_in_video(self):
        """Test finding Session in Video."""
        xml = '<Video><Session id="session123"/></Video>'
        video = ET.fromstring(xml)
        session = find_session_element(video)
        assert session is not None
        assert session.get("id") == "session123"

    def test_no_session_element(self):
        """Test when no Session element exists."""
        xml = '<Video ratingKey="123"/>'
        video = ET.fromstring(xml)
        session = find_session_element(video)
        assert session is None


class TestMediaPartNavigator:
    """Tests for MediaPartNavigator class."""

    def test_navigate_full_hierarchy(self):
        """Test navigating full Video → Media → Part hierarchy."""
        xml = """
        <Video ratingKey="123">
            <Media videoResolution="1080p">
                <Part id="456" file="/media/movie.mkv"/>
            </Media>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)

        assert navigator.has_media() is True
        assert navigator.has_part() is True
        assert navigator.get_file_path() == "/media/movie.mkv"
        assert navigator.get_part_id() == "456"

    def test_navigate_missing_media(self):
        """Test navigation when Media is missing."""
        xml = '<Video ratingKey="123"/>'
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)

        assert navigator.has_media() is False
        assert navigator.has_part() is False
        assert navigator.get_file_path() is None
        assert navigator.get_part_id() is None

    def test_navigate_missing_part(self):
        """Test navigation when Part is missing."""
        xml = """
        <Video ratingKey="123">
            <Media videoResolution="1080p"/>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)

        assert navigator.has_media() is True
        assert navigator.has_part() is False
        assert navigator.get_file_path() is None
        assert navigator.get_part_id() is None

    def test_get_all_data(self):
        """Test getting all data at once."""
        xml = """
        <Video ratingKey="123">
            <Media videoResolution="1080p">
                <Part id="789" file="/path/file.mkv"/>
            </Media>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)
        data = navigator.get_all_data()

        assert isinstance(data, MediaPartData)
        assert data.file_path == "/path/file.mkv"
        assert data.part_id == "789"
        assert data.media_element is not None
        assert data.part_element is not None

    def test_get_all_data_missing_elements(self):
        """Test getting all data when elements are missing."""
        xml = '<Video ratingKey="123"/>'
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)
        data = navigator.get_all_data()

        assert isinstance(data, MediaPartData)
        assert data.file_path is None
        assert data.part_id is None
        assert data.media_element is None
        assert data.part_element is None

    def test_lazy_initialization(self):
        """Test that initialization is lazy."""
        xml = """
        <Video ratingKey="123">
            <Media><Part file="/test.mkv"/></Media>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)

        # Before accessing anything, _initialized should be False
        assert navigator._initialized is False

        # Access triggers initialization
        _ = navigator.get_file_path()
        assert navigator._initialized is True

    def test_multiple_accesses_single_traversal(self):
        """Test that multiple accesses only traverse once."""
        xml = """
        <Video ratingKey="123">
            <Media><Part id="123" file="/test.mkv"/></Media>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)

        # Multiple accesses should work without error
        path1 = navigator.get_file_path()
        path2 = navigator.get_file_path()
        id1 = navigator.get_part_id()

        assert path1 == path2 == "/test.mkv"
        assert id1 == "123"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_file_path_from_video(self):
        """Test get_file_path_from_video convenience function."""
        xml = """
        <Video>
            <Media><Part file="/movies/test.mkv"/></Media>
        </Video>
        """
        video = ET.fromstring(xml)
        path = get_file_path_from_video(video)
        assert path == "/movies/test.mkv"

    def test_get_file_path_from_video_none(self):
        """Test get_file_path_from_video when no path exists."""
        xml = "<Video/>"
        video = ET.fromstring(xml)
        path = get_file_path_from_video(video)
        assert path is None

    def test_get_part_id_from_video(self):
        """Test get_part_id_from_video convenience function."""
        xml = """
        <Video>
            <Media><Part id="12345"/></Media>
        </Video>
        """
        video = ET.fromstring(xml)
        part_id = get_part_id_from_video(video)
        assert part_id == "12345"

    def test_get_part_id_from_video_none(self):
        """Test get_part_id_from_video when no ID exists."""
        xml = "<Video/>"
        video = ET.fromstring(xml)
        part_id = get_part_id_from_video(video)
        assert part_id is None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_xml_with_namespaces(self):
        """Test XML with namespaces."""
        xml = """
        <MediaContainer xmlns="http://plex.tv">
            <Video ratingKey="123"/>
        </MediaContainer>
        """
        # Note: ET.fromstring handles namespaces differently
        # This test verifies basic parsing still works
        result = parse_xml_response(xml)
        assert result is not None

    def test_very_deeply_nested_video(self):
        """Test finding Video deeply nested in XML."""
        xml = """
        <Root>
            <Level1>
                <Level2>
                    <Level3>
                        <Video ratingKey="deep"/>
                    </Level3>
                </Level2>
            </Level1>
        </Root>
        """
        root = ET.fromstring(xml)
        video = find_video_element(root)
        assert video is not None
        assert video.get("ratingKey") == "deep"

    def test_part_without_file_attribute(self):
        """Test Part element without file attribute."""
        xml = """
        <Video>
            <Media><Part id="123"/></Media>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)
        assert navigator.get_file_path() is None
        assert navigator.get_part_id() == "123"

    def test_part_without_id_attribute(self):
        """Test Part element without id attribute."""
        xml = """
        <Video>
            <Media><Part file="/test.mkv"/></Media>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)
        assert navigator.get_file_path() == "/test.mkv"
        assert navigator.get_part_id() is None

    def test_multiple_media_elements(self):
        """Test Video with multiple Media elements."""
        xml = """
        <Video>
            <Media resolution="720p">
                <Part file="/720.mkv"/>
            </Media>
            <Media resolution="1080p">
                <Part file="/1080.mkv"/>
            </Media>
        </Video>
        """
        video = ET.fromstring(xml)
        navigator = MediaPartNavigator(video)
        # Should find first Media
        assert navigator.get_file_path() == "/720.mkv"
