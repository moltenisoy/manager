from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Optional

class ProcessType(Enum):
    APP = "app"
    WEB = "web"
    DOCUMENT = "document"
    SYSTEM = "system"

class ViewMode(Enum):
    FLIP3D = "flip3d"
    STAGE = "stage"
    LIST = "list"

class CarouselStyle(Enum):
    DEFAULT = "default"
    DIAGONAL = "diagonal"
    PERSPECTIVE45 = "perspective45"
    PSEUDO3D = "pseudo3d"

class ThumbnailSize(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"

@dataclass
class ProcessInfo:
    pid: int
    hwnd: int
    name: str
    title: str
    memory_mb: float
    process_type: ProcessType = ProcessType.APP
    timestamp: float = field(default_factory=time.time)
    icon: str = "📱"
    image: Optional[Any] = None
    cpu_percent: float = 0.0
    status: str = "running"
    
    @property
    def id(self) -> str:
        return f"proc-{self.pid}-{self.hwnd}"

@dataclass
class AppSettings:
    default_view: ViewMode = ViewMode.FLIP3D
    carousel_style: CarouselStyle = CarouselStyle.DEFAULT
    animation_speed: float = 0.10
    keyboard_shortcuts: bool = True
    blur_strength: int = 12
    thumbnail_size: ThumbnailSize = ThumbnailSize.MEDIUM
    show_memory_on_thumbnails: bool = True
    uniform_aspect_ratio: bool = True
    process_blacklist: list = field(default_factory=list)
    flip3d_spacing: int = 150
    flip3d_card_scale: float = 1.0
    # New visual options
    show_borders: bool = True
    show_titles: bool = True