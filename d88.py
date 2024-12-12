from struct import unpack, calcsize, Struct
import sys
import array

# D88 header:
# 	char title[17];
#   BYTE rsrv[9];
#	BYTE protect;
#	BYTE type;
#	DWORD size;
#	DWORD trkptr[164] - can't decode directly, put in another structure;
d88_header_fmt = '<17s9sBB1i'
d88_header_len = calcsize(d88_header_fmt)
d88_header_unpack = Struct(d88_header_fmt).unpack_from

# D88 track header:
#	BYTE c, h, r, sector_size;
#	WORD nsec;
#	BYTE density, del, stat;
#	BYTE rsrv[5];
#	WORD size;
sector_header_fmt = '<BBBBsBBB5sI'
sector_header_len = calcsize(sector_header_fmt)
sector_header_unpack = Struct(sector_header_fmt).unpack_from

def usage():
    print(sys.argv[0] + " [d88 file]")

if len(sys.argv) < 2:
    usage()
    sys.exit(1)

def sector_size_to_bytes(sector_size):
    if sector_size == 0:
        return 128
    elif sector_size == 1:
        return 256
    elif sector_size == 2:
        return 512
    elif sector_size == 3:
        return 1024
    else:
        raise "Unknown sector size " + sector_size

def density_to_string(density):
    if density == 0:
        return "double"
    elif density == 1:
        return "high"
    else:
        raise "Unknown density " + density + ", could be single?"

with open(sys.argv[1], 'rb') as f:
    raw = f.read(d88_header_len)
    d88_header = d88_header_unpack(raw)
    (title, rsrv, protect, type, size) = d88_header
    tracks = array.array('I')
    tracks.fromfile(f, 164) # trkptr structure
    tracks = tracks.tolist()
    print('Filename:', sys.argv[1])
    print('Title:', title)
    #print 'Tracks:', tracks
    actual_tracks = list(filter(lambda x: x > 0, tracks))
    print('Tracks actually in use:', len(actual_tracks))

    # i suspect it goes TRK - SEC and track headers are the same
    i = 0
    for track_origin in actual_tracks:
        print('Track #', i)

        f.seek(track_origin)
        raw = f.read(sector_header_len)
        track_header = sector_header_unpack(raw)
        #print track_header
        (c, h, r, sector_size, nsec, density, _del, stat, rsrv, size) = track_header
        print('Cylinder', c, 'Head', h, 'Sector', r)
        print('Sector size (in bytes):', sector_size_to_bytes(sector_size))
        print('Density:', density_to_string(density))
        #break # FIXME

        i += 1
