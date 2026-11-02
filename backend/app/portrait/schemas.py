"""The crop of the portrait: the point that stays in view, in percent of the
width and height of the image, and how far the image is zoomed around it."""

from pydantic import BaseModel, Field

FOCUS_MAX = 100
FOCUS_CENTER = FOCUS_MAX // 2
# In percent, 100 shows the whole image as the page crops it.
ZOOM_MIN = 100
ZOOM_MAX = 300


class PortraitCrop(BaseModel):
    x: int = Field(ge=0, le=FOCUS_MAX)
    y: int = Field(ge=0, le=FOCUS_MAX)
    zoom: int = Field(ge=ZOOM_MIN, le=ZOOM_MAX)
