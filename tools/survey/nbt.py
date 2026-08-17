"""Minimal Anvil (.mca) + NBT reader. Stdlib only."""
import struct, zlib, gzip, io, os

TAG_END=0; TAG_BYTE=1; TAG_SHORT=2; TAG_INT=3; TAG_LONG=4; TAG_FLOAT=5
TAG_DOUBLE=6; TAG_BYTE_ARRAY=7; TAG_STRING=8; TAG_LIST=9; TAG_COMPOUND=10
TAG_INT_ARRAY=11; TAG_LONG_ARRAY=12


class R:
    __slots__ = ("b", "i")
    def __init__(self, b):
        self.b = b; self.i = 0
    def u1(self):
        v = self.b[self.i]; self.i += 1; return v
    def i1(self):
        v = struct.unpack_from(">b", self.b, self.i)[0]; self.i += 1; return v
    def i2(self):
        v = struct.unpack_from(">h", self.b, self.i)[0]; self.i += 2; return v
    def u2(self):
        v = struct.unpack_from(">H", self.b, self.i)[0]; self.i += 2; return v
    def i4(self):
        v = struct.unpack_from(">i", self.b, self.i)[0]; self.i += 4; return v
    def i8(self):
        v = struct.unpack_from(">q", self.b, self.i)[0]; self.i += 8; return v
    def f4(self):
        v = struct.unpack_from(">f", self.b, self.i)[0]; self.i += 4; return v
    def f8(self):
        v = struct.unpack_from(">d", self.b, self.i)[0]; self.i += 8; return v
    def s(self):
        n = self.u2(); v = self.b[self.i:self.i+n].decode("utf-8", "replace"); self.i += n; return v


def _payload(r, t):
    if t == TAG_BYTE: return r.i1()
    if t == TAG_SHORT: return r.i2()
    if t == TAG_INT: return r.i4()
    if t == TAG_LONG: return r.i8()
    if t == TAG_FLOAT: return r.f4()
    if t == TAG_DOUBLE: return r.f8()
    if t == TAG_BYTE_ARRAY:
        n = r.i4(); v = r.b[r.i:r.i+n]; r.i += n; return v
    if t == TAG_STRING: return r.s()
    if t == TAG_LIST:
        et = r.u1(); n = r.i4()
        if n <= 0: return []
        return [_payload(r, et) for _ in range(n)]
    if t == TAG_COMPOUND:
        d = {}
        while True:
            tt = r.u1()
            if tt == TAG_END: return d
            nm = r.s()
            d[nm] = _payload(r, tt)
    if t == TAG_INT_ARRAY:
        n = r.i4(); v = struct.unpack_from(">%di" % n, r.b, r.i); r.i += 4*n; return list(v)
    if t == TAG_LONG_ARRAY:
        n = r.i4(); v = struct.unpack_from(">%dq" % n, r.b, r.i); r.i += 8*n; return list(v)
    raise ValueError("bad tag %d" % t)


def parse_nbt(data):
    r = R(data)
    t = r.u1()
    if t == TAG_END: return {}
    r.s()  # root name
    return _payload(r, t)


def decompress(ctype, raw):
    if ctype == 1: return gzip.decompress(raw)
    if ctype == 2: return zlib.decompress(raw)
    if ctype == 3: return raw
    if ctype == 4:
        import lz4.block  # not expected
        return lz4.block.decompress(raw)
    raise ValueError("compression %d" % ctype)


def iter_chunks(path):
    """yield (cx_local, cz_local, root_compound)"""
    sz = os.path.getsize(path)
    if sz < 8192: return
    with open(path, "rb") as f:
        header = f.read(4096)
        for idx in range(1024):
            off = (header[idx*4] << 16) | (header[idx*4+1] << 8) | header[idx*4+2]
            cnt = header[idx*4+3]
            if off == 0 or cnt == 0: continue
            pos = off * 4096
            if pos + 5 > sz: continue
            f.seek(pos)
            hdr = f.read(5)
            if len(hdr) < 5: continue
            length = struct.unpack(">i", hdr[:4])[0]
            ctype = hdr[4]
            if length <= 0 or length > cnt*4096: continue
            raw = f.read(length - 1)
            try:
                nbt = parse_nbt(decompress(ctype, raw))
            except Exception:
                continue
            yield idx % 32, idx // 32, nbt


def unpack_heightmap(longs):
    """256 entries, 9 bits each, non-crossing packing -> list of 256 ints"""
    if not longs: return None
    out = []
    per = 64 // 9  # 7
    for L in longs:
        u = L & 0xFFFFFFFFFFFFFFFF
        for k in range(per):
            out.append((u >> (9*k)) & 0x1FF)
            if len(out) == 256: return out
    return out if len(out) == 256 else None


def unpack_indices(longs, nbits, count):
    """non-crossing packed palette indices"""
    if nbits == 0: return [0]*count
    per = 64 // nbits
    mask = (1 << nbits) - 1
    out = []
    for L in longs:
        u = L & 0xFFFFFFFFFFFFFFFF
        for k in range(per):
            out.append((u >> (nbits*k)) & mask)
            if len(out) == count: return out
    return out
