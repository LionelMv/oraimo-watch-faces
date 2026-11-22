# Custom Watch Faces for the oraimo Watch 5R Pro — Reverse-Engineering Notes

**Status (2026-11-07):** the watch-face file format (including layout, fonts and all graphic types) and
the Bluetooth transfer protocol are decoded; faces can be designed from scratch (`tools/facekit.py`,
`designs/`). A laptop running Linux can now **build** a watch-face file and **install** it on the watch
without the Oraimo Health app.

| Milestone | Result |
|---|---|
| Watch-face file format (`TOPSTEP` / `TBUI`) | Decoded, checksum verified on 6 files |
| Background / preview images | Standard 16-bit BMP, extract and replace working |
| Digit / label / icon graphics (`PA` format) | 760/760 graphics parse exactly; encoder working |
| Bluetooth transfer protocol | Decoded from 2 captures; every checksum verified |
| Laptop → watch, known-good file | **Success** (1,047,236 bytes, watch confirmed "applied") |
| Laptop → watch, our own design (new background + new digits) | **Success — custom face displayed on the watch** |
| Layout records, fonts, element kinds | Decoded; builder rebuilds a store face **byte-identical** |
| Face designed from scratch (`designs/meridian-gold`) | **Success — installed and confirmed working on the watch (all elements live)** |


> **Making a new face?** Follow the step-by-step guide: [NEW_FACE_GUIDE.md](NEW_FACE_GUIDE.md)

---

## 1. Hardware & software

| Item | Value |
|---|---|
| Watch | oraimo Watch 5R Pro, BLE address `54:88:00:00:9D:07`, internal model **OSW-830** |
| Screen | 466 × 466, round |
| Phone | OPPO CPH2359 (ColorOS, MediaTek chipset) |
| Phone app | Oraimo Health (`com.transsion.oraimohealth`), built on the **Topstep** watch SDK |
| Laptop | Linux, BlueZ 5.85, Python 3 (`dbus`, `gi`) + a venv with Pillow/NumPy |

---

## 2. How we got here (method)

1. **Looked at the watch over Bluetooth from the laptop.** Only two vendor-specific services, nothing
   readable — every function is a private command channel. Guessing commands was ruled out as risky.
2. **Tried Android's standard Bluetooth HCI snoop log.** On this OPPO it always produced an empty
   16-byte file. (ColorOS routes Bluetooth logs to its own tool.)
3. **Found the app's own working files** via `adb` in
   `/sdcard/Android/data/com.transsion.oraimohealth/files/oraimoHealth/dial/` — the finished watch-face
   `.bin` files the app builds and sends, plus the downloaded store faces. This gave us the file format.
4. **Captured the real Bluetooth traffic** with ColorOS's own logger:
   dial `*#800#` → enable **Developer mode ("logs saved on this device only")** → Bluetooth →
   Connections → start → toggle phone Bluetooth off/on → install a face in the app → stop.
   Logs appear in
   `/sdcard/Android/data/com.oplus.logkit/files/Log/<date>@bluetooth/bluetooth/btsnoop_hci/CsLog_*/BT_HCI_*.cfa`
   (standard `btsnoop` format). *Do not use "Submit" — it uploads logs to OPPO.*
5. **Decoded the capture** with our own parser (`tools/att.py`), rebuilt the transferred files
   byte-for-byte from the radio traffic, and identified every checksum.
6. **Wrote a sender** (`tools/send_face.py`) that replays the app's exact sequence over BlueZ.
   First test: re-sent a file the app had already installed → success.
7. **Decoded the compressed graphics**, wrote an encoder, built a face with our own background and
   digits (`tools/build_test_face.py`), and sent it.

---

## 3. Watch Bluetooth (GATT) layout

