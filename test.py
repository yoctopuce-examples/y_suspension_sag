"""
Platformer Game

python -m arcade.examples.platform_tutorial.02_draw_sprites
"""
import arcade
from yoctopuce import yocto_api
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
            #print("update value :"+self.get_sag_text())

    def get_sag_text(self):
        return "SAG = %d%% (%dmm)" % (self.sag, self.mm_sag)


class Status:
    def __init__(self, fr_hwid, fr_travel, rd_hwid, rd_travel):
        self.front = SuspStatus(fr_hwid, fr_travel)
        self.rear = SuspStatus(rd_hwid, rd_travel)

    def reset(self):
        self.front.reset()
        self.rear.reset()


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


def main():
    """Main function"""
    url = "usb"
    errmsg = YRefParam()
    print("connecting to %s" % url)
    if YAPI.RegisterHub(url, errmsg) != YAPI.SUCCESS:
        print("USB error: " + errmsg.value)
        return
    print("connected")
    target = "front"
    rf = YRangeFinder.FindRangeFinder(target + ".rangeFinder1")
    if not rf.isOnline():
        print(f"{target} not connected")
        return
    print("use sensor %s" % rf.get_serialNumber())
    # Use high-accuracy mode for better precision
    rf.set_rangeFinderMode(YRangeFinder.RANGEFINDERMODE_HIGH_ACCURACY)

    # Build the parameter object, passing the GUI reference so callbacks can update it
    status = Status(rf.get_hardwareId(), 160, "inv", 65)
    rf.set_userData(status.front)
    rf.registerValueCallback(valueCallback)
    #YAPI.Sleep(5000)

    window = GameView(status)
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
