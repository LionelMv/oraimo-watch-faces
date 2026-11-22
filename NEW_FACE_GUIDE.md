# How to make and install a new watch face (what works)

Proven on 2026-11-07 with `designs/meridian-gold` (built from scratch, installed, all elements live).

## 0. One-time setup
```bash
cd ~/Documents/PROJECTS/oraimo-watch-faces
python3 -m venv venv && venv/bin/pip install -r tools/requirements.txt   # Pillow, NumPy
sudo apt install python3-dbus python3-gi bluez                            # for the sender (system python3)
```
The laptop must be paired with the watch (`54:88:00:00:9D:07`).

## 1. Start a new design from the working one
```bash
cp -r designs/meridian-gold designs/my-face
mv designs/my-face/meridian-gold.bin designs/my-face/my-face.bin   # optional, gets overwritten
```
In `designs/my-face/design.py` change the output name (`meridian-gold.bin` → `my-face.bin`).

## 2. Edit the design (`design.py`)
The script draws pictures with Pillow and describes the face with `tools/facekit.py`:

```python
face = fk.Face(TEMPLATE)                    # template = store face 1000031 (header + hands)
face.background(img_466x466)                # opaque background
fid = face.add_font({'0': img, …, '9': img, '/': img})          # digit font (all glyphs same height)
face.rec(fk.K_TIMEDATE, fk.SRC_MONTHDAY, x, y, params=[fid])    # date MM/DD, x,y = left-top
face.rec(fk.K_TIMEDATE, fk.SRC_TIME,     x, y, params=[fid])    # digital time (font needs ':')
face.rec(fk.K_DATA, fk.SRC_STEPS, cx, y, params=[fid, fk.ALIGN_CENTER])   # x = centre
face.rec(fk.K_DATA, fk.SRC_HEART, cx, y, params=[fid, fk.ALIGN_CENTER])   # also SRC_KCAL, SRC_DISTANCE
face.rec(fk.K_IMGLIST, fk.SRC_WEEKDAY, x, y, params=[first_id]) # 14 images: CN,EN pairs Mon→Sun
face.rec(fk.K_LEVEL, fk.SRC_BATTERY, x, y, params=[first_id])   # 11 images: 0…10 segments lit
face.rec(fk.K_WEATHER, fk.SRC_WEATHER, x, y, params=[first_id])  # 13 weather icons (order in README)
face.rec(fk.K_DATA, fk.SRC_TEMP, cx, y, params=[temp_font, fk.ALIGN_CENTER])  # font needs / C F _
hid = face.add_hand(hand_img_18x158)        # own hand picture (tile format handled by facekit)
face.rec(fk.K_HAND, fk.SRC_HOUR, 224, 117, 233, 233, params=[hid])    # SRC_MIN / SRC_SEC likewise
face.preview(preview_img)                   # 312×312 picture shown in the watch's face list
open(OUT, 'wb').write(face.build())
```
* Images with transparency: `face.add_image(img)`; returns the graphic id. Consecutive calls give
  consecutive ids (needed for weekday/battery lists).
* Fonts: include placeholder glyphs `-` and `_` (the watch draws them when there is no reading).
* Hands: draw an upright picture and add it with `face.add_hand(img)`. The rotation point inside the
  picture is `(233 − x, 233 − y + 7)`: with the template placements that is hour 18×158 → (9, 123),
  minute 18×241 → (9, 206), seconds 36×278 → (18, 228). See `designs/meridian-gold/design.py`
  (`pill_hand`). You can still reuse Oraimo hands with `fk.copy_resource(template, 45/46/48)`.

## 3. Build and check the preview
```bash
venv/bin/python -I designs/my-face/design.py
venv/bin/python -I tools/verify.py designs/my-face/my-face.bin     # checksum + size fields
```
Open `designs/my-face/preview.png` to check the look before installing.

## 4. Install
1. Turn the **phone's Bluetooth OFF** (the watch only talks to one device).
2. Run:
   ```bash
   tools/robust_install.sh designs/my-face/my-face.bin
   ```
3. Success = `slot=FILLED`. (`slot=EMPTY` = the watch rejected the file and fell back to a built-in face.)
4. Turn the phone's Bluetooth back on afterwards if you like — the face stays.

## 5. Rules the watch enforces (already handled by `facekit.py`)
| Rule | What happens if broken |
|---|---|
| File must **end with the 4 bytes `TBUI`** | File is stored, then discarded → built-in face, empty slot |
| Opaque images (background/preview) must not contain 1-pixel runs (`0x81`) | Same as above |
| TOPSTEP checksum (CRC-16/UMTS from 0x400) and size fields correct | Rejected |
| Graphics 4-byte aligned, resource table / records at the standard offsets | Rejected |

If you edit `facekit.py`, re-check that it still rebuilds the template byte-identically:
```bash
cd tools && ../venv/bin/python -I variant.py ../samples/from_capture/store_face_373284.bin ../work/rt.bin \
  && cmp ../work/rt.bin ../samples/from_capture/store_face_373284.bin && echo OK
```

## 6. Things to know
* The watch has **4 built-in faces + 1 download slot**. Installing replaces the slot; keep every design in
  `designs/` so it can be reinstalled any time.
* The "applied" notice from the watch is not reliable — trust the face-list check (`robust_install.sh`).
* After a rejected file the Bluetooth link can be flaky (connection aborts, "UnknownObject" errors).
  Wait a minute and retry; if it persists, **restart the watch**.
* Installing a known-good file restores a working face:
  `tools/robust_install.sh samples/from_capture/store_face_373284.bin`
* Never guess new Bluetooth commands; `tools/watch_cmd.py` is for read-only queries (e.g. `0200520000`).

## 7. If a new design is rejected
Bisect with `tools/variant.py` (keep only some elements, or swap in template graphics) and install each
variant with `robust_install.sh` until the faulty element is found. See README §7c and the 2026-11-07
notes in the test log.
