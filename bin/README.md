When using the BBC Micro, I use
[BeebLink](https://github.com/tom-seddon/beeblink), a package that
lets your PC act as a file server for the BBC Micro. This way, I can
use the PC to edit and assemble files for immediate use on the BBC
Micro.

BeebLink stores each BBC file as a loose file on your PC, plus an
associated .inf file that stores file attributes, so the tools here
are oriented more towards this way of working. (There are also
[other tools that work with this format](https://www.stairwaytohell.com/essentials/index.html?page=homepage).)

For more info, run each with `-h` on the command line.

Scripts are for Python 3 unless noted. (I am slowly working through
converting them all.)

# BBCBasicToText

Convert tokenized BBC BASIC files to text. Originally by
[Matt Godbolt](https://github.com/mattgodbolt). I updated it with
support for line numbers and BASIC II.

Execute with `-h` to get a help page.

(If you want to use this to produce output for use with `*EXEC` on the
BBC, use the `--cr` option.)

Note: `BBCBasicToText` can be used in a pipeline, but when used this
way it might not work properly on Windows as it doesn't reopen stdin
in binary mode. (This will get fixed at some point, I promise...)

## Using with git

You can use `BBCBasicToText` as a git diff driver, so you can get text
diffs of changes to tokenized BASIC code.

To do this, ensure `BBCBasicToText` is on `PATH`. Then edit the
`.git/config` file in your working copy, and add something like this
to the end:

    [diff "bbcbasic"]
        textconv = BBCBasicToText -n

(The `-n` tells it to operate in a diff-friendly mode: no leading line
numbers, and line numbers in the program (e.g., `GOTO`, `RESTORE`)
replaced with numbered `@xxxx` labels.)

Then use the
[`.gitattributes`](http://git-scm.com/docs/gitattributes])file to
specify the diff driver for your BBC BASIC files:

    $.MYBAS diff=bbcbasic
    *.bbcbasic diff=bbcbasic

You can use wildcards (as in this example) if your BBC BASIC file
names conform to a pattern. There's no standard pattern, though, so
you may have to just list them out in the `.gitattributes` file in
each folder. Either way, it's worth the effort!

# dump_bbc_rom_info

Simple tool that scans sideways ROM headers and prints info to stdout.
I used this to have a quick look at [Wouter Scholten's monster ROM
archive](http://wouter.bbcmicro.net/bbc/bbc-software.html).

# find_unknown_roms

Search paths for ROMs not present in TobyLobster's BBC Micro ROM
Library: https://tobylobster.github.io/rom_library/ (stardot thread:
https://www.stardot.org.uk/forums/viewtopic.php?t=29831)

To use, download metadata.json from the library, then run the command,
supplying paths of folders to search in, and the path to metadata.json
if not in the working folder (run with `-h` to verify exact syntax).
ROM files will be found, cross-referenced against the library, and
paths to any unknown ones printed along with the ROM title.

The script will attempt to concatenate 16 KB ROMs that look like they
might be a larger ROM that was dumped in parts, in the hope this will
find a match.

# ssd_create

Build a single-sided disc image from .inf files.

Supply list of files on the command line. Files that have a
corresponding .inf file are assumed to be BBC files, and other files
are ignored.

Files are added to the disc image in the order given, with the first
file given starting at sector 2. You can combine manual lists of files
with wildcards, if you want to add a whole folder's-worth of files,
but only some need to go in order; if the list includes the same file
multiple times, only the first occurrence counts.

# ssd_extract

Convert a SSD or DSD disc image into a folder of .inf files suitable
for use with BeebLink. Supply name of disk on command line; it will
create a BeebLink-compatible folder in the same folder, named after
the disc image. Alternatively, specify `-0` or `-2` to have it output
files from side 0 or 2 straight into the folder specified.

Specify the `-b` switch to have it find tokenized BBC BASIC files,
convert them to text with `BBCBasicToText.py`, and save them to a
separate `raw` folder.

# bbc2png

Convert a BBC screen dump into an image.

Supply name on command line of dump of screen RAM (as saved by, e.g.,
`*SAVE X FFFF3000+5000`) and MODE the dump was taken from. Use `-o` to
specify output file. Specify `-r` to have image resized to 640x512,
making the image look reasonable on a PC. Specify `-p` and a list of
physical colour numbers, in order, to specify the palette (e.g., for a
MODE4 grab, `-p 13` to specify yellow on red.)

(Maybe one day I'll figure out how to make animated GIFs so that
flashing colours can be supported.)

# smload_join (Python 2.7)

Join a service ROM and
[relocatable modules](http://mdfs.net/Software/BBC/Modules/ModWriting),
creating a new ROM image.

(Note that while this will consume modules produced by JGH's tools, I
haven't tested its interaction with `*SMLoad` (etc.) - I just use this
to create new standalone ROMs.)

[Example use](https://github.com/tom-seddon/beeblink/blob/5c13bcc5fd6d07d2d656df4129ef1fe694723fe8/rom/Makefile#L16).

# smload_make_reloc (Python 2.7)

Make a
[relocatable module](http://mdfs.net/Software/BBC/Modules/ModWriting)
from a service ROM.

Assemble the service ROM twice, once at $8000 (a valid ROM image that
you might actually use) and once at $8100 (not a valid ROM), and
supply both files to this tool. The output is a valid ROM with a
relocation table that can be used by `smload_join`, and ought to work
with [JGH's tools](http://mdfs.net/Software/BBC/Modules/) too.

[Example use](https://github.com/tom-seddon/startup_rom/blob/4193e31aff25d22b59f6ab099613ae7cedbe011c/Makefile#L13).

# text2bbc, bbc2text (Python 2.7)

Along the lines of [`dos2unix`](https://linux.die.net/man/1/dos2unix),
convert files between modern standard line endings (lines ending with
LF, or, on Windows, CR+LF) and BBC-style ones (lines ending with CR).

# adf_create (Python 2.7)

Create an ADFS disk image from a set of DFS-style .inf files.

Files in `$` will be placed in the ADFS root, and additional
directories will be created to hold DFS files in other directories as
required.

Specify file order in the same way as `ssd_create.py`.

# adf_extract

Extract an ADFS disk image to .inf files.

The directory structure of the ADFS disk will be reproduced. PC
folders will be created corresponding to each ADFS directory, with
data/.inf files created in each PC folder corresponding to the ADFS
files.

The .inf format isn't ADFS-minded, so note that the conversion process
may be lossy. ADFS file names will be stored in the .inf files, so
they can always be reconstructed, but there is no similar mechanism
for ADFS directory names, which may become lost if they use chars not
supported by modern PC filing systems.

# png2bbc

Create a BBC bitmap screen memory image from a .png file.

The .png file should contain only valid BBC colours - (0,0,0),
(255,0,0), etc. - but png2bbc will try to do its best, within the
constraints of the mode specified.

# prg2bbc

Convert a C64 PRG file, as output by
[64tass](http://tass64.sourceforge.net/), into a BBC data/inf pair.

The PRG file's load address (stored in the first 2 bytes of the PRG
file) will be used as the BBC file's load address and execution
address, and the output file name will be used to generate the BBC
name in the .inf file.

## Separate execution address

If you don't mind a small amount of hassle, you can have a separate
execution address. Use a `.word` to get 64tass to output the desired
execution address in the first 2 bytes of the output, and supply
`--execution-address` on the prg2bbc command line.

The PRG file (which will be even more invalid in C64 terms than usual)
will then contain the 2-byte load address in the first 2 bytes, and
the 2-byte execution address in the second byte.

Because you've added an extra 2 bytes to the output, the ORG will have
to be 2 bytes lower. prg2bbc will cancel this out by adding 2 to the
PRG's load address.

This is easier to actually use than it is to explain. For an example,
see
https://github.com/tom-seddon/256_bytes/blob/f74a79e2ab02cfba2ccb5481a61632f12e00e363/nova_2023_1.s65#L12 -
note the `-2` in the org, and the `.word entry` that specifies the
execution entry point.

(Makefile:
https://github.com/tom-seddon/256_bytes/blob/f74a79e2ab02cfba2ccb5481a61632f12e00e363/Makefile#L63)

# mos_switch, mos_program _(Unix only)_ (Python 2.7)

Operate a MOS switcher addon.

`mos_switch` selects the bank to use, and `mos_program` programs a
bank.

# bbccat

Print an Acorn-style text file (with CR or LF CR line endings) to
stdout.

# tube_relocation

Manage
[MOS 3.50 Tube language ROM relocation data](https://github.com/bitshifters/bbc-documents/blob/b831539a1fdda44f8e43be03185f8390c035389b/Master128/MOS350.txt#L731).

The following sub-commands are available. The `-o` options are
optional; if not specified, the data will be processed (including
consistency checks and so on) but no files will be saved.

## `tube_relocation info ROM`

Print relevant info about sideways ROM `ROM`, including any Tube
relocation-related info.

`Tube relocation bitmap bank` will be shown as `+N` if the bank is
relative.

## `tube_relocation extract [-o BITMAP] ROM BITMAP-ROM`

Extract the Tube relocation bitmap for a sideways ROM, saving it to
`BITMAP`. `ROM` is the relocatable language ROM, and `BITMAP-ROM` is
the data for the ROM that contains its bitmap (which can be the same
file).

## `tube_relocate relocate [-o ROM] ROM BITMAP`

Relocate `ROM` to its Tube address, given the relocation bitmap
`BITMAP`. The output is intended to be identical to the ROM image that
ends up copied to the 2nd processor.

(This is provided for debugging purposes only. The relocated ROM may
not be usable.)

## `tube_relocation set [-o OUTPUT-ROM OUTPUT-BITMAP-ROM] ROM BITMAP BANK`

Set up Tube relocation data for a ROM, with the bitmap data held in a
2nd ROM.

`ROM` is the relocatable ROM. It must have the relocatable bit set in
the header, a Tube relocation address, and a relocatable descriptor
(which will be overwritten).

`BITMAP` is the Tube relocation bitmap, as produced by, e.g.,
`tube_relocation extract`.

`BANK` is the bank that the Tube relocation bitmap will be stored in,
relative to whichever bank the language ROM will go in.

There are two output files: `OUTPUT-ROM` is the file to save the
modified ROM to, and `OUTPUT-BITMAP-ROM` is the file to append the
bitmap data to. (These must be different files. It isn't currently
possible to add the bitmap to the relocatable ROM itself.)

The previous length of `OUTPUT-BITMAP-ROM` (or 0 if it doesn't exist)
is used to calculate the address for the bitmap data.

Note that the relocation bitmap will occupy 1 more byte in
`OUTPUT-BITMAP-ROM` than it does on disk. (The extra byte is booked in
case the bitmap needs to become larger to accommodate the changes to
the descriptor. This is often unnecessary, but `tube_relocation` does
not currently sweat the waste.)

### Inserting bitmap data into a ROM

The default assumption is that the bitmap ROM has spare space at the
end, and the bitmap can be appended. If it's actually got spare space
in the middle, or you just generally want the bitmap somewhere in
particular, use `--bitmap-address ADDR` (address in sideways ROM
area - i.e., 0x8000 to 0xbfff) or `--bitmap-offset OFFSET` (offset in
file - i.e., 0 to 16383) to specify where the bitmap should start.

The file will be extended, or existing bytes overwritten, as
necessary. There are no checks other than basic bounds checks.

Note that the relocation bitmap will occupy 1 more byte in
`OUTPUT-BITMAP-ROM` than it does on disk (see above) - this must be
borne in mind if trying to insert multiple relocation tables into a
ROM.

## `tube_relocation create [-o OUTPUT-BITMAP] ROM ROM2`

Create a Tube relocation bitmap from two ROMs:

- `ROM`: language part assembled to run at its unrelocated address,
  Tube relocation address set to the desired value, empty relocation
  descriptor
  
- `ROM2`: language part assembled to run it some other address, Tube
  relocation address set to the desired value, empty relocation
  descriptor
  
The differences between the two ROMs will be used to generate a
relocation bitmap, written to `OUTPUT-BITMAP`.

## `tube_relocation set-multi [--set-multi] [--begin=ADDR] [--end=ADDR] [-b BITMAP-ROM BANK] [-r ROM BITMAP]` 

Set up Tube relocation data for multiple ROMs, writing the bitmaps
into a contiguous region in a bitmap ROM, checking for region
overflow, and fixing up each ROM's descriptor as required.

Unlike the other operations, this one operates in-place, to avoid
making the command line even fiddlier than it is already. But, broadly
in keeping with the other operations, no files are modified by
default; supply `--set-multi` to tell it to actually do the thing.

`--begin` and `--end` specify the region to store bitmaps in. The
begin is inclusive, default 0x8000; the end is exclusive, default
0xc000.

`-b` specifies the ROM to store the bitmaps in, and the bank it will
go in. No checking of the existing contents is performed! The
specified region will be overwritten with the bitmap data, and you
have to be sure that this won't be a problem.

Each `-r ROM BITMAP` specifies a ROM image and its corresponding
bitmap.

(If `-b` is not specified, a default bank of 0 is used, and processing
will continue as normal, so region exhaustion can be tested. You must
specify `-b` if using `--set-multi` though.)

## `tube_relocation unset [-o OUTPUT-ROM] ROM`

Unset the Tube relocation bit in the header of `ROM`. Save the output
to `OUTPUT-ROM`.
