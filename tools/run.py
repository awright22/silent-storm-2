"""Launch the staged SS2 build and capture what it shows.

    python tools/run.py <console command ...> [--shots 5,20 --claim TEXT] [--out name] [--front]

    python tools/run.py map 50010 118 116 42 120 --shots 5 --out m01
        --claim "Night view of the farm's south-east corner with the four-person team among the trees"

The console command (e.g. "map 50010 ...") becomes a one-line cfg the engine
executes at boot. Shot times count from the moment the mission starts (the
engine's "Start game" message), so they do not depend on how long the map
takes to load. The game's debug output (engine messages and script out()
calls) goes to build/shots/<name>.log, and the game is closed after the last
shot, or after --seconds when no shots are taken.

Every screenshot must come with a claim: one line saying what it is supposed
to show. It is saved next to the image for the adversarial reviewer
(docs/screenshot-review.md, tools/reviews.py).

This uses the engine port's test hooks (SS_DEBUG_LOG, SS_RUN_CMD with the
"screenshot" console command, SS_ALWAYS_ACTIVE, SS_NO_INPUT, SS_HIDE_CURSOR),
so nothing depends on the window: it opens without taking focus, is sent
behind other windows, ignores the real mouse and keyboard and draws no cursor.
--front leaves it where it opens, for playing by hand; then the game is not
closed automatically unless shots were asked for.
"""
import argparse
import ctypes
import os
import struct
import subprocess
import sys
import time
import zlib
from ctypes import wintypes

import config
import reviews

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
STARTED = 'Start game'
CRASHED = 'FATAL unhandled exception'
LOAD_TIMEOUT = 600


def find_window(exe_name):
    """Top-level visible window of class 'A5' owned by a process named exe_name."""
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls, 64)
        if cls.value != 'A5' or not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = kernel32.OpenProcess(0x1000, False, pid)     # QUERY_LIMITED_INFORMATION
        if process:
            path = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size))
            kernel32.CloseHandle(process)
            if os.path.basename(path.value).lower() == exe_name.lower():
                found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def send_to_back(hwnd):
    """Put the game window behind everything else, without activating it."""
    # HWND_BOTTOM; SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
    user32.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(1), 0, 0, 0, 0, 0x0013)


