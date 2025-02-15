# -*- coding: utf-8 -*-
version = '1.0.0'

import time as _time
import platform as _platform

from ._mouse_event import ButtonEvent, MoveEvent, WheelEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, DOUBLE
from ._generic import GenericListener as _GenericListener

if _platform.system() == 'Windows':
    from. import _winmouse as _os_mouse
elif _platform.system() == 'Linux':
    from. import _nixmouse as _os_mouse
elif _platform.system() == 'Darwin':
    from. import _darwinmouse as _os_mouse
else:
    raise OSError("Unsupported platform '{}'".format(_platform.system()))

_pressed_events = set()
class _MouseListener(_GenericListener):
    def init(self):
        _os_mouse.init()
    def pre_process_event(self, event):
        if isinstance(event, ButtonEvent):
            if event.event_type in (UP, DOUBLE):
                _pressed_events.discard(event.button)
            else:
                _pressed_events.add(event.button)
        return True

    def listen(self):
        _os_mouse.listen(self.queue)

_listener = _MouseListener()

def is_pressed(button=LEFT):
    """ Returns True if the given button is currently pressed. """
    _listener.start_if_necessary()
    return button in _pressed_events

def press(button=LEFT):
    """ Presses the given button (but doesn't release). """
    _os_mouse.press(button)

def release(button=LEFT):
    """ Releases the given button. """
    _os_mouse.release(button)

def click(button=LEFT):
    """ Sends a click with the given button. """
    _os_mouse.press(button)
    _os_mouse.release(button)

def double_click(button=LEFT):
    """ Sends a double click with the given button. """
    click(button)
    click(button)

def right_click():
    """ Sends a right click with the given button. """
    click(RIGHT)

def wheel(delta=1):
    """ Scrolls the wheel `delta` clicks. Sign indicates direction. """
    _os_mouse.wheel(delta)

def move(x, y, absolute=True, duration=0, steps_per_second=120.0):
    """
    Moves the mouse. If `absolute`, to position (x, y), otherwise move relative
    to the current position. If `duration` is non-zero, animates the movement.
    The steps_per_second is only an approximation. Due to the internal sleep's
    unreliability it cannot be followed strictly. The less its value is, the more
    valid the number becomes.
    """
    x = int(x)
    y = int(y)

    # Requires an extra system call on Linux, but `move_relative` is measured
    # in millimeters so we would lose precision.
    position_x, position_y = get_position()

    if not absolute:
        x = position_x + x
        y = position_y + y

    if not duration:
        _os_mouse.move_to(x, y)
        return
    
    start_x = position_x
    start_y = position_y
    dx = x - start_x
    dy = y - start_y

    if dx == 0 and dy == 0:
        _time.sleep(duration)
        return

    interval_time = 1.0/steps_per_second
    start_time = _time.perf_counter()
    end_time = start_time + float(duration)
    step_start_time = start_time
    iteration_start_time = start_time
    while iteration_start_time < end_time:
        # Sleep to enforce the fps cap, considering the last step's duration and remaining time
        last_step_duration = iteration_start_time - step_start_time
        remaining_time = end_time - iteration_start_time
        corrected_sleep_time = interval_time - last_step_duration
        actual_sleep_time = min(remaining_time, corrected_sleep_time)
        if actual_sleep_time > 0:
            _time.sleep(actual_sleep_time)
        step_start_time = _time.perf_counter()

        # Move based on the elapsed time to ensure that the duration is valid
        current_time = step_start_time - start_time
        progress = current_time / duration
        _os_mouse.move_to(start_x + dx*progress, start_y + dy*progress)
        iteration_start_time = _time.perf_counter()

    # Move to the destination to ensure the final position
    _os_mouse.move_to(start_x + dx, start_y + dy)

def drag(start_x, start_y, end_x, end_y, absolute=True, duration=0):
    """
    Holds the left mouse button, moving from start to end position, then
    releases. `absolute` and `duration` are parameters regarding the mouse
    movement.
    """
    if is_pressed():
        release()
    move(start_x, start_y, absolute, 0)
    press()
    move(end_x, end_y, absolute, duration)
    release()