| Service UUID | Characteristic | ATT handle | Properties | Role |
|---|---|---|---|---|
| `000001ff-3c17-d293-8e48-14fe2e4da212` | `ff02` | 6 | write (with response) | **Command** channel, phone → watch |
| | `ff03` | 3 (CCCD 4) | notify | Command replies, watch → phone |
| `00009966-3c17-d293-8e48-14fe2e4da212` | `ffb1` | 9 | write-without-response | **Bulk file** data, phone → watch |
| | `ffb2` | 11 (CCCD 12) | notify | Bulk acknowledgements |

Negotiated ATT MTU: 256 (packets of 250 bytes are used for bulk data).

---

## 4. Command channel protocol (`ff02` / `ff03`)

Every message is a frame:

```
offset  size  field
0       1     0xAB  (magic)
1       1     flags  0x00 = data, 0x10 = acknowledgement
2       2     payload length (big-endian)
4       2     CRC-16/ARC of the payload (big-endian)
6       2     sequence number (big-endian)
8       n     payload:  [command][version=0x00][key][value length BE16][value…]
```

* Every data frame is acknowledged by the other side with `AB 10 00 00 00 00 <seq BE16>`.
* The watch sometimes splits a frame into two notifications (8-byte header, then payload).
* **CRC-16/ARC** = poly 0x8005 reflected (0xA001), init 0, no final XOR.

### Commands used for installing a face

| Step | Payload sent | Watch reply | Meaning |
|---|---|---|---|
| Login | `03 00 13 00 20` + 32-byte account id | `03 00 14 00 01 00` | `…01 00` = accepted, `…01 01` = rejected |
| Prepare transfer | `01 00 01 00 00` | `01 00 02 00 02 00 00` | Ready for bulk file |
| (after transfer) | — | `02 00 CA 00 05 01 03 01 04 xx` | Face applied notification |

**Login gotcha:** the value is the first **28 characters** of the app account id followed by
**4 zero bytes** (exact bytes are in `tools/send_face.py`). Sending the full 32-character id is rejected.

---

## 5. Bulk file transfer protocol (`ffb1` / `ffb2`)

Each message begins with a 12-byte header, then data; long messages are split into 250-byte BLE packets
(the receiver reassembles using the length field).

```
offset  size  field
0       1     type   01 start, 02 file header, 03 data block, 04 end
1       3     00 00 00   (start: byte 1 = file type, 0x05 = watch face)
4       4     file offset (little-endian)
8       2     CRC-16/ARC of the data in this message (little-endian)
10      2     data length (little-endian)
12      n     data
```

| Step | Phone sends | Watch replies (`ffb2`) |
|---|---|---|
| Start | `01 05 00 …` (12 bytes) | `81 …` — byte 28 = max packet (0xFD), bytes 30–31 = block size (0x3800 = 14,336) |
| Header | `02`, offset 0, first **1024 bytes** of the file | `82 … 01 00 00` (byte 10 = 1 → OK) |
| Data | `03`, offset, 14,336-byte blocks | `83 … 01 00 00` per block |
| End | `04 00 …` (12 bytes) | `84 … 01 00 00` |

A 1 MB face takes ~2 minutes from the laptop (~30 s from the app; our sender is not yet optimised).

---

## 6. Watch-face file format (`.bin`)

### 6.1 Outer `TOPSTEP` header (first 0x400 bytes)

| Offset | Size | Meaning |
|---|---|---|
| 0x00 | 7 | ASCII `TOPSTEP` |
| 0x0C | 4 | total file size (LE) |
| 0x10 | 2 | **CRC-16/UMTS** (poly 0x8005, *not* reflected, init 0) of bytes 0x400…end (LE) |
| 0x28 | 4 | body length = file size − 0x400 |
| 0x38 | … | internal name, e.g. `gui_dial_binfile_watch_1001999_1_20241015_ota.bin` |

### 6.2 `TBUI` body (from 0x400)

> **Required:** the file must **end with the 4 bytes `TBUI`** (end marker; TBUI field 0x40c = file size − 0x404).
> Without it the watch stores the file, then discards it and falls back to a built-in face.

