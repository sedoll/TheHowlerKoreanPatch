import lzma, struct, zlib, sys

def read_swf(path):
    d = open(path,'rb').read()
    sig = d[:3]
    ver = d[3]
    flen = struct.unpack('<I', d[4:8])[0]
    if sig == b'FWS':
        body = d[8:]
    elif sig == b'CWS':
        body = zlib.decompress(d[8:])
    elif sig == b'ZWS':
        # 8 hdr, 4 compressed len, 5 lzma props
        props = d[12:17]
        filt = lzma._decode_filter_properties(lzma.FILTER_LZMA1, props)
        dec = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[filt])
        body = dec.decompress(d[17:], max_length=flen-8)
    return ver, body

def parse_header(body):
    nbits = body[0] >> 3
    rect_bytes = (5 + nbits*4 + 7)//8
    pos = rect_bytes + 4  # frame rate + count
    return pos

def iter_tags(body, pos):
    while pos < len(body):
        start = pos
        code_len = struct.unpack('<H', body[pos:pos+2])[0]; pos += 2
        code = code_len >> 6; ln = code_len & 0x3f
        long = False
        if ln == 0x3f:
            ln = struct.unpack('<I', body[pos:pos+4])[0]; pos += 4; long=True
        yield code, start, pos, ln
        pos += ln
        if code == 0: break

def write_tag(code, data, force_long=False):
    if len(data) < 0x3f and not force_long:
        return struct.pack('<H', (code<<6)|len(data)) + data
    return struct.pack('<HI', (code<<6)|0x3f, len(data)) + data

def write_swf(path, ver, body, compress='CWS'):
    flen = len(body) + 8
    if compress == 'FWS':
        out = b'FWS' + bytes([ver]) + struct.pack('<I', flen) + body
    else:
        out = b'CWS' + bytes([ver]) + struct.pack('<I', flen) + zlib.compress(body, 9)
    open(path,'wb').write(out)
