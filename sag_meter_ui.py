"""
Platformer Game

python -m arcade.examples.platform_tutorial.02_draw_sprites
"""
from typing import Union

import arcade
import arcade.gui
from arcade.gui import UIInputText, UIMessageBox, UIManager
from yoctopuce.yocto_api import YRefParam, YAPI
from yoctopuce.yocto_rangefinder import YRangeFinder

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Yoctopuce Sag meter"
DEFAULT_FONT = ("Kenney Future", "arial")
WINDOW_BG = arcade.csscolor.GREY


class SuspStatus:
    travel: int
    max_val: int
    mm_sag: int
    sag: int

    def __init__(self, travel: int):
        self.travel = travel
        self.max_val = 0
        self.sag = 0
        self.mm_sag = 0
        self.reset()

    def reset(self):
        self.max_val = 0
        self.sag = 0
        self.mm_sag = 0

    def update_value(self, new_val: int):
        # Update max value in case the app was started with the suspension compressed
        if new_val > self.max_val:
            self.max_val = new_val

        mm_sag = self.max_val - new_val
        sag = mm_sag * 100 // self.travel

        if sag != self.sag or mm_sag != self.mm_sag:
            self.sag = sag
            self.mm_sag = mm_sag
            # print("update value :"+self.get_sag_text())

    def get_sag_text(self) -> str:
        return "SAG = %d%%\n(%dmm)" % (self.sag, self.mm_sag)

    def get_travel_text(self):
        return "Travel = %dmm" % self.travel


class ApplicationConfig:
    url: str
    error: str
    all_rf: list[str]
    front_selection: str
    rear_selection: str
    front_rf: Union[YRangeFinder, None]
    rear_rf: Union[YRangeFinder, None]
    front_travel: int
    rear_travel: int
    front: SuspStatus
    rear: SuspStatus

    def __init__(self):
        self.url = "usb"
        self.error = ""
        self.all_rf = []
        self.front_selection = "None"
        self.rear_selection = "None"
        self.front_rf = None
        self.rear_rf = None
        self.front_travel = 160
        self.rear_travel = 75
        self.front = SuspStatus(self.front_travel)
        self.rear = SuspStatus(self.rear_travel)

    def setup(self) -> None:
        errmsg = YRefParam()
        if YAPI.RegisterHub(self.url, errmsg) != YAPI.SUCCESS:
            print("Unable to register hub %s: %s" % (self.url, errmsg.value))
            # if usb failed it's probably because a VirtualHub is running. Try to use the VirtualHub
            self.url = "127.0.0.1"
            if YAPI.RegisterHub(self.url, errmsg) != YAPI.SUCCESS:
                print("Unable to register hub %s: %s" % (self.url, errmsg.value))
                self.error = errmsg.value
                return
        rf: YRangeFinder = YRangeFinder.FirstRangeFinder()
        while rf is not None:
            self.all_rf.append(rf.get_hardwareId())
            name = rf.get_logicalName()
            if name == "front":
                self.front_selection = rf.get_hardwareId()
            elif name == "rear":
                self.rear_selection = rf.get_hardwareId()
            rf = rf.nextRangeFinder()

    def check_config(self) -> str:
        if self.error != "":
            return self.error
        if len(self.all_rf) == 0:
            return "No Yocto-RangeFinder detected on " + self.url
        return ""

    def check_parameters(self, fr_hwid: Union[str | None], fr_travel: int, rd_hwid: Union[str | None], rd_travel: int) -> str:
        try:
            self.front_travel = int(fr_travel)
        except ValueError:
            return "Invalid front travel"
        try:
            self.rear_travel = int(rd_travel)
        except ValueError:
            return "Invalid rear travel"

        if fr_hwid == "None" and rd_hwid == "None":
            return "You need to select at least one Yocto-RangeFinder device"
        self.front = SuspStatus(self.front_travel)
        self.rear = SuspStatus(self.rear_travel)
        if fr_hwid != "None":
            self.front_rf = YRangeFinder.FindRangeFinder(fr_hwid)
            self.front_rf.set_rangeFinderMode(YRangeFinder.RANGEFINDERMODE_HIGH_ACCURACY)
            self.front_rf.set_userData(self.front)
            self.front_rf.registerValueCallback(valueCallback)

        if rd_hwid != "None":
            self.rear_rf = YRangeFinder.FindRangeFinder(rd_hwid)
            self.rear_rf.set_rangeFinderMode(YRangeFinder.RANGEFINDERMODE_HIGH_ACCURACY)
            self.rear_rf.set_userData(self.rear)
            self.rear_rf.registerValueCallback(valueCallback)
        return ""


