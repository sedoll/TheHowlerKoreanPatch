import struct
def u30(b, p):
    r = 0; sh = 0
    while True:
        x = b[p]; p += 1
        r |= (x & 0x7f) << sh; sh += 7
        if not (x & 0x80) or sh >= 35: break
    return r, p
def enc_u30(v):
    out = bytearray()
    while True:
        x = v & 0x7f; v >>= 7
        if v: out.append(x|0x80)
        else: out.append(x); break
    return bytes(out)

def parse_strings(abc):
    """abc = bytes starting at minor/major version. returns (strings, (start,end) of string pool, offsets)"""
    p = 4
    n, p = u30(abc, p)
    for _ in range(max(n-1,0)): _, p = u30(abc, p)
    n, p = u30(abc, p)
    for _ in range(max(n-1,0)): _, p = u30(abc, p)
    n, p = u30(abc, p)
    p += 8*max(n-1,0)
    sp_start = p
    n, p = u30(abc, p)
    strs = ['']
    for _ in range(max(n-1,0)):
        l, p = u30(abc, p)
        strs.append(abc[p:p+l].decode('utf-8', 'replace')); p += l
    return strs, sp_start, p

def build_string_pool(strs):
    out = bytearray(enc_u30(len(strs)))
    for s in strs[1:]:
        b = s.encode('utf-8'); out += enc_u30(len(b)) + b
    return bytes(out)

def name_string_refs(abc, sp_end):
    """string indices referenced by namespaces and multinames"""
    p = sp_end; refs=set()
    n, p = u30(abc, p)
    for _ in range(max(n-1,0)):
        p += 1; s, p = u30(abc, p); refs.add(s)
    n, p = u30(abc, p)
    for _ in range(max(n-1,0)):
        c, p = u30(abc, p)
        for _ in range(c): _, p = u30(abc, p)
    n, p = u30(abc, p)
    for _ in range(max(n-1,0)):
        k = abc[p]; p += 1
        if k in (0x07,0x0D):
            _, p = u30(abc,p); s, p = u30(abc,p); refs.add(s)
        elif k in (0x0F,0x10):
            s, p = u30(abc,p); refs.add(s)
        elif k in (0x11,0x12): pass
        elif k in (0x09,0x0E):
            s, p = u30(abc,p); refs.add(s); _, p = u30(abc,p)
        elif k in (0x1B,0x1C):
            _, p = u30(abc,p)
        elif k == 0x1D:
            _, p = u30(abc,p); c, p = u30(abc,p)
            for _ in range(c): _, p = u30(abc,p)
        else: raise Exception('mn kind %x'%k)
    return refs, p
