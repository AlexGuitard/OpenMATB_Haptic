import pyglet.image

from core.widgets.abstractwidget import *

class Tactons(AbstractWidget):

    def __init__(self, name, container, win):
        super().__init__(name, container, win)
        self.image = pyglet.image.load("../../includes/img/stimulus_sheet.png")
        self.sprite = pyglet.sprite.Sprite(self.image)
