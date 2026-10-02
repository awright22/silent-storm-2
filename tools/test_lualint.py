"""Tests for lualint. Needs no game data.

    python tools/test_lualint.py
"""
import sys

import lualint

NAMES = {
    'engine': ['out', 'Sleep', 'GetUnit', 'UnitKill', 'StartThread'],
    'noop': ['ShowHint', 'FadeIn'],
    'library': ['TRUE', 'FALSE', 'UnitCanFight', 'DS_ENEMY'],
}


def problems(source):
    return [message for _, message in lualint.lint(source, NAMES)]


def check(label, source, *expected_fragments):
    found = problems(source)
    ok = len(found) == len(expected_fragments) and all(
        any(fragment in message for message in found) for fragment in expected_fragments)
    print('%s  %s' % ('PASS' if ok else 'FAIL', label))
    if not ok:
        print('      expected: %s' % (list(expected_fragments) or 'no problems'))
        print('      found:    %s' % found)
    return ok


def main():
    results = [
        check('clean script',
              'guard = GetUnit( "g" )\n'
              'function Watch()\n'
              '\twhile TRUE do\n'
              '\t\tSleep( 10 )\n'
              '\t\tif not UnitCanFight( guard ) then out( "down" ) return end\n'
              '\tend\n'
              'end\n'
              'StartThread( Watch )\n'),
        check('misspelt engine function',
              'UnitKil( GetUnit( "g" ) )\n',
              'UnitKil is not defined anywhere'),
        check('do-nothing placeholder',
              'ShowHint( 3 )\n',
              'ShowHint does nothing'),
        check('each unknown name reported once',
              'Foo()\nFoo()\nFoo()\n',
              'Foo is not defined'),
        check('locals, parameters and loop variables are not globals',
              'function F( a, b )\n'
              '\tlocal c, d = a, b\n'
              '\tfor i = 1, 3 do out( i, c, d ) end\n'
              '\tfor k, v in { 1, 2 } do out( k, v ) end\n'
              'end\n'
              'F( 1, 2 )\n'),
        check('a flag assigned only inside a function may be read',
              'function Set() done = 1 end\n'
              'function Check() if done then out( "done" ) end end\n'
              'Set()\nCheck()\n'),
        check('table fields and constructor keys are not globals',
              't = { alpha = 1, beta = 2 }\n'
              'out( t.alpha, t.beta )\n'
              't.gamma = 3\n'),
        check('strings and comments are ignored',
              'out( "UnitKil( x )" )  -- UnitKil here too\n'
              "out( 'Foo()' )\n"),
        check('chunk-level use before definition',
              'Later()\n'
              'function Later() out( "x" ) end\n',
              'Later is used before the line that defines it'),
        check('a function body may call a function defined further down',
              'function First() Second() end\n'
              'function Second() out( "x" ) end\n'
              'First()\n'),
        check('multiple assignment defines every name',
              'a, b = 1, 2\n'
              'out( a, b )\n'),
        check('local x = x reads the outer x',
              'function F()\n'
              '\tlocal missing = missing\n'
              '\tout( missing )\n'
              'end\n'
              'F()\n',
              'missing is not defined'),
        check('upvalues read an enclosing local',
              'function Outer()\n'
              '\tlocal n = 1\n'
              '\tStartThread( function() out( %n ) end )\n'
              'end\n'
              'Outer()\n'),
    ]
    try:
        lualint.analyse('function F()\n\tout( 1 )\n')
        print('FAIL  unclosed block is a syntax error')
        results.append(False)
    except SyntaxError:
        print('PASS  unclosed block is a syntax error')
    sys.exit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
