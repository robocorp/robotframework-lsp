from PIL import Image, ImageTk
from RPA.core.geometry import Region
from io import BytesIO
from typing import NamedTuple
from typing import Optional
import base64
import json
import logging
import mss
import tkinter as tk
import sys
import os

__file__ = os.path.abspath(__file__)


class SnipResult(NamedTuple):
    region: Region
    template: str
    source: str


"""if IS_WINDOWS:
    from ctypes import windll

    try:
        windll.user32.SetProcessDPIAware()
    except AttributeError:  # Might not be supported
        pass
"""

LIGHTEST_GREY = "#f0f0f0"


def get_snip() -> Optional[SnipResult]:
    try:
        snipper = SnippingToolWindow()
        return snipper.run()
    except Exception as err:
        # FIXME: can we use the real logger here?
        logging.error(err)
        return None


def to_base64(screenshot):
    data = mss.tools.to_png(screenshot.rgb, screenshot.size)
    return base64.b64encode(data).decode()


class SnippingToolWindow:
    def __init__(self, timeout=30, logger=None):
        """
        Starts a full screen snipping tool for selecting coordinates
        """
        self.timeout = timeout
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.snip: str = None
        self.coordinates: Region = None

        self.active_monitor = 1

        with mss.mss() as sct:
            self.virtual_pixel_height = sct.monitors[self.active_monitor]["height"]
            self.virtual_pixel_width = sct.monitors[self.active_monitor]["width"]
            sct_source = sct.grab(sct.monitors[self.active_monitor])
            self.base64_src = to_base64(sct_source)
            pil_img = Image.frombytes(
                "RGB", sct_source.size, sct_source.bgra, "raw", "BGRX"
            )
            self.pil_format_src = pil_img

        self.root = tk.Tk()
        self.root.configure(bg=LIGHTEST_GREY)
        # Bring window to full screen and top most level. For some reason this overridedirect toggling is required
        # To let this work on macOS https://stackoverflow.com/a/42173885/6734941
        self.root.overrideredirect(True)
        self.root.overrideredirect(False)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)

        self.x = self.y = self.end_x = self.end_y = 0
        self.rect = None
        self.start_x = None
        self.start_y = None

        # Create the canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.virtual_pixel_width,
            height=self.virtual_pixel_height,
            cursor="crosshair",
        )
        self.canvas.pack()
        # Add the screenshot
        # Scale image to fit screen when displayed with TK. Required to make "fake display"
        # size correctly on scaled resolutions screens
        resized = pil_img.resize(
            (self.virtual_pixel_width, self.virtual_pixel_height), Image.LANCZOS
        )
        self.img = ImageTk.PhotoImage(resized)
        self.canvas.create_image((0, 0), image=self.img, anchor="nw")
        # FIXME: doesn't work at least on macOS
        # Focus users input on the canvas
        self.canvas.focus()
        self.canvas.focus_force()

        # Connect the event handlers
        self.canvas.bind("<Escape>", self.close)
        # self.canvas.bind("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def run(self) -> SnipResult:
        """Create window and start handling messages."""
        self.root.after(self.timeout * 1000, self.on_timeout)
        self.root.mainloop()
        return SnipResult(self.coordinates, self.snip, self.base64_src)

    def on_timeout(self):
        self.close(None)
        self.logger.debug("Snipping dialog timed out")
        return None, None, None

    def close(self, event=None):
        self.logger.debug("Calling self.quit")
        self.root.quit()

    def on_button_press(self, event):
        """
        On button press
        """

        # Update coordinates
        self.start_x = event.x
        self.start_y = event.y

        self.end_x = event.x
        self.end_y = event.y

        # If no rectangle is drawn yet, draw one
        if not self.rect:
            self.rect = self.canvas.create_rectangle(
                self.x, self.y, 1, 1, outline="#1B97F3", stipple="gray12"
            )

    def on_move(self, event):
        """
        On mouse move
        """
        # Update coordinates
        self.end_x, self.end_y = (event.x, event.y)

        # expand rectangle as you drag the mouse
        self.canvas.coords(
            self.rect, self.start_x, self.start_y, self.end_x, self.end_y
        )

    def on_button_release(self, event):
        self.logger.debug("Button released")
        pixel_width, pixel_height = self.pil_format_src.size
        height_scaling = pixel_height / self.root.winfo_height()
        width_scaling = pixel_width / self.root.winfo_width()
        if height_scaling != width_scaling:
            self.logger.warning(
                f"Uneven height and width scalings: height {height_scaling}, width {width_scaling}. "
                "This might mean that the window is not truly fullscreen or that the screenshot "
                "missed something"
            )
        scale_factor = height_scaling
        self.logger.debug(f"Calculated scale factor of {scale_factor}")
        coordinates = (
            scale_factor * min(self.start_x, self.end_x),
            scale_factor * min(self.start_y, self.end_y),
            scale_factor * max(self.start_x, self.end_x),
            scale_factor * max(self.start_y, self.end_y),
        )

        self.coordinates = coordinates
        crop_raw = self.pil_format_src.crop(coordinates)
        crop_bytes_buffer = BytesIO()
        crop_raw.save(crop_bytes_buffer, format="png")
        self.snip = base64.b64encode(crop_bytes_buffer.getvalue()).decode()
        self.logger.debug("Closing since button was released")
        self.close()


if __name__ == "__main__":
    result: Optional[SnipResult] = get_snip()
    assert result
    print(json.dumps(result))
