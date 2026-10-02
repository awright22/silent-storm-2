"""ssdb - read, edit and write Silent Storm game.db files.

game.db is a chunk tree holding one column-store object per table:

    root  id=4  format marker (retail only)
          id=1  main: tables hash (tableID -> object key) + relations
          id=0  object index, 9 bytes per object (typeID, key, valid)
          id=2  object data, one frame per object: key + table body
    body  fields 2/3/4 = int / float / wstring cells, one chunk per row
          field 5      = column descriptors in schema order (name, type)
          fields 6/7/8 = column names per cell group

Tables are decoded on first access and re-encoded only if modified, so an
untouched table is written back byte for byte. Column names are CP1251 and
matched byte-exactly (retail has a Cyrillic letter inside "DamageMod").

    db = Database.load("game.db")
    scripts = db["Scripts"]
    scripts.upsert(900001, Name="SS2_M01", CodeText=source)
    db.save("out/game.db")
"""
import struct

from table_names import TABLE_IDS, TABLE_NAMES

STORAGE_TYPE_ID = 0xA1843130
T_INT, T_BOOL, T_FLOAT, T_WSTR = 0, 1, 2, 3


def iter_chunks(buf, off, end):
    """Yield (id, header_off, payload_off, payload_len) for one chunk level."""
    while end - off >= 2:
        cid = buf[off]
        lb = buf[off + 1]
        if lb & 1:
            ln = struct.unpack_from('<I', buf, off + 1)[0] >> 1
            po = off + 5
        else:
            ln = lb >> 1
            po = off + 2
        if po + ln > end:
            raise ValueError('chunk at %d overruns its parent' % off)
        yield cid, off, po, ln
        off = po + ln
    if off != end:
        raise ValueError('trailing byte at %d' % off)


def emit(cid, payload):
    n = len(payload)
    if n < 128:
        return bytes((cid, n << 1)) + payload
    return bytes((cid,)) + struct.pack('<I', (n << 1) | 1) + payload


def _i32(v):
    return struct.pack('<i', v)


def _bits_to_float(bits):
    return struct.unpack('<f', struct.pack('<i', bits))[0]


def _float_to_bits(value):
    return struct.unpack('<i', struct.pack('<f', value))[0]


