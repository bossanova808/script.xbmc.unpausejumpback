"""
Unpause Jumpback Add-on for Kodi

This add-on provides functionality to automatically jump back a configurable amount 
when resuming playback after a pause.

The add-on supports multiple jumpback modes:
- Jump back on resume (default behavior)
- Jump back on pause (for low-power systems)
- Jump back on playback start from resume points
- Configurable jumpback after fast-forward/rewind operations

"""

import xbmc
import time
from typing import Optional
from bossanova808.logger import Logger
from bossanova808.utilities import get_setting, get_setting_as_bool

player: Optional['MyPlayer'] = None
kodi_monitor: Optional['MyMonitor'] = None


def run():
    """
    Main entry point for the add-on.

    Initializes the logger, creates player and monitor instances, and runs
    the main monitoring loop. Handles cleanup on exit or abort signals.

    The function will continue running until Kodi signals an abort request
    or an exception occurs.
    """
    global player
    global kodi_monitor

    Logger.start()
    try:
        kodi_monitor = MyMonitor()
        player = MyPlayer()
        while not kodi_monitor.abortRequested():
            if kodi_monitor.waitForAbort(1):
                break
    finally:
        Logger.stop()
        player = None
        kodi_monitor = None


class MyPlayer(xbmc.Player):
    """
    Custom Kodi Player class that handles unpause jumpback functionality.

    This class extends xbmc.Player to provide automatic jumpback functionality
    when playback is resumed after being paused, fast-forwarded, or rewound.

    The class supports multiple jumpback modes:
    - Jump back on resume: Seeks backward when playback resumes after pause
    - Jump back on pause: Seeks backward during the pause (for low-power systems)
    - Jump back on playback start: Seeks backward when starting from resume points
    - Variable jumpback after fast-forward/rewind at different speeds

    Exclusion settings allow skipping jumpback for specific content types or paths.
    """

    def __init__(self):
        """
        Initialize the MyPlayer instance.

        Sets up all configuration variables and loads settings from Kodi's
        add-on configuration.
        """
        xbmc.Player.__init__(self)
        Logger.debug('MyPlayer - init')

        # Jumpback behavior settings
        self.jump_back_on_resume = 0
        self.jump_back_on_playback_started = 0
        self.paused_time = 0
        self.jump_back_secs_after_pause = 0
        self.jump_back_secs_after_resume = 0
        self.last_playback_speed = 0
        self.wait_for_jumpback = 0

        # Fast-forward jumpback settings
        self.jump_back_secs_after_fwd_x2 = 0
        self.jump_back_secs_after_fwd_x4 = 0
        self.jump_back_secs_after_fwd_x8 = 0
        self.jump_back_secs_after_fwd_x16 = 0
        self.jump_back_secs_after_fwd_x32 = 0

        # Rewind jumpback settings
        self.jump_back_secs_after_rwd_x2 = 0
        self.jump_back_secs_after_rwd_x4 = 0
        self.jump_back_secs_after_rwd_x8 = 0
        self.jump_back_secs_after_rwd_x16 = 0
        self.jump_back_secs_after_rwd_x32 = 0

        # Exclusion settings
        self.exclude_live_tv = True
        self.exclude_http = True
        self.excluded_path_1_enabled = None
        self.excluded_path_2_enabled = None
        self.excluded_path_3_enabled = None
        self.excluded_path_1 = None
        self.excluded_path_2 = None
        self.excluded_path_3 = None

        self.load_settings()

    def load_settings(self):
        """
        Load and cache settings from Kodi's add-on settings.

        Retrieves all jumpback configuration options, exclusion settings,
        and timing parameters from the add-on settings and caches them
        for performance during playback events.

        Logs the current jumpback mode after loading settings.
        """
        self.jump_back_on_resume = get_setting_as_bool('jumpbackonresume')
        self.jump_back_on_playback_started = get_setting_as_bool('jumpbackonplaybackstarted')
        self.jump_back_secs_after_pause = int(float(get_setting("jumpbacksecs")))
        self.jump_back_secs_after_fwd_x2 = int(float(get_setting("jumpbacksecsfwdx2")))
        self.jump_back_secs_after_fwd_x4 = int(float(get_setting("jumpbacksecsfwdx4")))
        self.jump_back_secs_after_fwd_x8 = int(float(get_setting("jumpbacksecsfwdx8")))
        self.jump_back_secs_after_fwd_x16 = int(float(get_setting("jumpbacksecsfwdx16")))
        self.jump_back_secs_after_fwd_x32 = int(float(get_setting("jumpbacksecsfwdx32")))
        self.jump_back_secs_after_rwd_x2 = int(float(get_setting("jumpbacksecsrwdx2")))
        self.jump_back_secs_after_rwd_x4 = int(float(get_setting("jumpbacksecsrwdx4")))
        self.jump_back_secs_after_rwd_x8 = int(float(get_setting("jumpbacksecsrwdx8")))
        self.jump_back_secs_after_rwd_x16 = int(float(get_setting("jumpbacksecsrwdx16")))
        self.jump_back_secs_after_rwd_x32 = int(float(get_setting("jumpbacksecsrwdx32")))
        self.wait_for_jumpback = int(float(get_setting("waitforjumpback")))
        self.exclude_live_tv = get_setting_as_bool('ExcludeLiveTV')
        self.exclude_http = get_setting_as_bool('ExcludeHTTP')
        self.excluded_path_1_enabled = get_setting_as_bool('ExcludePathOption')
        self.excluded_path_2_enabled = get_setting_as_bool('ExcludePathOption2')
        self.excluded_path_3_enabled = get_setting_as_bool('ExcludePathOption3')
        self.excluded_path_1 = get_setting('ExcludePath')
        self.excluded_path_2 = get_setting('ExcludePath2')
        self.excluded_path_3 = get_setting('ExcludePath3')

        if self.jump_back_on_resume:
            Logger.info(f'Settings loaded, jump back set to: On Resume with a jump back of {self.jump_back_secs_after_pause} seconds')
        else:
            Logger.info(f'Settings loaded, jump back set to: On Pause with a jump back of {self.jump_back_secs_after_pause} seconds')

    def is_excluded(self, full_path):
        """
        Check if the given file path should be excluded from jumpback functionality.

        Tests the provided path against configured exclusion rules including:
        - Live TV streams (pvr:// protocol)
        - HTTP/HTTPS streams
        - Up to 3 custom excluded paths

        Args:
            full_path (str): The full file path or URL to check for exclusion

        Returns:
            bool: True if the path should be excluded from jumpback, False otherwise
        """
        if not full_path:
            return True

        Logger.info(f"Checking exclusion for: '{full_path}'.")

        if (full_path.find("pvr://") > -1) and self.exclude_live_tv:
            Logger.info("Video is playing via Live TV, which is set as an excluded location.")
            return True

        if ((full_path.find("http://") > -1) or (full_path.find("https://") > -1)) and self.exclude_http:
            Logger.info("Video is playing via HTTP source, which is set as an excluded location.")
            return True

        if self.excluded_path_1 and self.excluded_path_1_enabled:
            if full_path.find(self.excluded_path_1) > -1:
                Logger.info(f"Video is playing from '{self.excluded_path_1}', which is set as excluded path 1.")
                return True

        if self.excluded_path_2 and self.excluded_path_2_enabled:
            if full_path.find(self.excluded_path_2) > -1:
                Logger.info(f"Video is playing from '{self.excluded_path_2}', which is set as excluded path 2.")
                return True

        if self.excluded_path_3 and self.excluded_path_3_enabled:
            if full_path.find(self.excluded_path_3) > -1:
                Logger.info(f"Video is playing from '{self.excluded_path_3}', which is set as excluded path 3.")
                return True

        Logger.info(f"Not excluded: '{full_path}'")
        return False

    def onPlayBackResumed(self):
        """
        Handle playback resume events (default jumpback mode).

        Called when playback is resumed after being paused. This is the default
        behavior where the pause position remains where the user actually paused,
        which is usually the desired behavior.

        When jump_back_on_resume is enabled:
        - Checks exclusion settings for the current file
        - Performs jumpback if conditions are met (sufficient pause time, etc.)
        - Resets the paused_time tracking variable

        When jump_back_on_resume is disabled:
        - Cancels any pending alarm-based jumpback operations
        """
        Logger.info(f'onPlayBackResumed with jump_back_on_resume: {self.jump_back_on_resume}')

        if self.jump_back_on_resume:

            if self.paused_time > 0:
                Logger.info(f'Was paused for {int(time.time() - self.paused_time)} seconds.')

            # Check for exclusion
            try:
                _filename = self.getPlayingFile()
            except RuntimeError:
                Logger.info('No file is playing, could not getPlayingFile(), stopping UnpauseJumpBack')
                xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')
                return

            if self.is_excluded(_filename):
                Logger.info(f"Ignored because '{_filename}' is in exclusion settings.")
                return

            else:
                # Handle jump back after pause
                if self.jump_back_secs_after_pause != 0 \
                        and self.isPlayingVideo() \
                        and self.getTime() > self.jump_back_secs_after_pause \
                        and self.paused_time > 0 \
                        and (time.time() - self.paused_time) > self.wait_for_jumpback:
                    resume_time = self.getTime() - self.jump_back_secs_after_pause
                    self.seekTime(resume_time)
                    Logger.info(f'Resumed, with {int(self.jump_back_secs_after_pause)}s jump back')

                self.paused_time = 0

        # If we're not jumping back on resume, cancel any alarm set for manual resume
        else:
            Logger.info('Cancelling alarm - playback either resumed or stopped by the user.')
            xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')

    def onPlayBackPaused(self):
        """
        Handle playback pause events (alternative jumpback mode for low-power systems).

        Called when playback is paused. Records the pause time and optionally
        sets up alarm-based jumpback during the pause period.

        For low-power systems, the add-on can be configured to perform the jumpback
        during the pause period, which prevents jankiness on resume but has the
        disadvantage that the paused image also jumps back.

        Checks exclusion settings and sets up delayed jumpback via Kodi's AlarmClock
        if jump_back_on_resume is disabled.
        """
        # Record when the pause was done
        self.paused_time = time.time()
        Logger.info(f'onPlayBackPaused. Time: {self.paused_time}')

        try:
            _filename = self.getPlayingFile()
        except RuntimeError:
            Logger.info('No file is playing, could not getPlayingFile(), stopping UnpauseJumpBack')
            xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')
            return

        if self.is_excluded(_filename):
            Logger.info(f'Playback paused - ignoring because [{_filename}] is in exclusion settings.')
            return

        # For low power systems, perform jumpback during pause period
        # Prevents janky resume experience but paused image also jumps back
        if not self.jump_back_on_resume and self.isPlayingVideo() and 0 < self.jump_back_secs_after_pause < self.getTime():
            jump_back_point = self.getTime() - self.jump_back_secs_after_pause
            Logger.info(f'Playback paused - jumping back {self.jump_back_secs_after_pause}s to: {int(jump_back_point)} seconds')
            xbmc.executebuiltin(
                    f'AlarmClock(JumpbackPaused, Seek(-{self.jump_back_secs_after_pause}), 0:{self.wait_for_jumpback}, silent)')

    def onAVStarted(self):
        """
        Handle audio/video start events.

        Called when audio/video playback starts. If jump_back_on_playback_started
        is enabled, this method will perform a jumpback when playback begins from
        a resume point (not from the beginning).

        This is useful for situations where users want to jump back a bit when
        resuming a previously watched video to catch up on context.

        Checks exclusion settings and only performs jumpback if the current
        playback position is greater than zero (indicating a resume operation).
        """
        Logger.info(f'onAVStarted.')

        # If configured to jump back when playback starts from a resume point
        if self.jump_back_on_playback_started:

            try:
                current_time = self.getTime()
            except RuntimeError:
                Logger.info('No file is playing, could not getTime(), stopping UnpauseJumpBack')
                xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')
                return

            Logger.info(f'Current playback time is {current_time}')

            # Check for exclusion
            try:
                _filename = self.getPlayingFile()
            except RuntimeError:
                Logger.info('No file is playing, could not getPlayingFile(), stopping UnpauseJumpBack')
                xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')
                return

            if self.is_excluded(_filename):
                Logger.info(f"Ignored because '{_filename}' is in exclusion settings.")
                return
            else:
                if current_time > 0 and 0 < self.jump_back_secs_after_pause < current_time:
                    resume_time = current_time - self.jump_back_secs_after_pause
                    Logger.info(f"Resuming playback from saved time: {int(current_time)} "
                                f"with jump back seconds: {self.jump_back_secs_after_pause}, "
                                f"thus resume time: {int(resume_time)}")
                    self.seekTime(resume_time)

    def onPlayBackSpeedChanged(self, speed):
        """
        Handle playback speed change events.

        Called when the playback speed changes (e.g., fast-forward, rewind, or
        return to normal speed). When returning to normal speed (speed == 1)
        from fast-forward or rewind, performs configurable jumpback operations.

        Supports different jumpback amounts for different fast-forward/rewind speeds:
        - Fast-forward: Jump back after returning to normal speed
        - Rewind: Jump forward after returning to normal speed
        - Speeds supported: 2x, 4x, 8x, 16x, 32x

        Args:
            speed (int): The new playback speed (1 = normal, >1 = fast-forward, 
                        <0 = rewind, 0 = paused)
        """
        if speed == 1:  # Normal playback speed reached
            direction = 1
            abs_last_speed = abs(self.last_playback_speed)
            resume_time = 0
            try:
                resume_time = self.getTime()
            except RuntimeError:
                Logger.info('No file is playing, stopping UnpauseJumpBack')
                xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')
                pass

            Logger.info(f"onPlayBackSpeedChanged with speed {speed} and resume_time {resume_time}")

            if self.last_playback_speed < 0:
                Logger.info('Resuming. Was rewound with speed X%d.' % (abs(self.last_playback_speed)))
            if self.last_playback_speed > 1:
                direction = -1
                Logger.info('Resuming. Was forwarded with speed X%d.' % (abs(self.last_playback_speed)))

            # Handle jump after fast-forward/rewind (jump back after fwd, jump forward after rwd)
            if direction == -1:  # Fast-forward - jump back
                if abs_last_speed == 2:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x2 * direction
                elif abs_last_speed == 4:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x4 * direction
                elif abs_last_speed == 8:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x8 * direction
                elif abs_last_speed == 16:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x16 * direction
                elif abs_last_speed == 32:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x32 * direction
            else:  # Rewind - jump forward
                if abs_last_speed == 2:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x2 * direction
                elif abs_last_speed == 4:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x4 * direction
                elif abs_last_speed == 8:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x8 * direction
                elif abs_last_speed == 16:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x16 * direction
                elif abs_last_speed == 32:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x32 * direction

            if abs_last_speed != 1:  # We actually fast-forwarded or rewound
                self.seekTime(resume_time)  # Perform the jump

        self.last_playback_speed = speed


class MyMonitor(xbmc.Monitor):
    """
    Custom Kodi Monitor class for handling system events.

    This class extends xbmc.Monitor to handle settings changes and other
    system events that affect the unpause jumpback functionality.

    Primary responsibility is to reload player settings when the user
    changes add-on configuration through Kodi's settings interface.
    """

    def __init__(self):
        """Initialize the MyMonitor instance."""
        super().__init__()
        Logger.debug('MyMonitor - init')

    def onSettingsChanged(self):
        """
        Handle add-on settings change events.

        Called when the user changes settings in the add-on configuration.
        Reloads settings in the player if it's initialized, or defers loading
        until the player is available.

        This ensures that configuration changes take effect immediately without
        requiring a restart of the add-on.
        """
        global player
        if player is not None:
            player.load_settings()
        else:
            Logger.debug('Settings changed before player initialised; deferring.')