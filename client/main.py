from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.stacklayout import StackLayout
from kivy.uix.image import Image

class IconImage(Image):
    pass

class ChampionImage(Image):
    pass

class ChampionAdviceImage(Image):
    pass

class RowLayout(StackLayout):
    pass

class WelcomeWindow(Screen):
    pass

class ClashWindow(Screen):
    pass

class WindowManager(ScreenManager):
    pass


class MoonCakerApp(App):
    def build(self):
        return 

if __name__ == "__main__":
    MoonCakerApp().run()