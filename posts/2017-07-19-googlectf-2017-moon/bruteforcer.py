import frida
import time

code = """
'use strict';

var pswd_ptr = Memory.alloc(0x20);
var hash_ptr = Memory.alloc(0x400);

var keygen_ptr = new NativePointer(0x401BF0);
var keygen = new NativeFunction(keygen_ptr, 'int', ['pointer', 'pointer']);

var expected = [
    0x30c7ead9, 0x71077759,
    0x69be4ba0, 0x0cf5578f,
    0x1048ab13, 0x75113631,
    0xdbb6871d, 0xbe35162b,
    0x1c62e982, 0xeb6a7512,
    0xf3274743, 0xfb2e55c8,
    0x18912779, 0xef7a3416,
    0x9a838666, 0xff3994bb,
    0x4d3c6e14, 0xba2d732f,
    0x14414f2c, 0x1cb5d384,
    0x4935aebb, 0xbe3fb206,
    0x343a004e, 0x18a092da,
    0xba02e3c0, 0x96987154,
    0x8ed2c372, 0xeb68d1af,
    0x41152cb3, 0xb61f300e,
    0x3c1a8246, 0x108010d2,
    0x82e16df8, 0xae7bff6c,
    0xb6314d4a, 0xd38b5f97,
    0x79ef2320, 0x8efe3e1b,
    0x69970042, 0x9eae1fa9,
    0x3c036e5d, 0xcbe87d32,
    0xbe1ecfac, 0x2452ddfd,
    0xc704a00e, 0xa24fbc21,
    0x61b7824a, 0x968e9da1,
    0xdb756712, 0xbe3e7b3d,
    0x3420c8f3, 0x3c37dba4,
    0x2072a941, 0xd799ba2e,
    0xebbf8619, 0x1cb59aa4,
    0x9a80ebe0, 0xb61a7974,
    0x1888cb62, 0x341259f6,
    0x2848aad4, 0x4df2b809,
    0x383e0943, 0x7928980f
];

function to_uint32(n) {
    return (n + 0x100000000) & 0xFFFFFFFF;
}

Interceptor.attach(keygen_ptr, {
    onEnter: function (args) {
        for (var i = 0; i < 0x20; i++) {
            console.log("Index " + i + " of 32");
            for (var c = 0; c < 0x100; c++) {
                var valid = false;
                for (var h = 0; h < 0x100; h++) {
                    var maskh = to_uint32(h | (h << 8) | (h << 16) | (h << 24));
                    Memory.writeU8(pswd_ptr.add(i), c);
                    keygen(pswd_ptr, hash_ptr);
                    var dword = Memory.readU32(hash_ptr.add(8*i)) ^ maskh;
                    if (to_uint32(dword) == to_uint32(expected[2*i])) {
                        valid = true;
                        break;
                    }
                }
                if (valid) break;
            }
        }
        console.log(hexdump(pswd_ptr, {length: 32}));
        console.log(Memory.readUtf8String(pswd_ptr, 32));
    }
});
"""

def on_message(message, data):
    print(message)
    
pid = frida.spawn(['moon/moon.exe'])
frida.resume(pid)

session = frida.attach(pid)
script = session.create_script(code)
script.on('message', on_message)
script.load()
