import os

import pyglet.image

from core.widgets.abstractwidget import *


class Tactons(AbstractWidget):

    def __init__(self, name, container, win):
        super().__init__(name, container, win)
        script_dir = os.path.dirname(__file__)
        path = os.path.join(script_dir, '../../includes/img/stimulus_sheet.png')
        self.image = pyglet.image.load(path)
        self.sprite = pyglet.sprite.Sprite(self.image)

    def on_draw(self):
        self.sprite.draw()
