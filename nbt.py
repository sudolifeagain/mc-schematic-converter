"""Minimal NBT (Named Binary Tag) reader/writer for Minecraft schematic files."""

import io
import struct


class NBTReader:
    """Read NBT binary data sequentially."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self, n: int) -> bytes:
        r = self.data[self.pos:self.pos + n]
        self.pos += n
        return r

    def read_ubyte(self) -> int:
        return struct.unpack('>B', self.read(1))[0]

    def read_short(self) -> int:
        return struct.unpack('>h', self.read(2))[0]

    def read_int(self) -> int:
        return struct.unpack('>i', self.read(4))[0]

    def read_long(self) -> int:
        return struct.unpack('>q', self.read(8))[0]

    def read_float(self) -> float:
        return struct.unpack('>f', self.read(4))[0]

    def read_double(self) -> float:
        return struct.unpack('>d', self.read(8))[0]

    def read_string(self) -> str:
        length = struct.unpack('>H', self.read(2))[0]
        return self.read(length).decode('utf-8', errors='replace')

    def read_payload(self, tag_type: int) -> tuple:
        if tag_type == 1:
            return ('byte', self.read_ubyte())
        elif tag_type == 2:
            return ('short', self.read_short())
        elif tag_type == 3:
            return ('int', self.read_int())
        elif tag_type == 4:
            return ('long', self.read_long())
        elif tag_type == 5:
            return ('float', self.read_float())
        elif tag_type == 6:
            return ('double', self.read_double())
        elif tag_type == 7:
            length = self.read_int()
            return ('byte_array', length, self.read(length))
        elif tag_type == 8:
            return ('string', self.read_string())
        elif tag_type == 9:
            list_type = self.read_ubyte()
            count = self.read_int()
            return ('list', list_type, [self.read_payload(list_type) for _ in range(count)])
        elif tag_type == 10:
            entries = []
            while True:
                child_type = self.read_ubyte()
                if child_type == 0:
                    break
                child_name = self.read_string()
                child_val = self.read_payload(child_type)
                entries.append((child_type, child_name, child_val))
            return ('compound', entries)
        elif tag_type == 11:
            length = self.read_int()
            return ('int_array', length, [self.read_int() for _ in range(length)])
        elif tag_type == 12:
            length = self.read_int()
            return ('long_array', length, [self.read_long() for _ in range(length)])
        else:
            raise ValueError(f"Unknown NBT tag type: {tag_type}")


class NBTWriter:
    """Write NBT binary data sequentially."""

    def __init__(self):
        self.buf = io.BytesIO()

    def write(self, data: bytes) -> None:
        self.buf.write(data)

    def write_ubyte(self, v: int) -> None:
        self.write(struct.pack('>B', v))

    def write_short(self, v: int) -> None:
        self.write(struct.pack('>h', v))

    def write_int(self, v: int) -> None:
        self.write(struct.pack('>i', v))

    def write_long(self, v: int) -> None:
        self.write(struct.pack('>q', v))

    def write_float(self, v: float) -> None:
        self.write(struct.pack('>f', v))

    def write_double(self, v: float) -> None:
        self.write(struct.pack('>d', v))

    def write_string(self, s: str) -> None:
        encoded = s.encode('utf-8')
        self.write(struct.pack('>H', len(encoded)))
        self.write(encoded)

    def write_payload(self, tag_type: int, value: tuple) -> None:
        if tag_type == 1:
            self.write_ubyte(value[1])
        elif tag_type == 2:
            self.write_short(value[1])
        elif tag_type == 3:
            self.write_int(value[1])
        elif tag_type == 4:
            self.write_long(value[1])
        elif tag_type == 5:
            self.write_float(value[1])
        elif tag_type == 6:
            self.write_double(value[1])
        elif tag_type == 7:
            self.write_int(value[1])
            self.write(value[2])
        elif tag_type == 8:
            self.write_string(value[1])
        elif tag_type == 9:
            self.write_ubyte(value[1])
            self.write_int(len(value[2]))
            for item in value[2]:
                self.write_payload(value[1], item)
        elif tag_type == 10:
            for ct, cn, cv in value[1]:
                self.write_ubyte(ct)
                self.write_string(cn)
                self.write_payload(ct, cv)
            self.write_ubyte(0)
        elif tag_type == 11:
            self.write_int(value[1])
            for i in value[2]:
                self.write_int(i)
        elif tag_type == 12:
            self.write_int(value[1])
            for i in value[2]:
                self.write_long(i)

    def get_bytes(self) -> bytes:
        return self.buf.getvalue()


def find_tag(compound: tuple, name: str) -> tuple:
    """Find a named tag within a compound. Returns (tag_type, value) or (None, None)."""
    for ct, cn, cv in compound[1]:
        if cn == name:
            return ct, cv
    return None, None