* 0x400: ASCII `TBUI` + header; 0x420 holds `D2 01 D2 01` (466 × 466).
* 0x440: **layout header** — see §6.5 (records, resource table, fonts, data start).
* 0x1120: **resource table**, 12 bytes per entry:
  `id (u16) · format (u16) · width (u16) · height (u16) · offset (u32, add 0x400 for file position)`

| Format | Content |
|---|---|
| `0x50e` | Standard Windows **BMP**, 16-bit RGB565 (BITFIELDS), bottom-up — backgrounds & previews |
| `0x20e` | **`PA` compressed image** with alpha — digits, labels, icons |
| `0x10e` | `PA` image **without alpha** (2-byte pixels) — backgrounds & previews in store faces |
| `0x40e` | `PA` **hands**: upright picture split into **31×31 tiles** (row-major), one index entry per tile; the watch rotates it. Encoder: `facekit.encode_hand` |

### 6.3 `PA` compressed image (format 0x20e)

```
header (16 bytes): 'P' 'A' 00 01 · width u16 · height u16 · 00 · es · avg u16 · 00 00 00 00
row table: (height+1) signed integers of es bytes (es = 1 or 2)
           row y starts at  data_start + y*avg + table[y]   (entry [height] = end of data)
data: per row, tokens until the row is full:
   0x80|n  a  c_lo c_hi   → n pixels (n ≤ 63) of alpha a, colour RGB565 c
   0xC0|n  then n × (c_lo c_hi) → n pixels, each its own colour, alpha = previous alpha
   0x00–0x7F (one byte)   → one pixel = previous colour + small delta, alpha = previous alpha
                            bits 6-5: dR+2 · bits 4-2: dG+4 · bits 1-0: dB+2   (0x52 = same colour)
   (header byte 3: 1 = 3-byte pixels with alpha, 0 = 2-byte opaque pixels; byte 8: rows per index
    entry, 0 = every row)
```

**Rule for opaque (`0x10e`) images:** never write 1-pixel runs (`0x81`); single pixels must be literals
(`0xC1…`). Oraimo never uses `0x81` there and the watch rejects files that do. (Alpha images may use `0x81`.)

Our **encoder** writes only `0x80|n` run tokens (verified to be understood by the watch, as all Oraimo
graphics use them). Hard-edged / per-row-gradient designs compress well with runs only.

### 6.5 Layout header, element records and fonts

At 0x440 (offsets relative to 0x400):
`records off u32 (0xa0) · count u16 · size u16 (32) · resources off u32 (0xd20) · count u16 · 12 ·
fonts off u32 (0x1920) · count u16 · 0x60 · 4 · data off u32 (0x4920)`; 0x460 = preview resource id.

**Element record** (32 bytes): `index · kind · 01 · source · x i16 · y i16 · w i16 · h i16 · params u16×10`

