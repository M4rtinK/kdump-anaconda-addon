# Kdump anaconda configuration
#
# Copyright (C) 2014 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): David Shea <dshea@redhat.com>
#

"""Kdump anaconda GUI configuration"""

from gi.repository import Gtk

from pyanaconda.ui.gui.categories.system import SystemCategory
from pyanaconda.ui.gui.spokes import NormalSpoke
from pyanaconda.ui.gui.utils import fancy_set_sensitive

from com_redhat_kdump.i18n import _, N_
from com_redhat_kdump.constants import CONFIG_FILE
from com_redhat_kdump.common import getReservedMemory, getTotalMemory, getMemoryBounds, getOS

__all__ = ["KdumpSpoke"]

class KdumpSpoke(NormalSpoke):
    """Kdump configuration spoke"""

    builderObjects = ["KdumpWindow", "advancedConfigBuffer"]
    mainWidgetName = "KdumpWindow"
    uiFile = "kdump.glade"

    icon = "computer-fail-symbolic"
    title = N_("_KDUMP")
    category = SystemCategory
    OS = "redhat"
    def __init__(self, data, storage, payload, instclass):
        KdumpSpoke.OS = getOS()
        if KdumpSpoke.OS == "fedora":
            KdumpSpoke.uiFile = "fedora.glade"
        NormalSpoke.__init__(self, data, storage, payload, instclass)
        self._reserveMem = 0

    def initialize(self):
        NormalSpoke.initialize(self)
        self._enableButton = self.builder.get_object("enableKdumpCheck")
        KdumpSpoke.OS = getOS()
        if KdumpSpoke.OS == "redhat":
            self._reservationTypeLabel = self.builder.get_object("reservationTypeLabel")
            self._autoButton = self.builder.get_object("autoButton")
            self._manualButton = self.builder.get_object("manualButton")

        self._currentlyReservedLabel = self.builder.get_object("currentlyReservedLabel")
        self._currentlyReservedMB = self.builder.get_object("currentlyReservedMB")
        self._toBeReservedLabel = self.builder.get_object("toBeReservedLabel")
        self._toBeReservedSpin = self.builder.get_object("toBeReservedSpin")
        self._totalMemLabel = self.builder.get_object("totalMemLabel")
        self._totalMemMB = self.builder.get_object("totalMemMB")
        self._usableMemLabel = self.builder.get_object("usableMemLabel")
        self._usableMemMB = self.builder.get_object("usableMemMB")
        #self._config_buffer = self.builder.get_object("advancedConfigBuffer")

        # Set an initial value and adjustment on the spin button
        lower, upper, step = getMemoryBounds()
        adjustment = Gtk.Adjustment(lower, lower, upper, step, step, 0)
        self._toBeReservedSpin.set_adjustment(adjustment)
        self._toBeReservedSpin.set_value(lower)
        # Initialize the advanced config area with the contents of /etc/kdump.conf
        #try:
        #    with open(CONFIG_FILE, "r") as fobj:
        #        self._config_buffer.set_text(fobj.read())
        #except IOError:
        #    self._config_buffer.set_text("")

    def refresh(self):
        # If a reserve amount is requested, set it in the spin button
        if self.data.addons.com_redhat_kdump.reserveMB != "auto":
            # Strip the trailing 'M'
            reserveMB = self.data.addons.com_redhat_kdump.reserveMB
            if reserveMB and reserveMB[-1] == 'M':
                reserveMB = reserveMB[:-1]
            if reserveMB:
                self._toBeReservedSpin.set_value(int(reserveMB))

        # Set the various labels. Use the spin button signal handler to set the
        # usable memory label once the other two have been set.
        self._currentlyReservedMB.set_text("%d" % getReservedMemory())
        self._totalMemMB.set_text("%d" % getTotalMemory())
        self._toBeReservedSpin.emit("value-changed")

        # Set the states on the toggle buttons and let the signal handlers set
        # the sensitivities on the related widgets. Set the radio button first,
        # since the radio buttons' bailiwick is a subset of that of the
        # enable/disable checkbox.
        if KdumpSpoke.OS == "redhat":
            if self.data.addons.com_redhat_kdump.reserveMB == "auto":
                self._autoButton.set_active(True)
                self._manualButton.set_active(False)
            else:
                self._autoButton.set_active(False)
                self._manualButton.set_active(True)

        if self.data.addons.com_redhat_kdump.enabled:
            self._enableButton.set_active(True)
        else:
            self._enableButton.set_active(False)

        # Force a toggled signal on the button in case it's state has not changed
        self._enableButton.emit("toggled")

        # Fill the advanced configuration area with the current state
        #start, end = self._config_buffer.get_bounds()
        #self.data.addons.com_redhat_kdump.content = self._config_buffer.get_text(start, end, True)

    def apply(self):
        # Copy the GUI state into the AddonData object
        self.data.addons.com_redhat_kdump.enabled = self._enableButton.get_active()

        if KdumpSpoke.OS == "redhat" and self._autoButton.get_active():
            reserveMem = "auto"
        else:
            reserveMem = "%dM" % self._toBeReservedSpin.get_value_as_int()

        self.data.addons.com_redhat_kdump.reserveMB = reserveMem

        #start, end = self._config_buffer.get_bounds()
        #self.data.addons.com_redhat_kdump.content = self._config_buffer.get_text(start, end, True)

    @property
    def ready(self):
        return True

    @property
    def completed(self):
        # Always treat as completed
        return True

    @property
    def mandatory(self):
        return False

    @property
    def status(self):
        if self.data.addons.com_redhat_kdump.enabled:
            state = _("Kdump is enabled")
        else:
            state = _("Kdump is disabled")

        return state

    # SIGNAL HANDLERS

    def on_enable_kdump_toggled(self, checkbutton, user_data=None):
        status = checkbutton.get_active()

        # If disabling, set everything to insensitve. Otherwise, only set the radio
        # button and currently reserved widgets to sensitive and then fake a
        # toggle event on the radio button to set the state on the reserve
        # amount spin button and total/usable mem display.
        self._currentlyReservedLabel.set_sensitive(status)
        self._currentlyReservedMB.set_sensitive(status)
        if KdumpSpoke.OS == "redhat":
            self._autoButton.set_sensitive(status)
            self._manualButton.set_sensitive(status)
            self._reservationTypeLabel.set_sensitive(status)

        if not status:
            fancy_set_sensitive(self._toBeReservedSpin, status)
            self._totalMemLabel.set_sensitive(status)
            self._totalMemMB.set_sensitive(status)
            self._usableMemLabel.set_sensitive(status)
            self._usableMemMB.set_sensitive(status)
        elif KdumpSpoke.OS == "redhat":
            self._autoButton.emit("toggled")
        else:
            fancy_set_sensitive(self._toBeReservedSpin, True)
            self._totalMemLabel.set_sensitive(True)
            self._totalMemMB.set_sensitive(True)
            self._usableMemLabel.set_sensitive(True)
            self._usableMemMB.set_sensitive(True)

    def on_reservation_toggled(self, radiobutton, user_data=None):
        status = self._manualButton.get_active()

        # If setting to auto, disable the manual config spinner and
        # the total/usable memory labels
        fancy_set_sensitive(self._toBeReservedSpin, status)
        self._totalMemLabel.set_sensitive(status)
        self._totalMemMB.set_sensitive(status)
        self._usableMemLabel.set_sensitive(status)
        self._usableMemMB.set_sensitive(status)

    def on_reserved_value_changed(self, spinbutton, user_data=None):
        reserveMem = spinbutton.get_value_as_int()
        totalMemText = self._totalMemMB.get_text()

        # If no total memory is available yet, do nothing
        if totalMemText:
            totalMem = int(self._totalMemMB.get_text())
            self._usableMemMB.set_text("%d" % (totalMem - reserveMem))
