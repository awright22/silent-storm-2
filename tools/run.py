"""Launch the staged SS2 build and capture what it shows.

    python tools/run.py <console command ...> [--shots 20,40] [--seconds 60] [--out name]

    python tools/run.py map 50001 --shots 25,45 --out m01

The console command (e.g. "map 50001") becomes a one-line cfg the engine
executes at boot. The game's debug output (engine messages and script out()
calls) is collected into build/shots/<name>.log and the game is killed after
--seconds. With --debug it runs under the engine port's dbgrun instead, which
adds crash stacks but makes large maps load several times slower.
Screenshots are taken with PrintWindow, so the window does not need focus and
is never raised over whatever else is on the desktop.
"""
import argparse
import ctypes
import os
import struct
import subprocess
import sys
import threading
import time
import zlib
from ctypes import wintypes

import config

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
PW_CLIENTONLY, PW_RENDERFULLCONTENT = 1, 2


class DebugOutput(threading.Thread):
    """Collect OutputDebugString text from one process without attaching a debugger.

    Uses the system-wide DBWIN buffer (the DebugView mechanism): the writer
    waits for DBWIN_BUFFER_READY, fills the shared buffer with its pid and
    text, then signals DBWIN_DATA_READY.
    """

    def __init__(self, log):
        super().__init__(daemon=True)
        self.log = log
        self.pid = None
        self.stop = False
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.CreateFileMappingW.restype = wintypes.HANDLE
        kernel32.MapViewOfFile.restype = ctypes.c_void_p
        self.ready = kernel32.CreateEventW(None, False, False, 'DBWIN_BUFFER_READY')
        self.data = kernel32.CreateEventW(None, False, False, 'DBWIN_DATA_READY')
        mapping = kernel32.CreateFileMappingW(wintypes.HANDLE(-1), None, 4, 0, 4096, 'DBWIN_BUFFER')
        self.view = kernel32.MapViewOfFile(wintypes.HANDLE(mapping), 4, 0, 0, 0)     # FILE_MAP_READ

    def run(self):
        while not self.stop:
            kernel32.SetEvent(wintypes.HANDLE(self.ready))
            if kernel32.WaitForSingleObject(wintypes.HANDLE(self.data), 200) != 0:
                continue
            pid = ctypes.c_uint32.from_address(self.view).value
            if pid == self.pid:
                text = ctypes.string_at(self.view + 4, 4092).split(b'\0', 1)[0]
                self.log.write(text.rstrip(b'\r\n') + b'\n')


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


def capture(hwnd, png_path):
    """Save the window's client area as a PNG. Returns (width, height)."""
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    w, h = rect.right, rect.bottom
    if w <= 0 or h <= 0:
        return 0, 0
    screen = user32.GetDC(0)
    dc = gdi32.CreateCompatibleDC(screen)
    bitmap = gdi32.CreateCompatibleBitmap(screen, w, h)
    gdi32.SelectObject(dc, bitmap)
    user32.PrintWindow(hwnd, dc, PW_CLIENTONLY | PW_RENDERFULLCONTENT)
    header = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)   # top-down BGRA
    pixels = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(dc, bitmap, 0, h, pixels, header, 0)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(dc)
    user32.ReleaseDC(0, screen)

    raw = pixels.raw
    rows = bytearray()
    for y in range(h):
        row = raw[y * w * 4:(y + 1) * w * 4]
        rgb = bytearray(w * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::4], row[1::4], row[0::4]
        rows += b'\x00' + rgb

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body))

    with open(png_path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n'
                + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(bytes(rows), 6))
                + chunk(b'IEND', b''))
    return w, h


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('command', nargs='+', help='console command to run at boot, e.g. map 50001')
    parser.add_argument('--shots', default='30', help='comma-separated capture times in seconds')
    parser.add_argument('--seconds', type=int, default=0, help='kill the game after this long (default: last shot + 5)')
    parser.add_argument('--out', default='run', help='base name for build/shots/<name>*.png and .log')
    parser.add_argument('--width', default='1024', help='window width: 640, 800, 1024 or 1280')
    parser.add_argument('--debug', action='store_true', help='run under dbgrun for crash stacks (slow loading)')
    args = parser.parse_args()

    paths = config.load()
    run = paths['run']
    shots_dir = os.path.join(config.REPO, 'build', 'shots')
    os.makedirs(shots_dir, exist_ok=True)
    shot_times = sorted(int(s) for s in args.shots.split(','))
    seconds = args.seconds or shot_times[-1] + 5

    if find_window('SS2.exe'):
        sys.exit('an SS2.exe window is already open')
    with open(os.path.join(run, 'cfg', 'ss2_run.cfg'), 'w', newline='\r\n') as f:
        f.write(' '.join(args.command) + '\n')

    game = [os.path.join(run, 'SS2.exe'), '-nosound', '-' + args.width, '-cfg', './cfg/ss2_run.cfg']
    log_path = os.path.join(shots_dir, args.out + '.log')
    with open(log_path, 'wb') as log:
        if args.debug:
            dbgrun = os.path.join(paths['engine'], 'tools', 'dbgrun.exe')
            env = dict(os.environ, DBGRUN_SECONDS=str(seconds))
            proc = subprocess.Popen([dbgrun, game[0], run] + game[1:], cwd=run, stdout=log, stderr=log, env=env)
        else:
            listener = DebugOutput(log)
            listener.start()
            proc = subprocess.Popen(game, cwd=run)
            listener.pid = proc.pid
        start = time.time()
        for at in shot_times:
            while time.time() - start < at and proc.poll() is None:
                time.sleep(0.25)
            hwnd = find_window('SS2.exe')
            if proc.poll() is not None or not hwnd:
                print('t=%ds: no game window (exited early?)' % at)
                break
            png = os.path.join(shots_dir, '%s_%02d.png' % (args.out, at))
            print('t=%ds: %s %dx%d' % ((at, png) + capture(hwnd, png)))
        while time.time() - start < seconds and proc.poll() is None:
            time.sleep(0.25)
        if args.debug:
            proc.wait(20)       # dbgrun's own watchdog ends the game
        else:
            if proc.poll() is None:
                proc.kill()
                proc.wait(10)
            else:
                print('game exited by itself with code 0x%X' % (proc.returncode & 0xFFFFFFFF))
            listener.stop = True
            listener.join(2)
    print('log: %s' % log_path)


if __name__ == '__main__':
    main()