| kind | meaning | source values | params |
|---|---|---|---|
| 0 | background | 0 | [resource] |
| 1 | hand (x,y = sprite top-left at 12 o'clock, w,h = pivot) | 6 hour · 7 minute · 8 second | [resource] |
| 2 | time / date number (x,y = left-top) | 0 time · 1 day · 13 month/day | [font, …] |
| 3 | data number | 0 steps · 6 distance · 7 kcal · **8 heart rate** · **11 temperature** | [font, align 0 left / 1 centre (x = centre)] |
| 4 | image list | 0 weekday (14 imgs: CN/EN pairs Mon→Sun) · 6 AM/PM | [first resource] |
| 5 | level gauge | 0 **battery** (11 imgs: 0…10 segments) | [first resource] |
| 6 | preview / state image | 1 preview · **2 weather icon** (13 imgs) | [resource / first resource] |
| 8 | touch shortcut | 16, 17 … | — |
| 9 / 255 | DIY colour sets / DIY editable areas | | |

**Hands** (`0x40e`): the picture is stored in 31×31 tiles; the element's `x,y` place the picture at
12 o'clock and `w,h = 233,233` is the screen pivot. The rotation point inside the picture is
`(233 − x, 233 − y + 7)` — e.g. hour (9, 123), minute (9, 206), seconds (18, 228).

**Weather**: kind 6 / source 2 with 13 icons in this order: partly cloudy, sunny, light snow, rain,
heavy snow, cloudy, fog, wind, heavy rain, sleet, light rain, thunder, unknown. Temperature: kind 3 /
source 11; its font needs `'/'` (minus), `'C'` (°C), `'F'` (°F), `'_'` (no data).

**Font** entries (0x180 bytes apart from 0x1920+0x400): `count u16 · 0 · (char u16, resource u16) × count`
— e.g. `'0'..'9', ':'`, `'/'` (date separator), `'%'`, `'.'`, `'_'` (no data).

### 6.4 What the files contain

| File | Type | Elements |
|---|---|---|
| `dial_*.bin` (app DIY / photo face) | Digital | 5 colour sets × (10 small date digits 24×40, 10 big time digits 48×74, colon 18×74), 70 weekday labels 103×40 (CN/EN × colours), 5 colour preview strips 466×114, background BMP 466×466, preview BMP 312×312 |
| `4114.bin` (store) | Digital | big digits 67×85 + colon, two small digit sets with separators, icons 41×21, weekday/month labels |
| `4167.bin` (store) | Hybrid | analog hands (16×54, 18×82, 2×76), 13 weather-style icons 61×60, 13 gauge images 48×25, digits, labels |
| `4089.bin` (store) | Analog | hands 38×160, 38×210, 94×268, digit sets, 14 labels 190×54 |

Rendered examples are in `images/` (e.g. `d_sets.png` = the 5 colour digit sets).

---

## 7. Tools (`tools/`)

Set up once:
```bash
python3 -m venv venv && venv/bin/pip install -r tools/requirements.txt
```
`send_face.py` uses the **system** `python3` (needs `python3-dbus` and `python3-gi`).

| Script | Purpose |
|---|---|
| `att.py` | Parse a `btsnoop` capture into ATT packets (with L2CAP reassembly) |
| `timeline.py`, `bulk.py` | Print the command timeline / bulk transfer structure of a capture |
| `rebuild.py` | Rebuild the transferred `.bin` files from a capture |
| `verify_all.py` | Check every bulk-block and command-frame CRC in a capture |
| `verify.py` | Check the TOPSTEP checksum and size fields of `.bin` files |
| `tbui.py` | Read the resource table (`entries()`) |
| `tbui3.py` | Decode `PA` graphics (`decode_pa()`) |
| `sheet.py` | Render a range of graphic ids to a PNG contact sheet |
| `extract.py` | Extract embedded BMP images |
| `build_test_face.py` | Build a face: new background, preview and time digits on a known-good DIY file |
| `pa_generic.py` | Decode **any** `PA` graphic (all token types, alpha/opaque) → `to_image()` |
| `layout.py` | Print a face's element records |
| `facekit.py` | **Build a face from scratch** (backgrounds, fonts, numbers, weekday, battery gauge, hands) |
| `install_face.sh` | Verify + install a `.bin` (refuses if the phone's Bluetooth is on, when adb is connected) |
| `robust_install.sh` | Install with connection retries and **verify via the face list** (recommended) |
| `watch_cmd.py` | Send read-only command payloads after login (e.g. `0200520000` = face list) |
| `variant.py` | Rebuild a face keeping only some elements / swapping graphics (used for bisecting) |
| `send_face.py` | **Install a `.bin` on the watch from the laptop** |

Typical workflow:
```bash
cd tools
../venv/bin/python -I build_test_face.py ../samples/from_capture/photo_face_1047236.bin my_face.bin
../venv/bin/python -I verify.py my_face.bin
# turn the PHONE's Bluetooth off first, so the watch can connect to the laptop
python3 -I send_face.py my_face.bin
```

---

## 7b. Design library (`designs/`)

The watch keeps only a few faces, so every design lives here and can be re-installed at any time.
Each folder holds `design.py` (generator), `<name>.bin` (ready to install), `preview.png`, `README.md`.

| Design | Description |
|---|---|
| [`meridian-gold`](designs/meridian-gold/) | Analog, white batons, own outlined hands, 4 sub-dials: date+weekday, steps, weather+temperature, golden 10-segment battery ring |
| [`horizon`](designs/horizon/) | Analog dusk scene (stars, mountains), dauphine hands, coral seconds; weather in the sky, date & steps plates, golden battery arc along the rim |

```bash
venv/bin/python -I designs/<name>/design.py          # rebuild after editing
tools/robust_install.sh designs/<name>/<name>.bin     # install + verify (phone Bluetooth off)
```

## 7c. How the watch stores faces & how to verify an install

* 4 built-in faces (ids 1000185, 1000194, 1000196, 1000197) + **one download slot** shared by store and
  custom faces. Installing anything replaces the slot; a rejected file leaves it **empty** and the watch
  falls back to a built-in face.
* Face id = TBUI field 0x408 (low 24 bits), e.g. `0x0f425f` = 1000031, `0x0f4a0f` = 1001999 (DIY).
* Read-only query `02 00 52 00 00` returns the face list (`02 00 53 …`); `ff ff ff ff` = empty slot.
* The "applied" notice (`02 00 CA …`) is **not** proof: the watch can store a file and discard it shortly
  after. Verify with the face list ~30 s later — `tools/robust_install.sh` does this automatically
  (retries the connection, installs, reconnects, prints `slot=FILLED/EMPTY`).
* After a rejected file the watch may restart; the BLE link can be flaky for a while (stale GATT objects,
  `le-connection-abort`). Disconnect, wait, retry — or restart the watch.

## 8. Safety notes

* Always start from a **known-good** file and keep structure, sizes and offsets unchanged unless the
  layout records are understood. Our builder pads new graphics into the original slots.
* The sender aborts on any unexpected reply. An incomplete transfer has so far simply been ignored by
  the watch; reconnecting the Oraimo app restores normal use.
* `send_face.py` contains the account login bytes; keep it private.
* The phone's Bluetooth must be **off** while the laptop talks to the watch (one connection at a time).

---

## 9. Test log

| Date / time | File | Result |
|---|---|---|
| 2026-11-06 01:06 | first attempt, full 32-char login | Login rejected (`…01 01`), nothing sent — harmless |
| 2026-11-06 01:08 | `photo_face_1047236.bin` (known-good, from capture) | **Success**, 116 s, watch replied "applied" |
| 2026-11-06 01:20 | `our_builds/test_face_custom.bin` (new background + orange/pink digits) | **Success** — all 72 blocks accepted (121 s); watch shows the blue ring face with orange/pink time digits (confirmed by user). The "applied" notice arrived later than the sender's 3 s listen window. |
| 2026-11-08 | `designs/meridian-gold` v2 (own hands, weather, shorter markers) | **Installed and confirmed perfect by user** — first custom-drawn hands |
| 2026-11-07 | `designs/meridian-gold` (built from scratch) | First attempts rejected (slot emptied). Bisecting found two rules: no 1-pixel runs in opaque images, and the file must end with `TBUI`. After both fixes: **installed, all elements confirmed working by user** |

---

## 10. Next steps

1. Speed up the sender.
2. ~~Decode the layout records~~ (done 2026-11-07) — add more designs: steps / heart rate /
   battery (store faces 4114/4167 show the format supports them).
3. ~~Custom-drawn hands~~ (done 2026-11-08: 31×31 tile format, pivot ≈ 7 px below 233−y).
4. A small design tool: drop in a background + choose a digit font/colour → `.bin` → install.
