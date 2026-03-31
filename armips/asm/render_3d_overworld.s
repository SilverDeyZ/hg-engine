.nds
.thumb

/*
 * render_3d_overworld.s — Overworld 3D Camera Mode
 *
 * Controlled by RENDER_3D_OVERWORLD in armips/include/config.s.
 * Set to 1 to enable; 0 (default) preserves vanilla behavior.
 *
 * Effect when enabled:
 *   Replaces camera param table entries for type 0 and type 4 in overlay_01
 *   with the bytes from type 6 (Normal 3D perspective, "Normal 3D [06]").
 *
 *   Type 0 — outdoor routes and towns     (perspective telephoto, angle ~−49.5°, FOV ~8°)
 *   Type 4 — interiors, caves, buildings  (orthographic / flat 2D,     angle ~−35.8°)
 *   Both → Type 6 — Normal 3D            (perspective,                 angle ~−50.6°, far 1500)
 *
 *   ~521 of ~540 maps use type 0 or type 4 and will be affected.
 *
 * Technical basis:
 *   Camera param table: ov01_02206478 in overlay_01 (load addr 0x021E5900)
 *   Each entry: 36 bytes (0x24).  cameraType indexes this table directly.
 *   Type 0 @ 0x02206478  (offset 0x00 from table base)
 *   Type 4 @ 0x02206508  (offset 0x90 from table base)
 *   Type 6 @ 0x02206550  (offset 0xD8 from table base)  ← source profile
 *
 *   Type 6 entry bytes (verified from base/overlay/overlay_0001.bin):
 *     distance:         0x0029AEC1  (~667 units)
 *     angle.x:          0xDFE2      (~−50.6°)
 *     angle.y/z/unused: 0x0000 x3
 *     perspectiveType:  0x00        (PERSPECTIVE)
 *     dummy:            0x00
 *     perspectiveAngle: 0x05C1      (~8.1°)
 *     near:             0x00096000  (150.0)
 *     far:              0x005DC000  (1500.0)
 *     lookAtOffset:     0, 0, 0
 *
 * Limitations (see area_header_data_report.md §10.6):
 *   - Script camera overrides (cutscenes, gyms) bypass cameraType entirely.
 *   - The time-of-day angle modifier table (ov01_02206464) has a type-6 entry
 *     that will be used; its content has not been runtime-tested.
 *   - Type 6 was unused in vanilla — visual regression testing is required.
 *   - When this patch is active, all type-0 and type-4 maps share the same
 *     profile, so the transition assert in field_warp_tasks.c:201 is satisfied.
 */

.if RENDER_3D_OVERWORLD == 1

.open "base/overlay/overlay_0001.bin", 0x021E5900

/* ------------------------------------------------------------------ */
/* Entry 0 (outdoor, type 0) — overwrite with type-6 bytes            */
/* ------------------------------------------------------------------ */
.org 0x02206478
.byte 0xC1, 0xAE, 0x29, 0x00  // distance   = 0x0029AEC1 (~667 units)
.byte 0xE2, 0xDF, 0x00, 0x00  // angle.x    = 0xDFE2 (~−50.6°), angle.y = 0
.byte 0x00, 0x00, 0x00, 0x00  // angle.z    = 0, angle.unused = 0
.byte 0x00, 0x00, 0xC1, 0x05  // perspType  = 0 (PERSPECTIVE), perspAngle = 0x05C1
.byte 0x00, 0x60, 0x09, 0x00  // near       = 0x00096000 (150.0)
.byte 0x00, 0xC0, 0x5D, 0x00  // far        = 0x005DC000 (1500.0)
.byte 0x00, 0x00, 0x00, 0x00  // lookAtOffset.x = 0
.byte 0x00, 0x00, 0x00, 0x00  // lookAtOffset.y = 0
.byte 0x00, 0x00, 0x00, 0x00  // lookAtOffset.z = 0

/* ------------------------------------------------------------------ */
/* Entry 4 (indoor/orthographic, type 4) — overwrite with type-6 bytes */
/* ------------------------------------------------------------------ */
.org 0x02206508
.byte 0xC1, 0xAE, 0x29, 0x00  // distance   = 0x0029AEC1 (~667 units)
.byte 0xE2, 0xDF, 0x00, 0x00  // angle.x    = 0xDFE2 (~−50.6°), angle.y = 0
.byte 0x00, 0x00, 0x00, 0x00  // angle.z    = 0, angle.unused = 0
.byte 0x00, 0x00, 0xC1, 0x05  // perspType  = 0 (PERSPECTIVE), perspAngle = 0x05C1
.byte 0x00, 0x60, 0x09, 0x00  // near       = 0x00096000 (150.0)
.byte 0x00, 0xC0, 0x5D, 0x00  // far        = 0x005DC000 (1500.0)
.byte 0x00, 0x00, 0x00, 0x00  // lookAtOffset.x = 0
.byte 0x00, 0x00, 0x00, 0x00  // lookAtOffset.y = 0
.byte 0x00, 0x00, 0x00, 0x00  // lookAtOffset.z = 0

/* ------------------------------------------------------------------ */
/* DISP3DCNT — disable edge marking, preserve anti-aliasing           */
/* ------------------------------------------------------------------ */
/*
 * ov01_021FBA3C (field 3D scene setup) reads REG_DISP3DCNT (0x04000060),
 * clears status bits, then ORs in 0x20 (bit 5 = edge marking) — turning
 * edge marking ON for every field entry.
 *
 * Vanilla flow (gf_3d_render.c → ov01_021FBA3C):
 *   initializeSimple3DVramManager sets AA=ON, edge=OFF
 *   ov01_021FBA3C then ORs 0x20 → AA=ON, edge=ON
 *
 * Patched flow:
 *   ov01_021FBA3C ORs 0x10 instead (AA bit, already set) → AA=ON, edge=OFF
 *
 * Single write site — confirmed only DISP3DCNT reference in overlay_01.
 * See .context/reports/render_3d_overworld_edge_aa_report.md
 */
.org 0x021FBC3A
.byte 0x10   // was 0x20 (MOVS r0, #0x20 → MOVS r0, #0x10)

.close

.endif // RENDER_3D_OVERWORLD == 1
