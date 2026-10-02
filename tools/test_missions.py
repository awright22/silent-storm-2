"""Run every mission's scripted playthrough in the game.

    python tools/test_missions.py [mission name ...]

Builds a test build (each mission's test.lua compiled into its script), then
launches each mission that has a test and waits for its verdict in the log:
"SS2: TEST PASS" or "SS2: TEST FAIL: <why>". A mission also fails if it does
not start, crashes, logs a script error, or gives no verdict in time.

Afterwards the normal build is restored. Logs: build/shots/test_<mission>.log
Exit code 0 = every test passed.
"""
import os
import sys

import build
import config
import run as game_run

VERDICT_TIMEOUT = 120       # seconds after mission start


def main():
    wanted = set(sys.argv[1:])
    paths = config.load()
    shots_dir = os.path.join(config.REPO, 'build', 'shots')
    os.makedirs(shots_dir, exist_ok=True)
    if game_run.find_window('SS2.exe'):
        sys.exit('an SS2.exe window is already open')

    missions = [m for m in build.build(test=True) if m['has_test'] and (not wanted or m['name'] in wanted)]
    failures = 0
    try:
        for mission in missions:
            command = 'map %d %s' % (mission['variant'], ' '.join(str(p) for p in mission['party']))
            log_path = os.path.join(shots_dir, 'test_%s.log' % mission['name'])
            result = game_run.run_game(paths['run'], 'SS2.exe', command.strip(), log_path,
                                       until=('SS2: TEST PASS', 'SS2: TEST FAIL'), until_timeout=VERDICT_TIMEOUT)
            script_errors = [line for line in result.log.splitlines() if 'Script error' in line]
            fail_lines = [line for line in result.log.splitlines() if 'SS2: TEST FAIL' in line]
            if result.started is None:
                verdict = 'did not start'
            elif result.crashed:
                verdict = 'crashed'
            elif script_errors:
                verdict = script_errors[0].strip()
            elif fail_lines:
                verdict = fail_lines[0].split('SS2: ', 1)[1].strip()
            elif result.matched != 'SS2: TEST PASS':
                verdict = 'no verdict within %ds' % VERDICT_TIMEOUT
            else:
                verdict = None
            print('%s  %-12s %s' % ('FAIL' if verdict else 'PASS', mission['name'],
                                    verdict or 'started in %.0fs' % result.started), flush=True)
            failures += bool(verdict)
    finally:
        print('restoring the normal build...', flush=True)
        build.build()
    if not missions:
        sys.exit('no missions with a test.lua%s' % (' matching ' + ', '.join(sorted(wanted)) if wanted else ''))
    print('%d of %d mission tests passed' % (len(missions) - failures, len(missions)))
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
