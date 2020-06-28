# -*- coding: utf-8 -*-

import xbmc
import time
from resources.lib.common import *
from resources.lib.common import log

global g_jumpBackOnResume
global g_jumpBackOnPlaybackStarted
global g_pausedTime
global g_jumpBackSecsAfterPause
global g_jumpBackSecsAfterFwdX2
global g_jumpBackSecsAfterFwdX4
global g_jumpBackSecsAfterFwdX8
global g_jumpBackSecsAfterFwdX16
global g_jumpBackSecsAfterFwdX32
global g_jumpBackSecsAfterRwdX2
global g_jumpBackSecsAfterRwdX4
global g_jumpBackSecsAfterRwdX8
global g_jumpBackSecsAfterRwdX16
global g_jumpBackSecsAfterRwdX32
global g_jumpBackSecsAfterResume
global g_lastPlaybackSpeed
global g_waitForJumpback


def run(args):
    """
    This is 'main'

    @param args: sys.argv is passed in here
    """

    load_settings()
    kodi_monitor = MyMonitor()
    player = MyPlayer()

    while not kodi_monitor.abortRequested():
        if kodi_monitor.waitForAbort(1):
            # Abort was requested while waiting. We should exit
            break


def is_excluded(full_path):
    """
    Check exclusion settings for filename passed as argument

    @param full_path: path to check
    @return: True or False
    """
    if not full_path:
        return True

    log(f"Checking exclusion for: '{full_path}'.")

    if (full_path.find("pvr://") > -1) and get_setting_as_bool('ExcludeLiveTV'):
        log("Video is playing via Live TV, which is set as an excluded location.")
        return True

    if (full_path.find("http://") > -1) and (full_path.find("https://") > -1) and get_setting_as_bool('ExcludeHTTP'):
        log("Video is playing via HTTP source, which is set as an excluded location.")
        return True

    ExcludePath = get_setting('ExcludePath')
    if ExcludePath and get_setting_as_bool('ExcludePathOption'):
        if full_path.find(ExcludePath) > -1:
            log(f"Video is playing from '{ExcludePath}', which is set as excluded path 1.")
            return True

    ExcludePath2 = get_setting('ExcludePath2')
    if ExcludePath2 and get_setting_as_bool('ExcludePathOption2'):
        if full_path.find(ExcludePath2) > -1:
            log(f"Video is playing from '{ExcludePath2}', which is set as excluded path 2.")
            return True

    ExcludePath3 = get_setting('ExcludePath3')
    if ExcludePath3 and get_setting_as_bool('ExcludePathOption3'):
        if full_path.find(ExcludePath3) > -1:
            log(f"Video is playing from '{ExcludePath3}', which is set as excluded path 3.")
            return True

    log(f"Not excluded: '{full_path}'")
    return False


def load_settings():
    """
    Load the addon's settings
    """
    global g_jumpBackOnResume
    global g_jumpBackOnPlaybackStarted
    global g_pausedTime
    global g_jumpBackSecsAfterPause
    global g_waitForJumpback
    global g_jumpBackSecsAfterFwdX2
    global g_jumpBackSecsAfterFwdX4
    global g_jumpBackSecsAfterFwdX8
    global g_jumpBackSecsAfterFwdX16
    global g_jumpBackSecsAfterFwdX32
    global g_jumpBackSecsAfterRwdX2
    global g_jumpBackSecsAfterRwdX4
    global g_jumpBackSecsAfterRwdX8
    global g_jumpBackSecsAfterRwdX16
    global g_jumpBackSecsAfterRwdX32

    g_jumpBackOnResume = get_setting_as_bool('jumpbackonresume')
    g_jumpBackOnPlaybackStarted = get_setting_as_bool('jumpbackonplaybackstarted')
    g_jumpBackSecsAfterPause = int(float(get_setting("jumpbacksecs")))
    g_jumpBackSecsAfterFwdX2 = int(float(get_setting("jumpbacksecsfwdx2")))
    g_jumpBackSecsAfterFwdX4 = int(float(get_setting("jumpbacksecsfwdx4")))
    g_jumpBackSecsAfterFwdX8 = int(float(get_setting("jumpbacksecsfwdx8")))
    g_jumpBackSecsAfterFwdX16 = int(float(get_setting("jumpbacksecsfwdx16")))
    g_jumpBackSecsAfterFwdX32 = int(float(get_setting("jumpbacksecsfwdx32")))
    g_jumpBackSecsAfterRwdX2 = int(float(get_setting("jumpbacksecsrwdx2")))
    g_jumpBackSecsAfterRwdX4 = int(float(get_setting("jumpbacksecsrwdx4")))
    g_jumpBackSecsAfterRwdX8 = int(float(get_setting("jumpbacksecsrwdx8")))
    g_jumpBackSecsAfterRwdX16 = int(float(get_setting("jumpbacksecsrwdx16")))
    g_jumpBackSecsAfterRwdX32 = int(float(get_setting("jumpbacksecsrwdx32")))
    g_waitForJumpback = int(float(get_setting("waitforjumpback")))

    if g_jumpBackOnResume:
        log('Settings loaded, jump back set to: On Resume')
    else:
        log('Settings loaded, jump back set to: On Pause')


