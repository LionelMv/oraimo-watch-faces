#!/usr/bin/env python3
"""Send a TOPSTEP watch-face .bin to an oraimo Watch 5R Pro over BLE (BlueZ D-Bus).
Replicates the sequence captured from the Oraimo Health app. Aborts on any unexpected reply."""
import sys, struct, time, dbus, dbus.mainloop.glib
from gi.repository import GLib

MAC = "54:88:00:00:9D:07"
USER_ID = bytes.fromhex("37663938643238313736363434653230393539313461343436343862") + bytes(4)   # exact 32 bytes from captured login frame
UUID_CMD_W, UUID_CMD_N = "0000ff02-0000-1000-8000-00805f9b34fb", "0000ff03-0000-1000-8000-00805f9b34fb"
UUID_BLK_W, UUID_BLK_N = "0000ffb1-0000-1000-8000-00805f9b34fb", "0000ffb2-0000-1000-8000-00805f9b34fb"

def arc(d):
    c = 0
    for b in d:
        c ^= b
        for _ in range(8): c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
ctx = GLib.MainContext.default()
devpath = "/org/bluez/hci0/dev_" + MAC.replace(":", "_")
dev = dbus.Interface(bus.get_object("org.bluez", devpath), "org.bluez.Device1")
props = dbus.Interface(bus.get_object("org.bluez", devpath), "org.freedesktop.DBus.Properties")

def pump(sec):
    end = time.time() + sec
    while time.time() < end: ctx.iteration(False); time.sleep(0.002)

def wait(cond, timeout, what):
    end = time.time() + timeout
    while time.time() < end:
        ctx.iteration(False)
        r = cond()
        if r: return r
        time.sleep(0.002)
    raise SystemExit(f"ABORT: timeout waiting for {what}")

# ---- connect
if not props.Get("org.bluez.Device1", "Connected"):
    log("connecting…"); dev.Connect()
wait(lambda: props.Get("org.bluez.Device1", "ServicesResolved"), 20, "services")
om = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
chars = {}
for p, ifs in om.GetManagedObjects().items():
    c = ifs.get("org.bluez.GattCharacteristic1")
    if p.startswith(devpath + "/") and c: chars[str(c["UUID"])] = (p, c)
def ch(u): return dbus.Interface(bus.get_object("org.bluez", chars[u][0]), "org.bluez.GattCharacteristic1")
mtu = int(chars[UUID_BLK_W][1].get("MTU", 23)); log("ATT MTU", mtu)

# ---- notification handling
cmd_buf = bytearray(); cmd_frames = []; blk_msgs = []
def on_cmd(iface, changed, inv):
    if "Value" not in changed: return
    cmd_buf.extend(bytes(changed["Value"]))
    while len(cmd_buf) >= 8 and cmd_buf[0] == 0xAB:
        ln = struct.unpack_from(">H", cmd_buf, 2)[0]
        if len(cmd_buf) < 8 + ln: break
        fr = bytes(cmd_buf[:8 + ln]); del cmd_buf[:8 + ln]
        cmd_frames.append(fr)
        if fr[1] & 0x10 == 0:   # data frame from watch -> ack it
            ch(UUID_CMD_W).WriteValue(dbus.Array(b"\xab\x10\x00\x00\x00\x00" + fr[6:8], "y"), {"type": "request"})
    if cmd_buf and cmd_buf[0] != 0xAB: cmd_buf.clear()
def on_blk(iface, changed, inv):
    if "Value" in changed: blk_msgs.append(bytes(changed["Value"]))
bus.add_signal_receiver(on_cmd, "PropertiesChanged", "org.freedesktop.DBus.Properties", "org.bluez", chars[UUID_CMD_N][0])
bus.add_signal_receiver(on_blk, "PropertiesChanged", "org.freedesktop.DBus.Properties", "org.bluez", chars[UUID_BLK_N][0])
ch(UUID_CMD_N).StartNotify(); pump(0.3)