class Table:
    """One table. Rows are addressed by the value of their ID column."""

    def __init__(self, tid, key, body):
        self.tid = tid
        self.key = key
        self._body = body
        self._decoded = False
        self.dirty = False

    @property
    def name(self):
        return TABLE_NAMES.get(self.tid, '0x%08X' % self.tid)

    # -- decode / encode ---------------------------------------------------

    def _decode(self):
        if self._decoded:
            return
        buf = self._body
        fields = {}
        for cid, _, po, ln in iter_chunks(buf, 0, len(buf)):
            if cid in fields or not 2 <= cid <= 8:
                raise ValueError('%s: unexpected body field %d' % (self.name, cid))
            fields[cid] = (po, ln)
        if len(fields) != 7:
            raise ValueError('%s: body does not have fields 2..8' % self.name)

        def elements(cid):
            po, ln = fields[cid]
            return [(p, l) for c, _, p, l in iter_chunks(buf, po, po + ln) if c == 1]

        def cell_rows(cid):
            rows = []
            for p, l in elements(cid):
                blob = b''
                for c, _, sp, sl in iter_chunks(buf, p, p + l):
                    if c == 2:
                        blob = buf[sp:sp + sl]
                rows.append(list(struct.unpack('<%di' % (len(blob) // 4), blob)))
            return rows

        def names(cid):
            return [bytes(buf[p:p + l]) for p, l in elements(cid)]

        self._ints = cell_rows(2)
        self._flts = cell_rows(3)
        self._wstrs = [
            [buf[sp:sp + sl].decode('utf-16le', 'surrogatepass')
             for c, _, sp, sl in iter_chunks(buf, p, p + l) if c == 1]
            for p, l in elements(4)
        ]
        self._columns = []
        for p, l in elements(5):
            cname, ctype = None, None
            for c, _, sp, sl in iter_chunks(buf, p, p + l):
                if c == 2:
                    cname = bytes(buf[sp:sp + sl])
                elif c == 3:
                    ctype = struct.unpack_from('<i', buf, sp)[0]
            self._columns.append((cname, ctype))
        self._int_names = names(6)
        self._flt_names = names(7)
        self._wstr_names = names(8)

        if not len(self._ints) == len(self._flts) == len(self._wstrs):
            raise ValueError('%s: cell groups disagree on row count' % self.name)
        self._where = {}
        for group, cols in ((0, self._int_names), (1, self._flt_names), (2, self._wstr_names)):
            for i, cname in enumerate(cols):
                self._where[cname] = (group, i)
        self._id_col = self._int_names.index(b'ID')
        self._by_id = {row[self._id_col]: r for r, row in enumerate(self._ints)}
        if len(self._by_id) != len(self._ints):
            raise ValueError('%s: duplicate record IDs' % self.name)
        self._decoded = True

    def encode(self):
        """Table body bytes; the original bytes if the table was never modified."""
        if not self.dirty:
            return self._body
        return self._encode()

    def _encode(self):
        self._decode()

        def cell_rows(rows):
            # an empty row is just its count; the value blob is only written when non-empty
            return b''.join(
                emit(1, emit(1, _i32(len(row)))
                     + (emit(2, struct.pack('<%di' % len(row), *row)) if row else b''))
                for row in rows)

        def names(cols):
            return b''.join(emit(1, c) for c in cols)

        return b''.join((
            emit(2, cell_rows(self._ints)),
            emit(3, cell_rows(self._flts)),
            emit(4, b''.join(
                emit(1, b''.join(emit(1, s.encode('utf-16le', 'surrogatepass')) for s in row))
                for row in self._wstrs)),
            emit(5, b''.join(emit(1, emit(2, n) + emit(3, _i32(t))) for n, t in self._columns)),
            emit(6, names(self._int_names)),
            emit(7, names(self._flt_names)),
            emit(8, names(self._wstr_names)),
        ))

    # -- schema ------------------------------------------------------------

    @property
    def columns(self):
        """[(name, type code)] in schema order; type 0 int, 1 bool, 2 float, 3 string."""
        self._decode()
        return [(n.decode('cp1251'), t) for n, t in self._columns]

    def _locate(self, col):
        key = col if isinstance(col, bytes) else col.encode('cp1251')
        try:
            return self._where[key]
        except KeyError:
            raise KeyError('%s has no column %r' % (self.name, col)) from None

    # -- reading -----------------------------------------------------------

    def __len__(self):
        self._decode()
        return len(self._ints)

    def __contains__(self, rid):
        self._decode()
        return rid in self._by_id

    def ids(self):
        self._decode()
        return list(self._by_id)

    def max_id(self):
        self._decode()
        return max(self._by_id, default=0)

    def _row_dict(self, r):
        out = {}
        for cname, _ in self._columns:
            group, i = self._where[cname]
            if group == 0:
                value = self._ints[r][i]
            elif group == 1:
                value = _bits_to_float(self._flts[r][i])
            else:
                value = self._wstrs[r][i]
            out[cname.decode('cp1251')] = value
        return out

    def get(self, rid):
        """The row with this ID as {column: value}, or None."""
        self._decode()
        r = self._by_id.get(rid)
        return None if r is None else self._row_dict(r)

    def rows(self):
        self._decode()
        for r in range(len(self._ints)):
            yield self._row_dict(r)

    def find(self, **where):
        """Rows whose columns equal the given values."""
        self._decode()
        tests = [(self._locate(c), v) for c, v in where.items()]
        for r in range(len(self._ints)):
            for (group, i), want in tests:
                if group == 0:
                    have = self._ints[r][i]
                elif group == 1:
                    have = _bits_to_float(self._flts[r][i])
                else:
                    have = self._wstrs[r][i]
                if have != want:
                    break
            else:
                yield self._row_dict(r)

    # -- writing -----------------------------------------------------------

    def _set(self, r, col, value):
        group, i = self._locate(col)
        if group == 0:
            self._ints[r][i] = int(value)
        elif group == 1:
            self._flts[r][i] = _float_to_bits(float(value))
        else:
            if not isinstance(value, str):
                raise TypeError('%s.%s takes a string' % (self.name, col))
            self._wstrs[r][i] = value

    def upsert(self, rid, **values):
        """Set columns on row `rid`, adding the row (zeros / empty strings) if new."""
        self._decode()
        if 'ID' in values and values['ID'] != rid:
            raise ValueError('ID column disagrees with the row id')
        r = self._by_id.get(rid)
        if r is None:
            r = len(self._ints)
            self._ints.append([0] * len(self._int_names))
            self._flts.append([0] * len(self._flt_names))
            self._wstrs.append([''] * len(self._wstr_names))
            self._ints[r][self._id_col] = rid
            self._by_id[rid] = r
        for col, value in values.items():
            self._set(r, col, value)
        self.dirty = True

    def clone(self, src_id, new_id, **overrides):
        """Copy row `src_id` to a new row `new_id`, then apply overrides."""
        self._decode()
        if new_id in self._by_id:
            raise ValueError('%s already has row %d' % (self.name, new_id))
        src = self._by_id[src_id]
        self._ints.append(list(self._ints[src]))
        self._flts.append(list(self._flts[src]))
        self._wstrs.append(list(self._wstrs[src]))
        r = len(self._ints) - 1
        self._ints[r][self._id_col] = new_id
        self._by_id[new_id] = r
        for col, value in overrides.items():
            self._set(r, col, value)
        self.dirty = True

    def delete(self, rid):
        self._decode()
        r = self._by_id[rid]
        for rows in (self._ints, self._flts, self._wstrs):
            del rows[r]
        self._by_id = {row[self._id_col]: i for i, row in enumerate(self._ints)}
        self.dirty = True


class Database:
    def __init__(self):
        self._root = []      # (id, payload) for chunks kept verbatim; None payload = rebuilt
        self._order = []     # table IDs in object-pool order
        self._valid = {}     # tableID -> index "valid" byte
        self.tables = {}     # tableID -> Table

    @classmethod
    def load(cls, path):
        with open(path, 'rb') as f:
            buf = f.read()
        db = cls()
        root = list(iter_chunks(buf, 0, len(buf)))
        by_id = {}
        for cid, _, po, ln in root:
            if cid in by_id:
                raise ValueError('duplicate root chunk %d' % cid)
            by_id[cid] = (po, ln)

        # main: tables hash (tableID -> object key), then relations
        mp, ml = by_id[1]
        key_to_tid = {}
        pending = None
        for cid, _, po, ln in iter_chunks(buf, mp, mp + ml):
            if cid != 1:
                continue
            for hid, _, hp, hl in iter_chunks(buf, po, po + ln):
                if hid == 1:
                    pending = struct.unpack_from('<I', buf, hp)[0]
                elif hid == 2:
                    key_to_tid[struct.unpack_from('<I', buf, hp)[0]] = pending
            break

        ip, il = by_id[0]
        index = [struct.unpack_from('<IIB', buf, ip + 9 * i) for i in range(il // 9)]
        dp, dl = by_id[2]
        frames = [(po, ln) for cid, _, po, ln in iter_chunks(buf, dp, dp + dl) if cid == 1]
        if len(frames) != len(index):
            raise ValueError('object index and object data disagree')
        for (type_id, key, valid), (fp, fl) in zip(index, frames):
            if type_id != STORAGE_TYPE_ID:
                raise ValueError('unknown object type 0x%08X' % type_id)
            body = None
            for cid, _, po, ln in iter_chunks(buf, fp, fp + fl):
                if cid == 0 and struct.unpack_from('<I', buf, po)[0] != key:
                    raise ValueError('frame key does not match the index')
                if cid == 1:
                    body = buf[po:po + ln]
            tid = key_to_tid[key]
            db.tables[tid] = Table(tid, key, body)
            db._order.append(tid)
            db._valid[tid] = valid

        # index and object data are rebuilt on save; everything else is kept as is
        db._root = [(cid, None if cid in (0, 2) else buf[po:po + ln]) for cid, _, po, ln in root]
        return db

    def __getitem__(self, table):
        tid = TABLE_IDS[table] if isinstance(table, str) else table
        return self.tables[tid]

    def __contains__(self, table):
        tid = TABLE_IDS.get(table) if isinstance(table, str) else table
        return tid in self.tables

    def to_bytes(self):
        index = b''.join(
            struct.pack('<IIB', STORAGE_TYPE_ID, self.tables[tid].key, self._valid[tid])
            for tid in self._order)
        data = b''.join(
            emit(1, emit(0, struct.pack('<I', self.tables[tid].key)) + emit(1, self.tables[tid].encode()))
            for tid in self._order)
        rebuilt = {0: index, 2: data}
        return b''.join(
            emit(cid, rebuilt[cid] if payload is None else payload)
            for cid, payload in self._root)

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.to_bytes())
