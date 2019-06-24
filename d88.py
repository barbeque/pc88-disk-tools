from struct import unpack, calcsize, Struct
import sys

# D88 header:
# 	char title[17];
#   BYTE rsrv[9];
#	BYTE protect;
#	BYTE type;
#	DWORD size;
#	DWORD trkptr[164];
d88_header_fmt = '<17s9s1s1s1i164i'
d88_header_len = calcsize(d88_header_fmt)
d88_header_unpack = Struct(d88_header_fmt).unpack_from

# D88 track header:
#	BYTE c, h, r, sector_size;
#	WORD nsec;
#	BYTE density, del, stat;
#	BYTE rsrv[5];
#	WORD size;
track_header_fmt = '<ccccsccc5cs'
track_header_len = calcsize(track_header_fmt)
track_header_unpack = Struct(track_header_fmt).unpack_from

def usage():
    print sys.argv[0] + " [d88 file]"

if len(sys.argv) < 2:
    usage()
    sys.exit(1)

with open(sys.argv[1], 'rb') as f:
    raw = f.read(d88_header_len)
    header = d88_header_unpack(raw)
    print header
