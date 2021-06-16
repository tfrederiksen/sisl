from abc import ABC, abstractmethod

from ...plot import MultiplePlot, SubPlots, Animation

class Backend(ABC):

    @abstractmethod
    def clear(self):
        """Clears the figure so that we can draw again."""

class MultiplePlotBackend(Backend):

    @abstractmethod
    def draw(self, drawer_info, childs):
        """Recieves the child plots and is responsible for drawing all of them in the same canvas"""

class SubPlotsBackend(Backend):

    @abstractmethod
    def draw_subplots(self, drawer_info, rows, cols, childs, **make_subplots_kwargs):
        """Draws the subplots layout

        It must use `rows` and `cols`, and draw the childs row by row.
        """

class AnimationBackend(Backend):

    @abstractmethod
    def draw(self, drawer_info, childs, get_frame_names):
        """Generates an animation out of the child plots.
        """

MultiplePlot._backends.register_template(MultiplePlotBackend)
SubPlots._backends.register_template(SubPlotsBackend)
Animation._backends.register_template(AnimationBackend)