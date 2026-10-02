"""sspack - read Silent Storm .res resource packages.

    <u32 signature> <u32 header offset> <file data ...> <header>

The header is a chunk stream whose main chunk holds a hash of
fileID -> (start, length). File IDs are record IDs from game.db, sometimes
with a part number in the high 16 bits.

The engine falls back to a loose file "<PackName>\\<fileID>" in the working
directory when an ID is not in the package, which is how SS2 ships its own
resources without touching the retail packs.

    python tools/sspack.py list  <pack.res>
    python tools/sspack.py get   <pack.res> <fileID> <out-file>
"""
import struct
import sys

from ssdb import iter_chunks

SIGNATURES = (0x95938921, 0x96948A22)   # Jan03 source, retail


class Package:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            signature, header_pos = struct.unpack('<II', f.read(8))
            if signature not in SIGNATURES:
                raise ValueError('%s: not a resource package' % path)
            f.seek(header_pos)
            header = f.read()
        self.files = {}     # fileID -> (start, length)
        for cid, _, po, ln in iter_chunks(header, 0, len(header)):
            if cid != 1:
                continue
            for mid, _, mp, ml in iter_chunks(header, po, po + ln):
                if mid != 1:
                    continue
                key = None
                for hid, _, hp, hl in iter_chunks(header, mp, mp + ml):
                    if hid == 1:
                        key = struct.unpack_from('<i', header, hp)[0]
                    elif hid == 2:
                        self.files[key] = struct.unpack_from('<II', header, hp)

    def __contains__(self, file_id):
        return file_id in self.files

    def read(self, file_id):
        start, length = self.files[file_id]
        with open(self.path, 'rb') as f:
            f.seek(start)
            return f.read(length)


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    pack = Package(path)
    if cmd == 'list':
        for file_id in sorted(pack.files):
            print('%d\t%d' % (file_id, pack.files[file_id][1]))
    elif cmd == 'get':
        with open(sys.argv[4], 'wb') as f:
            f.write(pack.read(int(sys.argv[3])))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
