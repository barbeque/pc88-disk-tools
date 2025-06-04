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

# D88 sector header:
#	BYTE c, h, r, sector_size;
#	WORD nsec;
#	BYTE density, del, stat;
#	BYTE rsrv[5];
#	WORD size;
sector_header_fmt = '<BBBBhBBB5sh'
sector_header_len = calcsize(sector_header_fmt)
sector_header_unpack = Struct(sector_header_fmt).unpack_from

# length should be 0x10

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
    file_size = os.path.getsize(d88_path)
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

        is_double_sided = True

        if type == DiskType.DiskType_2D:
            print('\t2D')
        elif type == DiskType.DiskType_2DD:
            print('\t2DD')
        elif type == DiskType.DiskType_2HD:
            print('\t2HD')
        elif type == DiskType.DiskType_1D:
            is_double_sided = False
            print('\t1D')
        elif type == DiskType.DiskType_1DD:
            is_double_sided = False
            print('\t1DD')
        else:
            print('\tWARNING: unknown type')

        if is_double_sided:
            print('Tracks per side (guessed:)', len(actual_tracks) // 2)

        print('Size:', size)
        print('File size:', file_size)

        if size != file_size:
            print('WARNING: actual file size and the size claimed by the d88 header do not match. This might be a corrupt image, or not a d88 at all. Proceed with caution.')

        # there are no 'track headers,' tracks are just a collection of sectors one after the other
        # and usually it goes "side 0 side 1 side 0 side 1 side 0 side 1 ..." for double-sided
        i = 0
        for track_origin in actual_tracks:
            print('Track pointer index:', i)

            if track_origin > file_size:
                print('WARNING: Track index:', i, 'has illegal offset off the end of the disk (offset=', track_origin, 'disk_size=', file_size, '). This may not be a D88 image file!')
                continue

            f.seek(track_origin)
            raw = f.read(sector_header_len)
            track_header = sector_header_unpack(raw)
            #print track_header
            (c, h, r, sector_size, nsec, density, _del, stat, rsrv, size) = track_header
            print('Cylinder', c, 'Head', h, 'Sector', r, 'Offset in file', track_origin)
            sector_size_bytes = sector_size_to_bytes(sector_size)
            print('Sector size (in bytes):', sector_size_bytes)
            print('Number of sectors:', nsec)
            print('Density:', density_to_string(density))

            # the mystery is solved
            #print('I think next track offset is at:', (track_origin + (nsec * sector_size_bytes) + (nsec * sector_header_len)))

            i += 1

"""
Dumps the first sector of the disk to a file for further analysis.

Does some basic fingerprinting of the disk to try and figure out what system it came from.
"""
def dump_boot_sector(d88_path, output_path = 'boot-sector.bin'):
    with open(d88_path, 'rb') as f:
        raw = f.read(d88_header_len)
        d88_header = d88_header_unpack(raw)
        (_title, _rsrv, _protect, _type, _size) = d88_header

        tracks = array.array('I')
        tracks.fromfile(f, 164) # trkptr structure
        tracks = tracks.tolist()
        actual_tracks = list(filter(lambda x: x > 0, tracks))

        # jump to first track
        f.seek(actual_tracks[0])

        # try to fingerprint the boot sector
        raw = f.read(sector_header_len)
        track_header = sector_header_unpack(raw)
        (c, h, r, sector_size, nsec, density, _del, stat, rsrv, size) = track_header
        boot_sector_data = f.read(sector_size_to_bytes(sector_size))
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

        # anyway dump the entire thing now
        with open(output_path, 'wb') as o:
            o.write(boot_sector_data)
            print(f'Wrote {len(boot_sector_data)} bytes of boot sector to dump file "{output_path}"')
    
# Figure out what mode to be in
argp = OptionParser()

argp.add_option('-i', '--get-info', action='store_const', dest='mode', default='get-info', const='get-info', help="Print info on the disk image to the console")
argp.add_option('-f', '--flatten', action='store_const', dest='mode', const='flatten', help="Convert the d88 disk image into a flat, raw IMG sector image")
argp.add_option('-b', '--boot-dump', action='store_const', dest='mode', const='dump-boot-sector', help='Analyze the boot sector and extract it to a file')
argp.add_option('-1', '--1d', action='store_const', dest='mode', const='1d', help='Change disk type byte to indicate a single-sided, low density (1D) disk image')
argp.add_option('-d', '--1dd', action='store_const', dest='mode', const='1dd', help='Change disk type byte to indicate a single-sided, double density (1DD) disk image')
argp.add_option('-r', '--rename', help='Rename the image friendly name to something else')
argp.add_option('-o', '--output', dest='output_path', help='Where the output of the process (modified disk, boot sector, etc) will be written to', default='output.d88')

argp.add_option('-v', '--verbose', action='store_const', dest='verbose', const=True, default=False, help='Express more information in the console about the operation of the tool')

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

def convert_to_img(d88_path, verbose, output_img_path = 'output.img'):
    file_size = os.path.getsize(d88_path)

    output = open(output_img_path, 'wb')

    with open(d88_path, 'rb') as f:
        raw = f.read(d88_header_len)
        d88_header = d88_header_unpack(raw)
        (title, rsrv, protect, type, size) = d88_header

        tracks = array.array('I')
        tracks.fromfile(f, 164) # trkptr structure
        tracks = tracks.tolist()
        actual_tracks = list(filter(lambda x: x > 0, tracks))

        if verbose:
            print(f'Flattening {d88_path} ({len(actual_tracks)} track(s)), saving as {output_img_path}...')
        
        # there are no 'track headers,' tracks are just a collection of sectors one after the other
        i = 0
        for track_origin in actual_tracks:
            # print('Track #', i, 'Origin:', track_origin)

            if track_origin > file_size:
                print('WARNING: Track #', i, 'has illegal offset off the end of the disk (offset=', track_origin, 'disk_size=', file_size, '). This may not be a D88 image file!')
                continue

            f.seek(track_origin)
            raw = f.read(sector_header_len)
            sector_header = sector_header_unpack(raw)
            #print track_header
            (c, h, r, sector_size_enum, nsec, density, _del, stat, rsrv, size) = sector_header
            sector_size_in_bytes = sector_size_to_bytes(sector_size_enum)

            # it's a little weird that "number of sectors" is stored in the sector header,
            # but now that we know how many sectors to expect we can rewind to the start of
            # the track and start reading them all out
            f.seek(track_origin)

            if(verbose):
                print('Track', i, 'offset in new file:', output.tell())

            # read all sectors for this track
            for sector_index in range(nsec):
                if(verbose):
                    print('  Sector', i, 'offset in new file:', output.tell())

                sector_header_raw = f.read(sector_header_len)
                sector_header_data = sector_header_unpack(raw)
                # TODO: Detect changes in density, sector_size, nsec, etc from the other tracks
                # now we read the header, so read the rest of the sector
                #print('Reading sector of size', sector_size_in_bytes)
                sector_contents = f.read(sector_size_in_bytes)
                # write it to the output
                output.write(sector_contents)

            if i + 1 < len(actual_tracks):
                # PARANOID: check to make sure our current offset is lined up with the head of the next track in line
                #print('Current offset:', f.tell(), 'Next track at:', actual_tracks[i+1])
                assert(f.tell() == actual_tracks[i+1])

            i += 1

    output.close()

    if verbose:
        print(f'Wrote {len(actual_tracks)} track(s) to "{output_img_path}".')

if options.rename:
    rename_disk_image(args[0], options.rename, options.output_path)
elif options.mode == 'flatten':
    defaults = argp.get_default_values()
    if options.output_path == defaults.output_path:
        convert_to_img(args[0], options.verbose)
    else:
        convert_to_img(args[0], options.verbose, options.output_path)
elif options.mode == 'dump-boot-sector':
    # the default output path ends in D88, so we shouldn't do that for the boot sector
    # (it's not actually an image, just a chunk of one)
    defaults = argp.get_default_values()
    if options.output_path == defaults.output_path:
        dump_boot_sector(args[0])
    else:
        dump_boot_sector(args[0], options.output_path)
elif options.mode == '1d':
    change_disk_type_byte(args[0], options.output_path, DiskType.DiskType_1D)
elif options.mode == '1dd':
    change_disk_type_byte(args[0], options.output_path, DiskType.DiskType_1DD)
elif options.mode == 'get-info':
    # default to get_info
    get_info(args[0])