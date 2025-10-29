"""YouTube entity schemas.

Entities extracted from YouTube API and LlamaIndex YouTube reader.
"""

from packages.schemas.youtube.channel import Channel
from packages.schemas.youtube.transcript import Transcript
from packages.schemas.youtube.video import Video

__all__ = ["Channel", "Transcript", "Video"]
