#!/usr/bin/env python3
"""Exercise original menu controls and verify complete 8x16 setting rows in Mesen.
Run JP and KO in separate invocations, then compare their semantic state traces.
Hidden fields use an explicitly test-only ROM; no release cheat flags are changed.
"""
from pathlib import Path
import argparse, hashlib, json
from run_mesen import Runner, core_path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/settings_patch'
M = json.loads((BASE / 'manifest.json').read_text())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('language', choices=['jp', 'ko'])
    ap.add_argument('--hidden', action='store_true')
    ap.add_argument('--title-entry', action='store_true')
    ap.add_argument('--rom', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    out = args.out or ROOT / 'build/runtime' / ('settings_verify_' + args.language + ('_hidden' if args.hidden else ''))
    out.mkdir(parents=True, exist_ok=True)
    rom = args.rom or (next((ROOT / 'jp').glob('*.nes')) if args.language == 'jp' else BASE / 'Gun Nac (Korean settings prototype).nes')
    release_sha = hashlib.sha256(rom.read_bytes()).hexdigest()
    if args.hidden:
        data = bytearray(rom.read_bytes())
        off = 16 + data[4] * 16384 - 7  # CPU FFF9, same gate as original.
        assert data[off] == 0
        data[off] = 1
        rom = out / 'hidden_options_TEST_ONLY.nes'
        rom.write_bytes(data)
    core = core_path()
    r = Runner(core, out); r.load(rom)
    font = (BASE / 'settings.chr').read_bytes()
    glyphs = json.loads((BASE / 'glyphs.json').read_text())
    checks = []; coverage = {s['name']: set() for s in M['settings']}
    def frames(n, buttons=()):
        r.buttons = set(buttons)
        for _ in range(n): r.run()
    def press(button):
        frames(2, [button]); frames(38)
    def assert_pixels(text, x, y, width):
        raw, w, h, pitch = r.video
        assert r.pixel == 1 and (w, h) == (256, 240)
        for col, c in enumerate(text.ljust(width)):
            for half, tile in enumerate(glyphs[c]):
                for yy, bits in enumerate(font[tile * 16:tile * 16 + 8]):
                    for xx in range(8):
                        px, py = (x + col) * 8 + xx, (y + half) * 8 + yy
                        off = py * pitch + px * 4
                        # White font ink; animated orange/blue stars show through
                        # transparent cells and must not count as text pixels.
                        got = min(raw[off:off + 3]) >= 200
                        want = bool(bits & (0x80 >> xx))
                        assert got == want, (text, px, py, r.frame)
    def state(label, screenshot=False):
        ram = r.ram()
        fields = {s['name']: ram[int(s['ram'], 16)] for s in M['settings']}
        fields['cursor'] = ram[0x1af]
        checks.append(dict(label=label, state=fields))
        if args.language == 'ko':
            t = M['title']; assert_pixels(t['text'], t['x'], t['row'], len(t['text']))
            for s in M['settings'][:8 if args.hidden else 5]:
                value = fields[s['name']]
                if s['name'] in ('counterattack', 'priority', 'death'): value = int(bool(value))
                assert value < len(s['values']), (s['name'], value)
                assert_pixels(s['values'][value], s['x'], s['row'], s['width'])
                coverage[s['name']].add(value)
            # Catch original ASCII-space clear tiles accidentally becoming ink.
            assert_pixels(' ', 0, 0, 32)
        if screenshot: r.capture(out / (label + '.png'))
        return fields
    def select(index):
        for _ in range(10):
            current = r.ram()[0x1af]
            if current == index: return
            press(5 if current < index else 4)
        raise AssertionError(('cursor cannot reach', index))
    def set_value(index, target):
        select(index); address = int(M['settings'][index]['ram'], 16)
        for _ in range(100):
            current = r.ram()[address]
            if current == target: return
            press(7 if current < target else 6)
        raise AssertionError(('cannot set value', index, target))

    if args.title_entry:
        frames(360); press(3); frames(200); press(5); press(3); frames(200)
    else:
        frames(200, [8, 0]); frames(100)  # Actual A+B boot entry, no PC/RAM redirects.
    state('default', True)
    if not args.hidden:
        select(0); press(7)
        assert state('area_locked_without_sound_05')['area'] == 1
    set_value(1, 5)  # Original normal-build gate: area editing needs sound 05.
    set_value(0, 0)
    for value in range(9):
        set_value(0, value); state(f'area_{value}')
    press(7); assert state('area_upper_limit')['area'] == 8
    set_value(0, 0); press(6); assert state('area_lower_limit')['area'] == 0
    set_value(0, 1)
    set_value(1, 1)
    for value in range(1, 0x49):
        set_value(1, value); state(f'sound_{value:02X}', value == 0x0a)
    press(7); assert state('sound_upper_limit')['sound'] == 0x48
    set_value(1, 1); press(6); assert state('sound_lower_limit')['sound'] == 1
    set_value(1, 1); press(0); state('sound_play'); press(8); state('sound_stop')
    for index in [2, 3, 4] + ([5, 6, 7] if args.hidden else []):
        for value in range(len(M['settings'][index]['values'])):
            set_value(index, value); state(f'{M["settings"][index]["name"]}_{value}', True)
        press(7)
        assert state(f'upper_limit_{index}')[M['settings'][index]['name']] == len(M['settings'][index]['values']) - 1
        set_value(index, 0); press(6)
        assert state(f'lower_limit_{index}')[M['settings'][index]['name']] == 0
    # Restore normal defaults, leave through real START and retain values.
    set_value(2, 1); set_value(3, 0); set_value(4, 1)
    select(7 if args.hidden else 4); press(5)
    assert state('cursor_lower_limit')['cursor'] == (7 if args.hidden else 4)
    select(0); press(4); assert state('cursor_upper_limit')['cursor'] == 0
    state('before_exit', True)
    press(3); frames(360); r.capture(out / 'after_exit.png')
    exit_state = {s['name']: r.ram()[int(s['ram'], 16)] for s in M['settings']}
    # Advance the original shop dialogs, choose exit, and enter the first stage.
    for _ in range(5): press(8); frames(60)
    for _ in range(3): press(5); frames(10)
    press(8); frames(300); r.capture(out / 'stage_entry.png')
    frames(600, [8]); r.capture(out / 'stage_play.png')
    result = dict(language=args.language, hidden_test_only=args.hidden,
                  entry='title_CONFIG.SYS' if args.title_entry else 'boot_A+B',
                  release_rom_sha256=release_sha, executed_rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                  frames=r.frame, core=r.info, video_callbacks=r.video_count,
                  audio_frames=r.audio_frames, checks=checks,
                  coverage={k: sorted(v) for k, v in coverage.items()},
                  pixel_verification=args.language == 'ko',
                  exit_state=exit_state)
    r.close()
    (out / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'coverage')}, ensure_ascii=False))

if __name__ == '__main__': main()