class AppView(arcade.View):
    """
    Main application class.
    """
    param: ApplicationConfig

    def __init__(self, param: ApplicationConfig):
        # Call the parent class and set up the window
        super().__init__()
        # bike texture
        self.bike_texture = None

        # Separate variable that holds the player sprite
        self.bike_sprite = None
        self.front_sag_text = None
        self.rear_sag_text = None
        self.front_travel_text = None
        self.rear_travel_text = None
        # SpriteList for our player
        self.fixed_spriteList = None

        self.camera = None
        self.param = param

    def setup(self):
        """Set up the game here. Call this function to restart the game."""
        # Variable to hold our texture for our player
        self.bike_texture = arcade.load_texture("lane.png")
        self.camera = arcade.Camera2D()

        # Separate variable that holds the player sprite
        self.bike_sprite = arcade.Sprite(self.bike_texture)
        self.bike_sprite.center_x = self.width // 2
        self.bike_sprite.center_y = self.height // 2
        self.bike_sprite.scale = 0.5

        self.fixed_spriteList = arcade.SpriteList()
        self.fixed_spriteList.append(self.bike_sprite)
        self.background_color = WINDOW_BG
        top_y = WINDOW_HEIGHT * 3 // 4
        bottom_y = WINDOW_HEIGHT // 8
        left_x = WINDOW_WIDTH // 4
        right_x = WINDOW_WIDTH * 3 // 4
        sag_font_size = 20
        self.front_sag_text = arcade.Text(self.param.front.get_sag_text(), font_name=DEFAULT_FONT, align="center", anchor_x="center", font_size=sag_font_size, x=right_x, y=top_y)
        self.rear_sag_text = arcade.Text(self.param.rear.get_sag_text(), font_name=DEFAULT_FONT, align="center", anchor_x="center", font_size=sag_font_size, x=left_x, y=top_y)
        self.front_travel_text = arcade.Text(self.param.front.get_travel_text(), font_name=DEFAULT_FONT, align="center", anchor_x="center", x=right_x, y=bottom_y)
        self.rear_travel_text = arcade.Text(self.param.rear.get_travel_text(), font_name=DEFAULT_FONT, align="center", anchor_x="center", x=left_x, y=bottom_y)

    def on_draw(self):
        """Render the screen."""

        # Clear the screen to the background color
        self.clear()

        # Activate our camera before drawing
        self.camera.use()
        # Draw our sprites
        self.fixed_spriteList.draw()
        self.front_sag_text.draw()
        self.rear_sag_text.draw()
        self.front_travel_text.draw()
        self.rear_travel_text.draw()

    def on_update(self, delta_time):
        YAPI.HandleEvents()
        self.front_sag_text.text = self.param.front.get_sag_text()
        self.rear_sag_text.text = self.param.rear.get_sag_text()

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""
        pass

    def on_key_release(self, key, modifiers):
        """Called whenever a key is released."""
        if key == arcade.key.ESCAPE:
            config_view = ConfigurationView(self.param)
            self.window.show_view(config_view)
            return


def valueCallback(rf, value):
    """Called by Yoctopuce SDK each time a new range measurement arrives."""
    p = rf.get_userData()
    p.update_value(int(value))


