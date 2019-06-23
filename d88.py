from struct import unpack, calcsize

# D88 header:
# 	char title[17];
#   BYTE rsrv[9];
#	BYTE protect;
#	BYTE type;
#	DWORD size;
#	DWORD trkptr[164];
d88_header_fmt = '17s9s1s1s<i<164i'

# D88 track header:
#	BYTE c, h, r, sector_size;
#	WORD nsec;
#	BYTE density, del, stat;
#	BYTE rsrv[5];
#	WORD size;