def on_button(callback, args=(), buttons=(LEFT, MIDDLE, RIGHT, X, X2), types=(UP, DOWN, DOUBLE), injected=(True, False)):
    """ Invokes `callback` with `args` when the specified event happens. """
    if not isinstance(buttons, (tuple, list)):
        buttons = (buttons,)
    if not isinstance(types, (tuple, list)):
        types = (types,)
    if not isinstance(injected, (tuple, list)):
        injected = (injected,)

    def handler(event):
        if isinstance(event, ButtonEvent):
            if event.event_type in types and event.button in buttons and event.injected in injected:
                callback(*args)
    _listener.add_handler(handler)
    return handler

def on_pressed(callback, args=()):
    """ Invokes `callback` with `args` when the left button is pressed. """
    return on_button(callback, args, [LEFT], [DOWN])

def on_click(callback, args=()):
    """ Invokes `callback` with `args` when the left button is clicked. """
    return on_button(callback, args, [LEFT], [UP])

def on_double_click(callback, args=()):
    """
    Invokes `callback` with `args` when the left button is double clicked.
    """
    return on_button(callback, args, [LEFT], [DOUBLE])

def on_middle_double_click(callback, args=()):
    """
    Invokes `callback` with `args` when the left button is double clicked.
    """
    return on_button(callback, args, [MIDDLE], [DOUBLE])

def on_right_double_click(callback, args=()):
    """
    Invokes `callback` with `args` when the left button is double clicked.
    """
    return on_button(callback, args, [RIGHT], [DOUBLE])

def on_right_click(callback, args=()):
    """ Invokes `callback` with `args` when the right button is clicked. """
    return on_button(callback, args, [RIGHT], [UP])

def on_middle_click(callback, args=()):
    """ Invokes `callback` with `args` when the middle button is clicked. """
    return on_button(callback, args, [MIDDLE], [UP])

def wait(button=LEFT, target_types=(UP, DOWN, DOUBLE)):
    """
    Blocks program execution until the given button performs an event.
    """
    from threading import Lock
    lock = Lock()
    lock.acquire()
    handler = on_button(lock.release, (), [button], target_types)
    lock.acquire()
    _listener.remove_handler(handler)

def get_position():
    """ Returns the (x, y) mouse position. """
    return _os_mouse.get_position()

def hook(callback):
    """
    Installs a global listener on all available mouses, invoking `callback`
    each time it is moved, a key status changes or the wheel is spun. A mouse
    event is passed as argument, with type either `mouse.ButtonEvent`,
    `mouse.WheelEvent` or `mouse.MoveEvent`.

    Returns the given callback for easier development.
    """
    _listener.add_handler(callback)
    return callback

def unhook(callback):
    """
    Removes a previously installed hook.
    """
    _listener.remove_handler(callback)

def unhook_all():
    """
    Removes all hooks registered by this application. Note this may include
    hooks installed by high level functions, such as `record`.
    """
    del _listener.handlers[:]

def record(button=RIGHT, target_types=(DOWN,)):
    """
    Records all mouse events until the user presses the given button.
    Then returns the list of events recorded. Pairs well with `play(events)`.

    Note: this is a blocking function.
    Note: for more details on the mouse hook and events see `hook`.
    """
    recorded = []
    hook(recorded.append)
    wait(button=button, target_types=target_types)
    unhook(recorded.append)
    return recorded

def play(events, speed_factor=1.0, include_clicks=True, include_moves=True, include_wheel=True):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals. If speed_factor is <= 0 then the actions are replayed as fast
    as the OS allows. Pairs well with `record()`.

    The parameters `include_*` define if events of that type should be included
    in the replay or ignored.
    """
    last_time = None
    for event in events:
        if speed_factor > 0 and last_time is not None:
            _time.sleep((event.time - last_time) / speed_factor)
        last_time = event.time

        if isinstance(event, ButtonEvent) and include_clicks:
            if event.event_type == UP:
                _os_mouse.release(event.button)
            else:
                _os_mouse.press(event.button)
        elif isinstance(event, MoveEvent) and include_moves:
            _os_mouse.move_to(event.x, event.y)
        elif isinstance(event, WheelEvent) and include_wheel:
            _os_mouse.wheel(event.delta)

replay = play
hold = press

if __name__ == '__main__':
    print('Recording... Double click to stop and replay.')
    play(record())
