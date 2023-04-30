A tester for BBC BASIC-related scripts - currently, BBCBasicToText.py.
Assembles a corpus of BBC BASIC files, and runs some tests on them.

Prerequisites: [`basictool`](https://github.com/ZornsLemma/basictool)
on the path.

Supply folder names on command line - they will be searched for BBC
BASIC files. And/or use `-b` to specify the path to your BeebLink
config json to have it search your BeebLink volumes.

(Beeb disk images are not supported.)

For each unique file found, it makes some files in the output folder,
named after the original file's SHA256 hash:

- `.original.dat` - the original file
- `.stripped.dat` - the BBC BASIC-only prefix of the file (usually the
  same as the original, but it's not unknown for BASIC programs to
  contain extra data after `TOP`)
- `.BBCBasicToText.basic4.txt` - the result of running BBCBasicToText
  on the original file, with the `--codes --perfect` options
- `.basictool.basic4.txt` - the result of running basictool on the
  original file, with the `--ascii --input-tokenised` options
- `.BBCBasicToText.basic2.txt`, `.basictool.basic2.txt` - as above,
  but with the options that direct the tools to reproduce BASIC II
  behaviour rather than BASIC IV
  
Any mismatches between the basictool and BBCBasicToText outputs are
flagged.

# Example use

How I run this on my laptop:

    ./test_BBCBasic_tools.py -b ~/github/beeblink/server/beeblink_config.json

In my case, it finds 4,295 BBC BASIC files, and no mismatches.
