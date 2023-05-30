from core.container import Container
from core.widgets.tactons import Tactons
from plugins.abstract import AbstractPlugin


class Tactonsinfo(AbstractPlugin):

    def __init__(self, window, taskplacement='topleft', taskupdatetime=10000):
        super().__init__(window, taskplacement, taskupdatetime)

    def create_widgets(self):
        super().create_widgets()
        tactons_w = self.task_container.w
        tactons_b = self.task_container.b
        tactons_h = self.task_container.h
        tactons_l = self.task_container.l

        tactons_container = Container('tactonsInfo', tactons_l, tactons_b, tactons_w, tactons_h)
        self.add_widget('tactonsInfo', Tactons, tactons_container)