class MyPlayer(xbmc.Player):

    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        log('MyPlayer - init')

    # Default case, Jump Back on Resume
    # This means the pause position is where the user actually paused...which is usually the desired behaviour
    def onPlayBackResumed(self):

        global g_jumpBackSecsAfterPause
        global g_pausedTime
        global g_waitForJumpback

        if g_jumpBackOnResume:

            if g_pausedTime > 0:
                log(f'onPlayBackResumed. Was paused for {int(time.time() - g_pausedTime)} seconds.')

            # check for exclusion
            _filename = self.getPlayingFile()
            if is_excluded(_filename):
                log(f"Ignored because '{_filename}' is in exclusion settings.")
                return

            else:
                # handle jump back after pause
                if g_jumpBackSecsAfterPause != 0 \
                        and self.isPlayingVideo() \
                        and self.getTime() > g_jumpBackSecsAfterPause \
                        and g_pausedTime > 0 \
                        and (time.time() - g_pausedTime) > g_waitForJumpback:
                    resume_time = self.getTime() - g_jumpBackSecsAfterPause
                    self.seekTime(resume_time)
                    log(f'Resumed, with {int(g_jumpBackSecsAfterPause)}s jump back')

                g_pausedTime = 0

    # Alternatively, handle Jump Back on Pause
    # (for low power systems, so it happens in the background during the pause - prevents janky-ness)
    def onPlayBackPaused(self):

        global g_jumpBackSecsAfterPause
        global g_waitForJumpback
        global g_jumpBackOnResume
        global g_pausedTime

        g_pausedTime = time.time()
        log(f'onPlayBackPaused. Time: {g_pausedTime}')

        _filename = self.getPlayingFile()
        if is_excluded(_filename):
            log(f'Playback paused - ignoring because [{_filename}] is in exclusion settings.')
            return

        if not g_jumpBackOnResume and self.isPlayingVideo() and 0 < g_jumpBackSecsAfterPause < self.getTime():
            jump_back_point = self.getTime() - g_jumpBackSecsAfterPause
            log(f'Playback paused - jumping back {g_jumpBackSecsAfterPause}s to: {int(jump_back_point)} seconds')
            xbmc.executebuiltin(
                f'AlarmClock(JumpbackPaused, Seek(-{g_jumpBackSecsAfterPause})), 0:{g_waitForJumpback}, silent)')

    def onAVStarted(self):
        global g_jumpBackOnPlaybackStarted
        global g_jumpBackSecsAfterPause

        if g_jumpBackOnPlaybackStarted:
            current_time = self.getTime()
            log(f'onAVStarted at {current_time}')

            # check for exclusion
            _filename = self.getPlayingFile()
            if is_excluded(_filename):
                log(f"Ignored because '{_filename}' is in exclusion settings.")
                return
            else:
                if current_time > 0 and 0 < g_jumpBackSecsAfterPause < current_time:
                    resume_time = current_time - g_jumpBackSecsAfterPause
                    log(f"Resuming playback from saved time: {int(current_time)} "
                        f"with jump back seconds: {g_jumpBackSecsAfterPause}, "
                        f"thus resume time: {int(resume_time)}")
                    self.seekTime(resume_time)

    def onPlayBackSpeedChanged(self, speed):
        global g_lastPlaybackSpeed

        if speed == 1:  # normal playback speed reached
            direction = 1
            absLastSpeed = abs(g_lastPlaybackSpeed)
            if g_lastPlaybackSpeed < 0:
                log('Resuming. Was rewound with speed X%d.' % (abs(g_lastPlaybackSpeed)))
            if g_lastPlaybackSpeed > 1:
                direction = -1
                log('Resuming. Was forwarded with speed X%d.' % (abs(g_lastPlaybackSpeed)))
            # handle jump after fwd/rwd (jump back after fwd, jump forward after rwd)
            if direction == -1:  # fwd
                if absLastSpeed == 2:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX2 * direction
                elif absLastSpeed == 4:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX4 * direction
                elif absLastSpeed == 8:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX8 * direction
                elif absLastSpeed == 16:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX16 * direction
                elif absLastSpeed == 32:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX32 * direction
            else:  # rwd
                if absLastSpeed == 2:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX2 * direction
                elif absLastSpeed == 4:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX4 * direction
                elif absLastSpeed == 8:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX8 * direction
                elif absLastSpeed == 16:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX16 * direction
                elif absLastSpeed == 32:
                    resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX32 * direction

            if absLastSpeed != 1:  # we really fwd'ed or rwd'ed
                self.seekTime(resumeTime)  # do the jump

        g_lastPlaybackSpeed = speed

    # def onPlayBackResumed(self):
    #     log('Cancelling alarm - playback either resumed or stopped by the user')
    #     xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')

    # We don't care if playback was resumed or stopped, we just want to know when we're no longer paused
    # onPlayBackStopped = onPlayBackResumed


class MyMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        log('MyMonitor - init')

    def onSettingsChanged(self):
        load_settings()


