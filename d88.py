from struct import unpack, calcsize, Struct
from optparse import OptionParser
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
    
def get_info(d88_path):
    """
    Print out info on a disk image to the console
    """
    with open(d88_path, 'rb') as f:
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
        print('Type:', hex(type))

        if type == 0x00:
            print('\t2D')
        elif type == 0x10:
            print('\t2DD')
        elif type == 0x20:
            print('\t2HD')
        elif type == 0x30:
            print('\t1D')
        elif type == 0x40:
            print('\t1DD')
        else:
            print('\tWARNING: unknown type')

        print('Size:', size)

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

    
# Figure out what mode to be in
argp = OptionParser()

argp.add_option('-i', '--get-info', action='store_const', dest='mode', default='get-info', const='get-info', help="Print info on the disk image to the console")
argp.add_option('-s', '--single-sided', action='store_const', dest='mode', const='single-sided', help='Convert to a single-sided disk image')
argp.add_option('-r', '--rename', help='Rename the image friendly name to something else')
argp.add_option('-o', '--output', dest='output_path', help='Where the modified disk image will be written to', default='output.d88')

if len(sys.argv) < 2:
    argp.print_help()
    sys.exit(1)

(options, args) = argp.parse_args()

def single_sided_conversion(d88_path, output_path):
    with open(d88_path, 'rb') as f:
        image_data = bytearray(f.read())

    image_data[0x1b] = 0x40
    with open(output_path, 'wb') as f:
        f.write(image_data)

    print('Written to', output_path)

def rename_disk_image(d88_path, new_name, output_path):
    # maximum length check
    if len(new_name) < 1 or len(new_name) > 17:
        print('The friendly name of a disk image must be between 1 and 17 characters long, inclusive.')
        sys.exit(1)
    else:
        # do it but pad it with zeroes
        with open(d88_path, 'rb') as f:
            image_data = bytearray(f.read())
        for i in range(18):
            if i >= len(new_name):
                image_data[i] = 0x00
            else:
                image_data[i] = ord(new_name[i])
        with open(output_path, 'wb') as f:
            f.write(image_data)

if options.rename:
    rename_disk_image(args[0], options.rename, options.output_path)
elif options.mode == 'single-sided':
    single_sided_conversion(args[0], options.output_path)
elif options.mode == 'get-info':
    # default to get_info
    get_info(args[0])