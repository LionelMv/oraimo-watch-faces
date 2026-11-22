"""Send raw command payloads (hex) after login and print replies. Read-only queries only!"""
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


r = send_cmd(b"\x03\x00\x13" + struct.pack(">H", len(USER_ID)) + USER_ID, expect=b"\x03\x00\x14")
for hx in sys.argv[1:]:
    p = bytes.fromhex(hx)
    n0 = len(cmd_frames)
    send_cmd(p); pump(3)
    for f in cmd_frames[n0:]:
        if f[1] & 0x10 == 0: log("RSP <", f[8:].hex(" "))
