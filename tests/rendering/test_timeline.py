"""Tests for Timeline Generation Engine."""

import pytest
from app.rendering.timeline import (
    TrackType, TimelineElement, TimelineTrack, TimelineScene,
    Timeline, TimelineGenerator
)


class TestTimelineElement:
    def test_create_element(self):
        element = TimelineElement(
            element_id="elem_1",
            track_type=TrackType.VIDEO,
            start_time=0.0,
            duration=5.0,
            asset_key="video_001"
        )
        assert element.element_id == "elem_1"
        assert element.track_type == TrackType.VIDEO
        assert element.duration == 5.0
    
    def test_element_to_dict(self):
        element = TimelineElement(
            element_id="elem_1",
            track_type=TrackType.VOICE,
            start_time=10.0,
            duration=3.0,
            asset_key="voice_001"
        )
        d = element.to_dict()
        assert d["element_id"] == "elem_1"
        assert d["track_type"] == "voice"


class TestTimelineTrack:
    def test_add_elements(self):
        track = TimelineTrack(track_id="t1", track_type=TrackType.VIDEO)
        e1 = TimelineElement("e1", TrackType.VIDEO, 0.0, 5.0, "v1")
        e2 = TimelineElement("e2", TrackType.VIDEO, 5.0, 3.0, "v2")
        
        track.add_element(e1)
        track.add_element(e2)
        
        assert len(track.elements) == 2
        assert track.get_total_duration() == 8.0


class TestTimelineGenerator:
    def test_generate_timeline(self):
        generator = TimelineGenerator(organization_id=1)
        composition = {
            "id": 1,
            "resolution": "1920x1080",
            "fps": 30.0,
            "clips": [
                {"asset_key": "clip1", "duration": 5.0, "type": "video"},
                {"asset_key": "clip2", "duration": 3.0, "type": "image"}
            ],
            "audio_tracks": [],
            "subtitles": []
        }
        
        timeline = generator.generate_timeline(composition)
        
        assert timeline.organization_id == 1
        assert len(timeline.tracks) == 5  # VIDEO, IMAGE, VOICE, MUSIC, SUBTITLE
        assert len(timeline.scenes) == 2
        assert timeline.total_duration > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