def bmp_to_png(bmp_path, png_path):
    """Convert an uncompressed 24- or 32-bit BMP (what the engine's screenshot writes) to PNG."""
    with open(bmp_path, 'rb') as f:
        data = f.read()
    offset = struct.unpack_from('<I', data, 10)[0]
    width, height, _, bpp, compression = struct.unpack_from('<iiHHI', data, 18)
    if data[:2] != b'BM' or compression != 0 or bpp not in (24, 32):
        raise ValueError('%s: unsupported BMP' % bmp_path)
    step = bpp // 8
    stride = (width * step + 3) & ~3
    rows = bytearray()
    order = range(abs(height) - 1, -1, -1) if height > 0 else range(abs(height))    # bottom-up when positive
    for y in order:
        row = data[offset + y * stride:offset + y * stride + width * step]
        rgb = bytearray(width * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::step], row[1::step], row[0::step]
        rows += b'\x00' + rgb

    def chunk(tag, payload):
        body = tag + payload
        return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body))

    with open(png_path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n'
                + chunk(b'IHDR', struct.pack('>IIBBBBB', width, abs(height), 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(bytes(rows), 6))
                + chunk(b'IEND', b''))


def read_log(path):
    try:
        with open(path, encoding='cp1251', errors='replace') as f:
            return f.read()
    except OSError:
        return ''


def stop(proc):
    """End the game process, however stuck it is."""
    if proc.poll() is None:
        proc.kill()
        try:
            proc.wait(15)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
            proc.wait(30)


class Run:
    """Outcome of one game run."""

    def __init__(self):
        self.started = None         # seconds from launch to "Start game", or None
        self.exit_code = None       # set if the game ended by itself
        self.crashed = False        # the log holds an unhandled exception
        self.matched = None         # which "until" text ended the run
        self.shots = []             # PNG paths written
        self.log = ''


def run_game(run_dir, exe_name, command, log_path, shots=(), shot_base=None, until=(), until_timeout=60,
             width='1024', front=False, keep_open=False, linger=0, load_timeout=LOAD_TIMEOUT, before=(),
             timed=()):
    """Launch the game on a console command and watch it.

    shots: seconds after mission start at which to save <shot_base>_NN.png.
    until: texts; the run ends as soon as the log contains one of them, or
    until_timeout seconds after the mission starts. With "until", shots due
    after the match are not taken.
    linger: with neither shots nor until, seconds to let the mission run.
    keep_open: leave the game running until the player closes it.
    before: console commands to run ahead of the main one (e.g. camera limits).
    timed: (seconds after mission start, console command) pairs. A command
    starting with "@" is run as Lua in the mission.
    """
    if os.path.exists(os.path.join(run_dir, 'BUILD_FAILED')):
        sys.exit('the last build of %s failed or is unfinished; fix it and rebuild before running' % run_dir)
    with open(os.path.join(run_dir, 'cfg', 'ss2_run.cfg'), 'w', newline='\r\n') as f:
        f.write(''.join(line + '\n' for line in tuple(before) + (command,)))
    if os.path.exists(log_path):
        os.remove(log_path)

    shot_files = []
    scheduled = []
    for at in sorted(shots):
        bmp = '%s_%02d.bmp' % (shot_base, at)
        if os.path.exists(bmp):
            os.remove(bmp)
        shot_files.append(bmp)
        # the console splits on spaces and SS_RUN_CMD on ';', so hand over a short relative path
        scheduled.append('@%s+%d|screenshot %s' % (STARTED, at, os.path.relpath(bmp, run_dir)))
    for n, (at, timed_command) in enumerate(timed):
        if timed_command.startswith('@'):
            # Lua: the hook runs console commands, and the console command for Lua is
            # script_run <file>, which looks for the file under scripts\
            lua_file = 'ss2_timed_%d.l' % n
            with open(os.path.join(run_dir, 'scripts', lua_file), 'w', newline='\r\n') as f:
                f.write(timed_command[1:] + '\n')
            timed_command = 'script_run ' + lua_file
        if ';' in timed_command or '|' in timed_command:
            sys.exit('a timed console command cannot contain ";" or "|": %s' % timed_command)
        scheduled.append('@%s+%d|%s' % (STARTED, at, timed_command))
    env = dict(os.environ, SS_DEBUG_LOG=log_path, SS_ALWAYS_ACTIVE='1')
    if not front:
        # unattended: the real mouse and keyboard must not reach the game (they scroll the camera
        # and click the interface), and the cursor must not be in the screenshots
        env.update(SS_NO_INPUT='1', SS_HIDE_CURSOR='1')
    if scheduled:
        env['SS_RUN_CMD'] = ';'.join(scheduled)

    startup = subprocess.STARTUPINFO()
    if not front:
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 4     # SW_SHOWNOACTIVATE
    game = [os.path.join(run_dir, exe_name), '-' + width, '-nosound', '-cfg', './cfg/ss2_run.cfg']
    proc = subprocess.Popen(game, cwd=run_dir, startupinfo=startup, env=env)

    result = Run()
    launched = time.time()
    in_back = front
    try:
        while proc.poll() is None and time.time() - launched < load_timeout:
            time.sleep(0.5)
            if not in_back:
                hwnd = find_window(exe_name)
                if hwnd:
                    send_to_back(hwnd)
                    in_back = True
            log = read_log(log_path)
            if CRASHED in log:
                break
            if STARTED in log:
                result.started = time.time() - launched
                break

        if result.started is not None:
            # what ends the run: an "until" text, else the last screenshot, else "linger" seconds
            deadline = time.time() + (until_timeout if until else max(shots) + 20 if shots else linger)
            while proc.poll() is None:
                log = read_log(log_path)
                if CRASHED in log:
                    break
                if until:
                    result.matched = next((text for text in until if text in log), None)
                    if result.matched:
                        break
                elif shot_files:
                    if all(os.path.exists(bmp) for bmp in shot_files):
                        time.sleep(0.5)     # let the last file finish writing
                        break
                if not keep_open and time.time() > deadline:
                    break
                time.sleep(0.5)
    finally:
        if proc.poll() is None:
            stop(proc)
        else:
            result.exit_code = proc.returncode & 0xFFFFFFFF

    result.log = read_log(log_path)
    result.crashed = CRASHED in result.log
    for bmp in shot_files:
        if os.path.exists(bmp):
            png = bmp[:-4] + '.png'
            bmp_to_png(bmp, png)
            os.remove(bmp)
            result.shots.append(png)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('command', nargs='+', help='console command to run at boot, e.g. map 50010 118 116 42 120')
    parser.add_argument('--shots', default='', help='comma-separated capture times, seconds after mission start')
    parser.add_argument('--out', default='run', help='base name for build/shots/<name>*.png and .log')
    parser.add_argument('--width', default='1024', help='window width: 640, 800, 1024 or 1280')
    parser.add_argument('--front', action='store_true', help='open the window normally, for playing by hand')
    parser.add_argument('--claim', action='append', default=[],
                        help='what a screenshot is supposed to show, for its reviewer: once for all shots, '
                             'or once per shot in time order. Required with --shots.')
    parser.add_argument('--at', action='append', default=[], metavar='SECONDS:COMMAND',
                        help='console command to run that many seconds after mission start; a command '
                             'starting with @ is Lua, e.g. "8:@CameraSet(GetCamera(SS2_CAMERA_farm))" (repeatable)')
    parser.add_argument('--before', action='append', default=[], metavar='COMMAND',
                        help='console command to run ahead of the main one (repeatable)')
    parser.add_argument('--seconds', type=int, default=10,
                        help='without --shots: how long to let the mission run before closing it (default 10)')
    args = parser.parse_args()

    paths = config.load()
    shots_dir = os.path.join(config.REPO, 'build', 'shots')
    os.makedirs(shots_dir, exist_ok=True)
    if find_window('SS2.exe'):
        sys.exit('an SS2.exe window is already open')
    shots = sorted(int(s) for s in args.shots.split(',') if s)
    if shots and len(args.claim) not in (1, len(shots)):
        sys.exit('--shots needs --claim: one for all shots or one per shot. Every screenshot is reviewed '
                 'against its claim (docs/screenshot-review.md).')
    log_path = os.path.join(shots_dir, args.out + '.log')

    result = run_game(paths['run'], 'SS2.exe', ' '.join(args.command), log_path, shots=shots,
                      shot_base=os.path.join(shots_dir, args.out), width=args.width, front=args.front,
                      keep_open=args.front and not shots, linger=args.seconds, before=args.before,
                      timed=[(int(item.split(':', 1)[0]), item.split(':', 1)[1]) for item in args.at])
    for n, png in enumerate(result.shots):
        reviews.write_claim(png, args.claim[n if len(args.claim) > 1 else 0])
    if result.started is None:
        print('mission did not start (%s)' % (
            'crashed' if result.crashed else
            'game exited with code 0x%X' % result.exit_code if result.exit_code is not None else
            'still loading after %ds' % LOAD_TIMEOUT))
    else:
        print('mission started %.0fs after launch' % result.started)
    for png in result.shots:
        print(png)
    if result.shots:
        print('these screenshots need a reviewer: python tools/reviews.py')
    if result.crashed:
        print('the game crashed: see the stack at the end of the log')
    print('log: %s' % log_path)
    sys.exit(0 if result.started is not None and not result.crashed and len(result.shots) == len(shots) else 1)


if __name__ == '__main__':
    main()
