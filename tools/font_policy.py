"""Approved B2 mixed font: untouched Hangul, original ASCII tiles at y=5..12."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_CHARACTERS = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !?.,+-&()[]')
ROM = next((ROOT / 'jp').glob('*.nes')).read_bytes()
assert hashlib.sha256(ROM).hexdigest() == '08ead6a2a83a7c476ac76a067a04055a6f68fe5b50248ea873d00305111da44d'
POLICY = {'id': 'B2', 'original_characters': ''.join(sorted(ORIGINAL_CHARACTERS)),
          'original_chr_file_base': '0x03F010', 'original_tile_y': 5,
          'cell': [8, 16], 'hangul_baseline': 14,
          'fallback': 'Unmodified Galmuri11-Condensed; no synthetic bold'}

def apply_font_policy(character, galmuri_mask):
    assert len(galmuri_mask) == 16
    if character not in ORIGINAL_CHARACTERS:
        return galmuri_mask
    off = 0x3f010 + ord(character) * 16
    tile = ROM[off:off + 16]
    return bytes(5) + bytes(tile[y] | tile[y + 8] for y in range(8)) + bytes(3)
