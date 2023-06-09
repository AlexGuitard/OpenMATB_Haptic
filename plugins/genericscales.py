# Copyright 2023, by Julien Cegarra & Benoît Valéry. All rights reserved.
# Institut National Universitaire Champollion (Albi, France).
# License : CeCILL, version 2.1 (see the LICENSE file)
import pyglet

from plugins.abstract import BlockingPlugin
from core.widgets import Simpletext, Slider, Frame
from core.constants import FONT_SIZES as F, PATHS as P, COLORS as C
from re import match as regex_match


class Genericscales(BlockingPlugin):
    def __init__(self, window):
        super().__init__(window)

        self.folder = P['QUESTIONNAIRES']
        new_par = dict(filename=None, pointsize=0, maxdurationsec=0, 
                       response=dict(text=_('Please wait'), key='W'),
                       allowkeypress=True)
        self.sliders = dict()
        self.parameters.update(new_par)
        
        self.ignore_empty_lines = True
        
        self.regex_scale_pattern = r'(.*);(.*)/(.*);(\d*)/(\d*)/(\d*)'
        self.question_height_ratio = 0.1  # question + response slider
        self.question_interspace = 0.05  # Space to leave between two questions
        self.top_to_top = self.question_interspace + self.question_height_ratio

        self.current_slider = None
    
    def make_slide_graphs(self):
        super().make_slide_graphs()
            
        scales = self.current_slide.split('\n')
        scale_list = [s.strip() for s in scales if len(s.strip()) > 0]
        if len(scale_list) == 0:
            return

        all_scales_container = self.container.get_reduced(1, self.top_to_top*(len(scale_list)))
        
        height_in_prop = (self.question_height_ratio * self.container.h)/all_scales_container.h
        for l, scale in enumerate(scale_list):

            # Define the scale main container (question + response slider)            
            scale_container = all_scales_container.reduce_and_translate(
                height=height_in_prop, y=1-(1/(len(scale_list)))*l)
            
            text_container = scale_container.reduce_and_translate(1, 0.4, 0, 1)
            slider_container = scale_container.reduce_and_translate(1, 0.6, 0, 0)
            
            if regex_match(self.regex_scale_pattern, scale):
                title, label, limit_labels, values = scale.strip().split(';')
                label_min, label_max = limit_labels.split('/')
                value_min, value_max, value_default = [int(v) for v in values.split('/')]
                
                self.add_widget(f'label_{l+1}', Simpletext, container=text_container,
                                text=label, wrap_width=0.8, font_size=F['MEDIUM'], 
                                draw_order=self.m_draw)
            
                self.sliders[f'slider_{l+1}'] = self.add_widget(f'slider_{l+1}', Slider, 
                                container=slider_container, parent=self,
                                title=title, label_min=label_min, label_max=label_max,
                                value_min=value_min, value_max=value_max, 
                                value_default=value_default, rank=l, draw_order=self.m_draw+3)
                if l == 0:
                    self.current_slider = self.sliders['slider_1']
                    self.current_slider.set_auto_focus()
    
    def stop(self):
        for slider_name, slider_widget in self.sliders.items():
            self.log_performance(slider_widget.get_title(), slider_widget.get_value())
        self.logger.log_manual_entry("end of block with nasatlx", 'end_nasatlx')
        self.logger.write_on_disk()
        self.logger.create_new_log_file()
        self.send_local_message(False)
        super().stop()

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.DOWN and self.current_slider is not None:
            self.focus_next_slider()
        elif symbol == pyglet.window.key.UP and self.current_slider is not None:
            self.focus_previous_slider()

    def focus_next_slider(self):
        if not self.is_paused():
            current_rank = self.current_slider.rank
            next_rank = (current_rank + 1) % len(self.sliders)

            next_slider_name = f'slider_{next_rank + 1}'
            next_slider = self.sliders.get(next_slider_name)
            if next_slider is not None:
                self.current_slider.remove_focus()
                self.current_slider = next_slider
                self.current_slider.set_auto_focus()

    def focus_previous_slider(self):
        if not self.is_paused():
            current_rank = self.current_slider.rank
            previous_rank = (current_rank - 1) % len(self.sliders)

            previous_slider_name = f'slider_{previous_rank + 1}'
            previous_slider = self.sliders.get(previous_slider_name)
            if previous_slider is not None:
                self.current_slider.remove_focus()
                self.current_slider = previous_slider
                self.current_slider.set_auto_focus()