seq = [0]
def send_cmd(payload, expect=None, timeout=8):
    seq[0] += 1
    fr = b"\xab\x00" + struct.pack(">HHH", len(payload), arc(payload), seq[0]) + payload
    n0 = len(cmd_frames)
    ch(UUID_CMD_W).WriteValue(dbus.Array(fr, "y"), {"type": "request"})
    log("CMD >", payload.hex(" "))
    if expect is None: pump(0.3); return None
    def got():
        for f in cmd_frames[n0:]:
            if f[1] & 0x10 == 0 and f[8:].startswith(expect): return f[8:]
    r = wait(got, timeout, "reply " + expect.hex(" ")); log("RSP <", r.hex(" ")); return r

# 1. login (cmd 03 key 13 -> expect 03 00 14 ...)
r = send_cmd(b"\x03\x00\x13" + struct.pack(">H", len(USER_ID)) + USER_ID, expect=b"\x03\x00\x14")
if r[5:6] != b"\x00": raise SystemExit("ABORT: login rejected " + r.hex(" "))
# 2. prepare transfer (cmd 01 key 01 -> expect 01 00 02)
send_cmd(b"\x01\x00\x01\x00\x00", expect=b"\x01\x00\x02", timeout=10)

# 3. bulk transfer
data = open(sys.argv[1], "rb").read()
assert data[:7] == b"TOPSTEP" and struct.unpack_from("<I", data, 0x0c)[0] == len(data)
ch(UUID_BLK_N).StartNotify(); pump(0.5)
blk = ch(UUID_BLK_W)
def bwrite(b): blk.WriteValue(dbus.Array(b, "y"), {"type": "command"})
def wait_blk(code, timeout=15):
    def got():
        while blk_msgs:
            m = blk_msgs.pop(0)
            if m[0] == code: return m
            raise SystemExit(f"ABORT: unexpected bulk reply {m.hex(' ')} (wanted {code:02x})")
    return wait(got, timeout, f"bulk reply {code:02x}")

bwrite(bytes([1, 5]) + bytes(10))
r = wait_blk(0x81); log("START ok", r.hex(" "))
pkt = min(r[28] | (r[29] << 8) or 250, mtu - 3) if len(r) >= 30 else mtu - 3
pkt = min(pkt, 250); bsize = struct.unpack_from("<H", r, 30)[0] if len(r) >= 32 else 0x3800
log(f"packet size {pkt}, block size {bsize}")

def send_block(typ, off, chunk, ack):
    msg = bytes([typ, 0, 0, 0]) + struct.pack("<IHH", off, arc(chunk), len(chunk)) + chunk
    for i in range(0, len(msg), pkt): bwrite(msg[i:i + pkt])
    r = wait_blk(ack)
    if r[10] != 1: raise SystemExit(f"ABORT: block at {off} rejected {r.hex(' ')}")

send_block(2, 0, data[:0x400], 0x82); log("header ok")
off = 0x400; t0 = time.time()
while off < len(data):
    chunk = data[off:off + bsize]; send_block(3, off, chunk, 0x83); off += len(chunk)
    print(f"\r  {off*100//len(data):3d}%  {off}/{len(data)} bytes", end="", flush=True)
print()
bwrite(bytes([4]) + bytes(11)); wait_blk(0x84); log(f"END ok — {len(data)} bytes in {time.time()-t0:.1f}s")
ch(UUID_BLK_N).StopNotify()
def ca_frame():
    for f in cmd_frames:
        if f[1] & 0x10 == 0 and f[8:11] == b"\x02\x00\xca": return f[8:]
r = wait(ca_frame, 30, "install result (02 ca)")
ok = r[3:5] == b"\x00\x05"
log("install result:", r.hex(" "), "->", "APPLIED" if ok else "REJECTED by watch")
pump(1)
lst = send_cmd(b"\x02\x00\x52\x00\x00", expect=b"\x02\x00\x53")
log("download slot:", "EMPTY" if b"\xff\xff\xff\xff" in lst else "filled")
log("done")
sys.exit(0 if ok else 2)
