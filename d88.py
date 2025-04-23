from struct import unpack, calcsize, Struct
from enum import IntEnum
from optparse import OptionParser
import sys
import os
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
sector_header_fmt = '<BBBBhBBB5sh'
sector_header_len = calcsize(sector_header_fmt)
sector_header_unpack = Struct(sector_header_fmt).unpack_from

class DiskType(IntEnum):
    DiskType_2D = 0x00
    DiskType_2DD = 0x10
    DiskType_2HD = 0x20
    DiskType_1D = 0x30
    DiskType_1DD = 0x40

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

        if type == DiskType.DiskType_2D:
            print('\t2D')
        elif type == DiskType.DiskType_2DD:
            print('\t2DD')
        elif type == DiskType.DiskType_2HD:
            print('\t2HD')
        elif type == DiskType.DiskType_1D:
            print('\t1D')
        elif type == DiskType.DiskType_1DD:
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

        # try to fingerprint the boot sector
        f.seek(actual_tracks[0])
        raw = f.read(sector_header_len)
        track_header = sector_header_unpack(raw)
        (c, h, r, sector_size, nsec, density, _del, stat, rsrv, size) = track_header
        boot_sector_data = f.read(sector_size_to_bytes(sector_size))  # this seems to be off by one?
        print('Boot sector fingerprint:', boot_sector_data[:0xff])
        # PC-8801: load 256 bytes into $c000 to $cfff, execute them. something special for N-BASIC?
        # X1: https://boukichi.github.io/HuDisk/HuBASIC_Format.html
        # PC-6001: RXR or SYS or IPL???
        if boot_sector_data[:3] == b'SYS' or boot_sector_data[:3] == b'RXR' or boot_sector_data[:3] == b'IPL':
            print('\tPotentially NEC PC-6001/PC-6601')
        if boot_sector_data[0] == 0x01:
            if boot_sector_data[0x0e:0x0e + 3] == b'Sys':
                # grab the label
                x1_label = boot_sector_data[1 : 1 + 13].decode('utf-8')
                print(f'\tPotentially Sharp X1 bootable (label: "{x1_label}")')

# TODO: write a boot sector dumper so we can pass it into z80dasm
    
# Figure out what mode to be in
argp = OptionParser()

argp.add_option('-i', '--get-info', action='store_const', dest='mode', default='get-info', const='get-info', help="Print info on the disk image to the console")
argp.add_option('-1', '--1d', action='store_const', dest='mode', const='1d', help='Change disk type byte to indicate a single-sided, low density (1D) disk image')
argp.add_option('-d', '--1dd', action='store_const', dest='mode', const='1dd', help='Change disk type byte to indicate a single-sided, double density (1DD) disk image')
argp.add_option('-r', '--rename', help='Rename the image friendly name to something else')
argp.add_option('-o', '--output', dest='output_path', help='Where the modified disk image will be written to', default='output.d88')

if len(sys.argv) < 2:
    argp.print_help()
    sys.exit(1)

(options, args) = argp.parse_args()

"""
Change the disk-type byte of the image.

Does not add or remove tracks and sides; this just changes the byte in the header.

Many images are incorrectly described as "1D" (1 sided, 40 track) when they are actually
"1DD" (1 sided, 70-80 track.) This causes problems with the HxC utility and probably
other disk tools as well. Use with caution and operate on a backup.
"""
def change_disk_type_byte(d88_path, output_path, new_disk_type = DiskType.DiskType_1DD):
    with open(d88_path, 'rb') as f:
        image_data = bytearray(f.read())

    image_data[0x1b] = new_disk_type
    with open(output_path, 'wb') as f:
        f.write(image_data)

    print(new_disk_type, ' converted image written to', output_path)

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
elif options.mode == '1d':
    change_disk_type_byte(args[0], options.output_path, DiskType.DiskType_1D)
elif options.mode == '1dd':
    change_disk_type_byte(args[0], options.output_path, DiskType.DiskType_1DD)
elif options.mode == 'get-info':
    # default to get_info
    get_info(args[0])