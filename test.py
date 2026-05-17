"""
Platformer Game

python -m arcade.examples.platform_tutorial.02_draw_sprites
"""
import arcade
import arcade.gui
from yoctopuce.yocto_api import YRefParam, YAPI
from yoctopuce.yocto_rangefinder import YRangeFinder

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Yoctopuce Sag meter"


class SuspStatus:
    def __init__(self, hwid, travel):
        self.hwid = hwid
        self.travel = int(travel)
        self.max_val = 0
        self.sag = 0
        self.mm_sag = 0
        self.reset()

    def reset(self):
        self.max_val = 0
        self.sag = 0
        self.mm_sag = 0

    def update_value(self, new_val):
        # Update max value in case the app was started with the suspension compressed
        if new_val > self.max_val:
            self.max_val = new_val

        mm_sag = self.max_val - new_val
        sag = mm_sag * 100 // self.travel

        if sag != self.sag or mm_sag != self.mm_sag:
            self.sag = sag
            self.mm_sag = mm_sag
            # print("update value :"+self.get_sag_text())

    def get_sag_text(self):
        return "SAG = %d%% (%dmm)" % (self.sag, self.mm_sag)


class Status:
    def __init__(self, fr_hwid, fr_travel, rd_hwid, rd_travel):
        self.front = SuspStatus(fr_hwid, fr_travel)
        self.rear = SuspStatus(rd_hwid, rd_travel)

    def reset(self):
        self.front.reset()
        self.rear.reset()


class ApplicationConfig:
    def __init__(self):
        self.url = "usb"
        self.error = None
        self.all_rf = []
        self.front_rf = None
        self.rear_rf = None

    def setup(self):
        errmsg = YRefParam()
        if YAPI.RegisterHub(self.url, errmsg) != YAPI.SUCCESS:
            print("Unable to register hub %s: %s" % (self.url, errmsg.value))
            # if usb failed it's probably because a VirtualHub is running. Try to use the VirtualHub
            self.url = "127.0.0.1"
            if YAPI.RegisterHub(self.url, errmsg) != YAPI.SUCCESS:
                print("Unable to register hub %s: %s" % (self.url, errmsg.value))
                self.error = errmsg.value
                return

        rf = YRangeFinder.FirstRangeFinder()
        while rf is not None:
            self.all_rf.append(rf.get_hardwareId())
            name = rf.get_logicalName()
            if name == "front":
                self.front_rf = rf.get_hardwareId()
            elif name == "rear":
                self.rear_rf = rf.get_hardwareId()
            rf = rf.nextRangeFinder()

    def check_config(self):
        if self.error is not None:
            return self.error
        if len(self.all_rf) == 0:
            return "No Yocto-RangeFinder detected on " + self.url

        return None


class GameView(arcade.Window):
    """
    Main application class.
    """

    def __init__(self, status):
        # Call the parent class and set up the window
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)

        # Variable to hold our texture for our player
        self.bike_texture = None

        # Separate variable that holds the player sprite
        self.bike_sprite = None
        self.front_sag_text = None
        self.rear_sag_text = None

        # SpriteList for our player
        self.fixed_spriteList = None

        self.camera = None
        self.status = status

    def setup(self):
        """Set up the game here. Call this function to restart the game."""
        # Variable to hold our texture for our player
        self.bike_texture = arcade.load_texture(
            "lane.png"
        )

        # Separate variable that holds the player sprite
        self.bike_sprite = arcade.Sprite(self.bike_texture)
        self.bike_sprite.center_x = self.width // 2
        self.bike_sprite.center_y = self.height // 2
        self.bike_sprite.scale = 0.5

        self.fixed_spriteList = arcade.SpriteList()
        self.fixed_spriteList.append(self.bike_sprite)
        self.camera = arcade.Camera2D()
        self.background_color = arcade.csscolor.GREY
        self.status.reset()
        self.front_sag_text = arcade.Text(self.status.front.get_sag_text(), x=WINDOW_WIDTH - 200, y=5)
        self.rear_sag_text = arcade.Text(self.status.rear.get_sag_text(), x=0, y=5)

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

    def on_update(self, delta_time):
        YAPI.HandleEvents()
        self.front_sag_text.text = self.status.front.get_sag_text()

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""
        pass

    def on_key_release(self, key, modifiers):
        """Called whenever a key is released."""
        if key == arcade.key.ESCAPE:
            self.setup()
            return
        pass


def valueCallback(rf, value):
    """Called by Yoctopuce SDK each time a new range measurement arrives."""
    p = rf.get_userData()
    p.update_value(int(value))


def start_yoctopuce_lib(config):
    window = GameView(status)
    window.setup()
    arcade.run()


class MainView(arcade.View):
    """ Main application class."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.manager = arcade.gui.UIManager()
        widget_layout = arcade.gui.UIBoxLayout(align="center", space_between=10)

        title_label = arcade.gui.UILabel(text="Yoctopuce SAG meter", align="center", font_size=20, multiline=False)
        title_label_space = arcade.gui.UISpace(height=30, color=arcade.color.DARK_BLUE_GRAY)
        widget_layout.add(title_label)
        widget_layout.add(title_label_space)

        error = config.check_config()
        if error is not None:
            error_label = arcade.gui.UILabel(text="Error: " + error, align="center", font_size=15,
                                             multiline=False)
            widget_layout.add(error_label)
            widget_layout.add(title_label_space)

            exit_button = arcade.gui.UIFlatButton(text="Exit", width=150)
            @exit_button.event("on_click")
            def on_click_exit_button(event):
                arcade.exit()
            widget_layout.add(exit_button)
        else:
            # todo continue next
            continue_button = arcade.gui.UIFlatButton(text="Continue", width=150)
            widget_layout.add(continue_button)

        self.anchor = self.manager.add(arcade.gui.UIAnchorLayout())
        self.anchor.add(
            anchor_x="center_x",
            anchor_y="center_y",
            child=widget_layout)
        version_label = arcade.gui.UILabel(text="ylib : " + YAPI.GetAPIVersion(), align="center", font_size=12,
                                           multiline=False)
        self.anchor.add(
            anchor_x="right",
            anchor_y="bottom",
            child=version_label)

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


def main():
    config = ApplicationConfig()
    config.setup()

    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, resizable=True)
    main_view = MainView(config)
    window.show_view(main_view)
    arcade.run()


if __name__ == "__main__":
    main()