class ConfigurationView(arcade.View):
    """ Configuration application class."""

    config: ApplicationConfig
    manager: arcade.gui.UIManager

    def __init__(self, config: ApplicationConfig):
        super().__init__()
        self.config = config
        self.background_color = WINDOW_BG
        self.manager = arcade.gui.UIManager()
        widget_layout = arcade.gui.UIBoxLayout(align="TOP", font_name=DEFAULT_FONT, space_between=10)
        title_label_space = arcade.gui.UISpace(height=30, color=arcade.color.GRAY)

        title_label = arcade.gui.UILabel(text="Yoctopuce SAG meter", align="center", font_size=32, multiline=False)
        widget_layout.add(title_label_space)
        widget_layout.add(title_label)
        widget_layout.add(title_label_space)
        error = config.check_config()
        if error != '':
            error_label = arcade.gui.UILabel(text="Error: " + error, align="center", font_size=15, multiline=False)
            widget_layout.add(error_label)
            widget_layout.add(title_label_space)
            exit_button = arcade.gui.UIFlatButton(text="Exit", width=150)

            @exit_button.event("on_click")
            def on_click_exit_button(event):
                arcade.exit()

            widget_layout.add(exit_button)
        else:
            self.grid = arcade.gui.UIGridLayout(column_count=3, row_count=3, horizontal_spacing=20, vertical_spacing=20)
            # first row
            self.grid.add(arcade.gui.UILabel(text="Front", align="center", font_size=20, multiline=False), column=1, row=0)
            self.grid.add(arcade.gui.UILabel(text="Rear", align="center", font_size=20, multiline=False), column=2, row=0)
            # second row
            self.grid.add(arcade.gui.UILabel(text="Travel", align="right", font_size=20, multiline=False), column=0, row=1)
            self.fr_travel_input = UIInputText(width=400, height=40, border_color=arcade.uicolor.GRAY_CONCRETE, text="%d" % self.config.front_travel, font_name=DEFAULT_FONT, font_size=24, border_width=2)
            self.grid.add(self.fr_travel_input, column=1, row=1)
            self.rd_travel_input = UIInputText(width=400, height=40, border_color=arcade.uicolor.GRAY_CONCRETE, text="%d" % self.config.rear_travel, font_name=DEFAULT_FONT, font_size=24, border_width=2)
            self.grid.add(self.rd_travel_input, column=2, row=1)
            # third row
            self.grid.add(arcade.gui.UILabel(text="Sensor", align="right", font_size=20, multiline=False), column=0, row=2)
            avail = ["None"] + self.config.all_rf
            self.fr_drop = arcade.gui.UIDropdown(options=avail, default=self.config.front_selection, height=40, width=400)
            self.grid.add(self.fr_drop, column=1, row=2)
            self.rd_drop = arcade.gui.UIDropdown(options=avail, default=self.config.rear_selection, height=40, width=400)
            self.grid.add(self.rd_drop, column=2, row=2)

            widget_layout.add(self.grid)
            widget_layout.add(title_label_space)

            continue_button = arcade.gui.UIFlatButton(text="Continue", width=150)

            @continue_button.event("on_click")
            def on_click_continue_button(event):
                # check parameters
                res = self.config.check_parameters(self.fr_drop.value, self.fr_travel_input.text, self.rd_drop.value, self.rd_travel_input.text)
                if res == "":
                    main_view = AppView(self.config)
                    main_view.setup()
                    self.window.show_view(main_view)
                    return
                else:
                    self.manager.add(
                        UIMessageBox(width=300, height=200, title="Invalid parameters", buttons=("Ok",), message_text=res, ),
                        layer=UIManager.OVERLAY_LAYER,
                    )

            widget_layout.add(continue_button)
        # center main view
        self.anchor = self.manager.add(arcade.gui.UIAnchorLayout())
        self.anchor.add(anchor_x="center_x", anchor_y="top", child=widget_layout)
        # add version on the bottom right
        version_label = arcade.gui.UILabel(text="ylib : " + YAPI.GetAPIVersion(), align="center", font_size=12, multiline=False)
        self.anchor.add(anchor_x="right", anchor_y="bottom", child=version_label)

    def on_show_view(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)
        # Enable the UIManager when the view is showm.
        self.manager.enable()

    def on_hide_view(self):
        # Disable the UIManager when the view is hidden.
        self.manager.disable()

    def on_draw(self):
        """ Render the screen. """
        # Clear the screen
        self.clear()
        # Draw the manager.
        self.manager.draw()

    def on_key_release(self, key, modifiers):
        """Called whenever a key is released."""
        if key == arcade.key.ESCAPE:
            arcade.exit()


def main():
    config: ApplicationConfig = ApplicationConfig()
    config.setup()

    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    main_view = ConfigurationView(config)
    window.show_view(main_view)
    arcade.run()


if __name__ == "__main__":
    main()
