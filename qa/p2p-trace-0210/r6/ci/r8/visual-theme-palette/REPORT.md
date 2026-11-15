# R8 Theme / Palette Static Visual Review

Finished: 2026-11-15T22:17:59.468502+08:00. Source `b3eb5568`; build `43715446826`; UI `43720799962`; API33 three-button cloud screenshots.

## Outcome

**No confirmed clipping / overflow defect in inspected visible component regions. This is NOT a blanket 97-scene all-component PASS.** Original numeric gates were not rerun and are not visual evidence. No app/code/build/device/browser actions; original PNGs unchanged. Real handshake not covered.

## Honest coverage

- 23 theme + 74 palette root originals: **all 97 personally seen** in labelled full-page contact-sheet overviews; no totally unviewed original.
- 28 contact sheets personally loaded/read: 17 full-page overview sheets and 11 magnified component sheets.
- 62 palette scenes have magnified-component sheet coverage; 12 palette system-mode scenes are overview-only depth.
- 21 theme scenes overview-only; 2 date-error scenes also have individually seen keyboard-only native crops (the crops do **not** include app dock).
- 81 native crop files generated: **62 visually inspected via resampled component sheets**, **11 individually seen at native size**, **8 supplemental theme crops UNVIEWED** after stop instruction. Generated files are not automatically reviewed.
- Four original palette full frames additionally loaded directly; per-scene SHA / coverage / crop coordinates are in `image-mapping.json`.

## Component findings

1. **Appearance / palette, light and dark, six colours:** 亮色 / 暗色 / 跟随系统, helper text and 紫 / 蓝 / 绿 / 青 / 橙 / 粉 labels readable and contained; selected checks/borders complete. Purple references additionally native-resolution inspected.
2. **Week header + course cells:** previous/next week, 第11周 · 单周, seven weekday chips, M3E配色验收, 08:00 / 08:45, course interval / recurrence have no observed clipping/collision. FAB separate from dock.
3. **Semester:** 学期 / 保存学期 / 学期开始日期 / 2026-09-01 and helper line fit with visible margins in light/dark six-colour cards.
4. **Editor bottom:** 每周 / 单周 / 双周, eight swatches, check mark, 删除课程 glyphs and outline complete. No visible collision with dock.
5. **System bars / navigation:** gray status/three-button keys on light frames; white on dark frames; app labels/icons and system keys visibly separated. Date-error dock remains above IME at overview resolution. Dark app still uses light system IME; not classified as app bug.
6. **Cold / restored:** stills show expected visible selected mode/palette; restored frame dark + purple, system-cold dark + pink/follow-system. No claim of launch-flicker absence, real persistence or transition/handshake validation.

## Boundary observation, not a fabricated UI defect

Options/cold/system/restored scenes are scrolled: top of the date label is cut at **original y=325** (viewport approximately `[53,325,1027,1584]`); the complete label is visible in semester scenes. Theme settings/options similarly leave palette row partly off-viewport above dock. Off-viewport content is excluded rather than marked PASS.

## Limits / unviewed derived files

The eight `crops/theme-{light,dark}-{date-dock,devices,today,editor-top}.png` files were created but **not loaded**, so no native component verdict for them. All other native crop review modes are explicit in mapping. 97 overview coverage is not 97 full-resolution component acceptance. No new actions or UI fixes authorized/performed.

## Verification / evidence

- Original 97 SHA256 mappings recomputed after review: unchanged, no mismatches.
- Current SHA256 for all **109 derived images** checked against generation mapping, no mismatches.
- `report.json`: structured findings/coverage/limits.
- `image-mapping.json`: each original absolute path/SHA, scene review depth, crop coordinates/hash and viewed/unviewed state.
- `derived-image-hashes.json`: current hashes for all contact sheets/crops.
- `sheets/`: labelled six-colour/same-page full images and magnified components.
- `crops/`: untouched-source native component crops.

Absolute evidence directory: `/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/visual-theme-palette`.
