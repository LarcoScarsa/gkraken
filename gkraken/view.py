# This file is part of gkraken.
#
# Copyright (c) 2018 Roberto Leinardi
#
# gkraken is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gkraken is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gkraken.  If not, see <http://www.gnu.org/licenses/>.

import logging
from typing import Optional, Dict, Any, List, Tuple

from gkraken.util import get_data_path
from injector import inject, singleton
import gi
from gi.repository import Gtk
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

# AppIndicator3 may not be installed
from gkraken.interactor import SettingsInteractor

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
except (ImportError, ValueError):
    AppIndicator3 = None

from gkraken.conf import APP_PACKAGE_NAME, APP_ID, FAN_MIN_DUTY, FAN_MAX_DUTY, PUMP_MIN_DUTY, PUMP_MAX_DUTY, APP_NAME, \
    APP_VERSION, APP_SOURCE_URL
from gkraken.model import Status, SpeedProfile, ChannelType
from gkraken.presenter import Presenter, ViewInterface

LOG = logging.getLogger(__name__)
if AppIndicator3 is None:
    LOG.warning("AppIndicator3 is not installed. The app indicator will not be shown.")


@singleton
class View(ViewInterface):

    @inject
    def __init__(self,
                 presenter: Presenter,
                 builder: Gtk.Builder,
                 settings_interactor: SettingsInteractor,
                 ) -> None:
        LOG.debug('init View')
        self._presenter: Presenter = presenter
        self._presenter.view = self
        self._builder: Gtk.Builder = builder
        self._settings_interactor = settings_interactor
        self._init_widgets()

    def _init_widgets(self) -> None:
        self._app_indicator: Optional[AppIndicator3.Indicator] = None
        self._window = self._builder.get_object("application_window")
        self._settings_dialog: Gtk.Dialog = self._builder.get_object("settings_dialog")
        self._settings_dialog.connect("delete-event", self._hide_on_delete)
        self._app_indicator_menu = self._builder.get_object("app_indicator_menu")
        self._statusbar: Gtk.Statusbar = self._builder.get_object('statusbar')
        self._context = self._statusbar.get_context_id(APP_PACKAGE_NAME)
        self._cooling_fan_speed: Gtk.Label = self._builder.get_object('cooling_fan_speed')
        self._cooling_fan_rpm: Gtk.Label = self._builder.get_object('cooling_fan_rpm')
        self._cooling_liquid_temp: Gtk.Label = self._builder.get_object('cooling_liquid_temp')
        self._cooling_pump_rpm: Gtk.Label = self._builder.get_object('cooling_pump_rpm')
        self._firmware_version: Gtk.Label = self._builder.get_object('firmware_version')
        self._cooling_fan_combobox: Gtk.ComboBox = self._builder.get_object('cooling_fan_profile_combobox')
        self._cooling_fan_liststore: Gtk.ListStore = self._builder.get_object('cooling_fan_profile_liststore')
        self._cooling_pump_combobox: Gtk.ComboBox = self._builder.get_object('cooling_pump_profile_combobox')
        self._cooling_pump_liststore: Gtk.ListStore = self._builder.get_object('cooling_pump_profile_liststore')
        cooling_fan_scrolled_window: Gtk.ScrolledWindow = self._builder.get_object('cooling_fan_scrolled_window')
        cooling_pump_scrolled_window: Gtk.ScrolledWindow = self._builder.get_object('cooling_pump_scrolled_window')
        self._cooling_fan_apply_button: Gtk.Button = self._builder.get_object('cooling_fan_apply_button')
        self._cooling_pump_apply_button: Gtk.Button = self._builder.get_object('cooling_pump_apply_button')
        self._cooling_fan_edit_button: Gtk.Button = self._builder.get_object('cooling_fan_edit_button')
        self._cooling_pump_edit_button: Gtk.Button = self._builder.get_object('cooling_pump_edit_button')
        self._cooling_fixed_speed_popover: Gtk.Popover = self._builder.get_object('cooling_fixed_speed_popover')
        self._cooling_fixed_speed_adjustment: Gtk.Adjustment = \
            self._builder.get_object('cooling_fixed_speed_adjustment')
        self._cooling_fixed_speed_scale: Gtk.Scale = self._builder.get_object('cooling_fixed_speed_scale')
        self._about_dialog: Gtk.AboutDialog = self._builder.get_object("about_dialog")
        self._init_about_dialog()
        self._init_plot_charts(cooling_fan_scrolled_window, cooling_pump_scrolled_window)

    def _init_about_dialog(self) -> None:
        self._about_dialog.set_program_name(APP_NAME)
        self._about_dialog.set_version(APP_VERSION)
        self._about_dialog.set_website(APP_SOURCE_URL)
        self._about_dialog.connect("delete-event", self._hide_on_delete)

    @staticmethod
    def _hide_on_delete(widget: Gtk.Widget, *_: Any) -> Any:
        widget.hide()
        return widget.hide_on_delete()

    def show(self) -> None:
        self._presenter.on_start()
        self._init_app_indicator()

    def _init_app_indicator(self) -> None:
        if AppIndicator3:
            self._app_indicator = AppIndicator3.Indicator \
                .new(APP_ID, get_data_path('gkraken-symbolic.svg'), AppIndicator3.IndicatorCategory.HARDWARE)
            self._app_indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
            self._app_indicator.set_menu(self._app_indicator_menu)

    def toggle_window_visibility(self) -> None:
        if self._window.props.visible:
            self._window.hide()
        else:
            self._window.show()

    def show_add_speed_profile_dialog(self, channel: ChannelType) -> None:
        LOG.debug("view show_add_speed_profile_dialog %s", channel.name)

    def show_fixed_speed_profile_popover(self, profile: SpeedProfile) -> None:
        if profile.channel == ChannelType.FAN.value:
            self._cooling_fixed_speed_popover.set_relative_to(self._cooling_fan_edit_button)
            self._cooling_fixed_speed_adjustment.set_lower(FAN_MIN_DUTY)
            self._cooling_fixed_speed_adjustment.set_upper(FAN_MAX_DUTY)
        elif profile.channel == ChannelType.PUMP.value:
            self._cooling_fixed_speed_popover.set_relative_to(self._cooling_pump_edit_button)
            self._cooling_fixed_speed_adjustment.set_lower(PUMP_MIN_DUTY)
            self._cooling_fixed_speed_adjustment.set_upper(PUMP_MAX_DUTY)
        else:
            raise ValueError("Unknown channel: %s" % profile.channel)
        self._cooling_fixed_speed_scale.set_name(profile.channel)
        self._cooling_fixed_speed_adjustment.set_value(profile.steps[0].duty)
        self._cooling_fixed_speed_popover.show_all()

    def dismiss_and_get_value_fixed_speed_popover(self) -> Tuple[int, str]:
        self._cooling_fixed_speed_popover.hide()
        return self._cooling_fixed_speed_scale.get_value(), self._cooling_fixed_speed_scale.get_name()

    def show_about_dialog(self) -> None:
        self._about_dialog.show()

    def show_settings_dialog(self) -> None:
        self._settings_dialog.show()

    def set_statusbar_text(self, text: str) -> None:
        self._statusbar.remove_all(self._context)
        self._statusbar.push(self._context, text)

    def refresh_status(self, status: Optional[Status]) -> None:
        LOG.debug('view status')
        if status:
            self._cooling_fan_rpm.set_markup("<span size=\"xx-large\">%s</span> RPM" % status.fan_rpm)
            self._cooling_fan_speed.set_markup("<span size=\"xx-large\">%s</span> %%" %
                                               ('-' if status.fan_speed is None else status.fan_speed))
            self._cooling_liquid_temp.set_markup("<span size=\"xx-large\">%s</span> °C" % status.liquid_temperature)
            self._cooling_pump_rpm.set_markup("<span size=\"xx-large\">%s</span> RPM" % status.pump_rpm)
            self._firmware_version.set_label("firmware version %s" % status.firmware_version)
            if self._app_indicator:
                if self._settings_interactor.get_bool('settings_show_app_indicator'):
                    self._app_indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
                else:
                    self._app_indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
                if self._settings_interactor.get_bool('settings_app_indicator_show_water_temp'):
                    self._app_indicator.set_label("  %s°C" % status.liquid_temperature, "  XX°C")
                else:
                    self._app_indicator.set_label("", "")

    def refresh_chart(self, profile: SpeedProfile) -> None:
        if profile.channel == ChannelType.FAN.value:
            self._plot_fan_chart(self._get_speed_profile_data(profile))
        elif profile.channel == ChannelType.PUMP.value:
            self._plot_pump_chart(self._get_speed_profile_data(profile))
        else:
            raise ValueError("Unknown channel: %s" % profile.channel)

    @staticmethod
    def _get_speed_profile_data(profile: SpeedProfile) -> Dict[int, int]:
        data = {p.temperature: p.duty for p in profile.steps}
        if profile.single_step:
            data.update({60: profile.steps[0].duty})
        else:
            data.update({60: 100})
        return data

    def refresh_profile_combobox(self, channel: ChannelType, data: List[Tuple[int, str]],
                                 active: Optional[int]) -> None:
        if channel is ChannelType.FAN:
            for item in data:
                self._cooling_fan_liststore.append([item[0], item[1]])
            self._cooling_fan_combobox.set_model(self._cooling_fan_liststore)
            self._cooling_fan_combobox.set_sensitive(len(self._cooling_fan_liststore) > 1)
            if active is not None:
                self._cooling_fan_combobox.set_active(active)
        elif channel is ChannelType.PUMP:
            for item in data:
                self._cooling_pump_liststore.append([item[0], item[1]])
            self._cooling_pump_combobox.set_model(self._cooling_pump_liststore)
            self._cooling_pump_combobox.set_sensitive(len(self._cooling_pump_liststore) > 1)
            if active is not None:
                self._cooling_pump_combobox.set_active(active)
        else:
            raise ValueError("Unknown channel: %s" % channel.name)

    def set_apply_button_enabled(self, channel: ChannelType, enabled: bool) -> None:
        if channel is ChannelType.FAN:
            self._cooling_fan_apply_button.set_sensitive(enabled)
        elif channel is ChannelType.PUMP:
            self._cooling_pump_apply_button.set_sensitive(enabled)
        else:
            raise ValueError("Unknown channel: %s" % channel.name)

    def set_edit_button_enabled(self, channel: ChannelType, enabled: bool) -> None:
        if channel is ChannelType.FAN:
            self._cooling_fan_edit_button.set_sensitive(enabled)
        elif channel is ChannelType.PUMP:
            self._cooling_pump_edit_button.set_sensitive(enabled)
        else:
            raise ValueError("Unknown channel: %s" % channel.name)

    # pylint: disable=attribute-defined-outside-init
    def _init_plot_charts(self,
                          fan_scrolled_window: Gtk.ScrolledWindow,
                          pump_scrolled_window: Gtk.ScrolledWindow) -> None:
        self._fan_figure = Figure(figsize=(8, 6), dpi=72, facecolor='#00000000')
        self._fan_canvas = FigureCanvas(self._fan_figure)  # a Gtk.DrawingArea+
        self._fan_axis = self._fan_figure.add_subplot(111)
        self._fan_line, = self._init_plot_chart(
            fan_scrolled_window,
            self._fan_figure,
            self._fan_canvas,
            self._fan_axis
        )

        self._pump_figure = Figure(figsize=(8, 6), dpi=72, facecolor='#00000000')
        self._pump_canvas = FigureCanvas(self._pump_figure)  # a Gtk.DrawingArea+
        self._pump_axis = self._pump_figure.add_subplot(111)
        self._pump_line, = self._init_plot_chart(
            pump_scrolled_window,
            self._pump_figure,
            self._pump_canvas,
            self._pump_axis
        )

    def refresh_settings(self, settings: Dict[str, Any]) -> None:
        for key, value in settings.items():
            if isinstance(value, bool):
                switch: Gtk.Switch = self._builder.get_object(key + '_switch')
                switch.set_active(value)
            elif isinstance(value, int):
                spinbutton: Gtk.SpinButton = self._builder.get_object(key + '_spinbutton')
                spinbutton.set_value(value)

    @staticmethod
    def _init_plot_chart(fan_scrolled_window: Gtk.ScrolledWindow,
                         figure: Figure,
                         canvas: FigureCanvas,
                         axis: Axes) -> Any:
        axis.grid(True, linestyle=':')
        axis.margins(x=0, y=0.05)
        axis.set_facecolor('#00000000')
        axis.set_xlabel('Liquid temperature [°C]')
        axis.set_ylabel('Fan speed [%]')
        figure.subplots_adjust(top=1)
        canvas.set_size_request(400, 300)
        fan_scrolled_window.add_with_viewport(canvas)
        # Returns a tuple of line objects, thus the comma
        lines = axis.plot([], [], 'o-', linewidth=3.0, markersize=10, antialiased=True)
        axis.set_ybound(lower=0, upper=105)
        axis.set_xbound(20, 60)
        figure.canvas.draw()
        return lines

    def _plot_fan_chart(self, data: Dict[int, int]) -> None:
        temperature = list(data.keys())
        duty = list(data.values())
        self._fan_line.set_xdata(temperature)
        self._fan_line.set_ydata(duty)
        self._fan_canvas.draw()
        self._fan_canvas.flush_events()

    def _plot_pump_chart(self, data: Dict[int, int]) -> None:
        temperature = list(data.keys())
        duty = list(data.values())
        self._pump_line.set_xdata(temperature)
        self._pump_line.set_ydata(duty)
        self._pump_canvas.draw()
        self._pump_canvas.flush_events()
