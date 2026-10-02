"""Stage a run root for Silent Storm 2 from an owned retail install.

    python tools/stage.py

Copies the retail data the engine needs into the run root (build/run by
default) together with the ported engine's Game.exe. The retail install is
only read. Re-running copies only what is missing or changed.
"""
import os
import re
import shutil

import config

SKIP_RES = ('.mdf', '.ldf')     # SQL Server dev leftovers shipped in retail res/, unused by the game


def _copy(src, dst):
    if os.path.exists(dst):
        s, d = os.stat(src), os.stat(dst)
        if s.st_size == d.st_size and int(s.st_mtime) <= int(d.st_mtime):
            return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _copy_tree(src, dst, skip=()):
    copied = 0
    for root, _, files in os.walk(src):
        for name in files:
            if name.lower().endswith(skip):
                continue
            path = os.path.join(root, name)
            copied += _copy(path, os.path.join(dst, os.path.relpath(path, src)))
    return copied


def stage(paths):
    retail, run = paths['retail'], paths['run']
    os.makedirs(run, exist_ok=True)
    copied = _copy_tree(os.path.join(retail, 'res'), os.path.join(run, 'res'), SKIP_RES)
    for name in ('cfg', 'scripts'):
        copied += _copy_tree(os.path.join(retail, name), os.path.join(run, name))
    copied += _copy(os.path.join(retail, 'start.cfg'), os.path.join(run, 'start.cfg'))
    copied += _copy(os.path.join(retail, 'game.db'), os.path.join(run, 'game.db.retail'))
    # The exe runs as SS2.exe so window-finding test tools aimed at "Game.exe"
    # (the engine port's own harness) never pick up an SS2 window, or vice versa.
    build = os.path.join(paths['engine'], 'build')
    copied += _copy(os.path.join(build, 'Game.exe'), os.path.join(run, 'SS2.exe'))
    copied += _copy(os.path.join(build, 'Game.pdb'), os.path.join(run, 'Game.pdb'))

    # the port runs windowed; retail config asks for exclusive fullscreen
    cfg = os.path.join(run, 'cfg', 'config.cfg')
    with open(cfg, encoding='cp1251') as f:
        text = f.read()
    windowed = re.sub(r'(setvar gfx_fullscreen = )\S+', r'\g<1>0.00', text)
    if windowed != text:
        with open(cfg, 'w', encoding='cp1251', newline='') as f:
            f.write(windowed)
    return copied


if __name__ == '__main__':
    paths = config.load()
    print('staged %s (%d files copied)' % (paths['run'], stage(paths)))
