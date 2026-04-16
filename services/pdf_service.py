"""
DSTAIR — Professional PDF Report Generator
Layout:
  Page 1  Cover: header, full-width hero, country/title overlay, 4-stat band
  Page 2  Results: full-width radar chart + full-width sphere score table
  Page 3  Tools: triggered tools listed by name with status pill
"""
import io
import math
import os
import logging
import datetime as dt_mod

import requests as http_requests
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, Color
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# ── Palette ───────────────────────────────────────────────────────────────────
C_INK        = HexColor('#0D1B13')   # near-black for body text
C_FOREST     = HexColor('#022C22')   # dark header backgrounds
C_EMERALD    = HexColor('#064E3B')   # section accents
C_GREEN_MID  = HexColor('#059669')   # strong tier
C_MINT       = HexColor('#D1FAE5')   # soft green tint
C_ORANGE     = HexColor('#F97316')   # primary accent
C_AMBER      = HexColor('#F59E0B')   # triggered badge
C_RED        = HexColor('#DC2626')   # weak tier
C_YELLOW     = HexColor('#D97706')   # moderate tier
C_WHITE      = white
C_RULE       = HexColor('#E5E7EB')   # thin divider lines
C_MUTED      = HexColor('#6B7280')   # secondary text
C_LIGHT_BG   = HexColor('#F9FAFB')   # alternating row fill

PAGE_W, PAGE_H = A4
M = 14 * mm          # 39.7 pt margin
CW = PAGE_W - 2 * M  # usable content width


# ── Utilities ─────────────────────────────────────────────────────────────────

def _tier(norm):
    if norm is None:    return 'na'
    if norm >= 0.70:    return 'strong'
    if norm >= 0.40:    return 'moderate'
    return 'weak'

def _tier_color(norm):
    t = _tier(norm)
    if t == 'strong':   return C_GREEN_MID
    if t == 'moderate': return C_YELLOW
    if t == 'weak':     return C_RED
    return C_MUTED

def _tier_label(norm):
    t = _tier(norm)
    if t == 'strong':   return 'STRONG'
    if t == 'moderate': return 'MODERATE'
    if t == 'weak':     return 'WEAK'
    return 'N/A'

def _fetch_image(url, timeout=5):
    try:
        r = http_requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return ImageReader(io.BytesIO(r.content))
    except Exception:
        pass
    return None

def _local_image(static_folder, rel_path):
    if not rel_path:
        return None
    p = os.path.join(static_folder, rel_path)
    if os.path.exists(p):
        try:
            return ImageReader(p)
        except Exception:
            pass
    return None

def _compute_sphere_scores(answers_dict, spheres):
    out = []
    for s in spheres:
        sa = answers_dict.get(s.name, {})
        vals = [int(v) for v in sa.values()
                if v is not None and str(v) not in ('-1', '', 'NA')]
        norm = round(sum(vals) / (len(vals) * 7), 3) if vals else None
        out.append((s, norm))
    return out

def _rect(c, x, y, w, h, fill=None, stroke=None, lw=0.5, r=0):
    c.saveState()
    if fill:   c.setFillColor(fill)
    if stroke: c.setStrokeColor(stroke); c.setLineWidth(lw)
    if r:
        p = c.beginPath(); p.roundRect(x, y, w, h, r)
        c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)
    else:
        c.rect(x, y, w, h, fill=1 if fill else 0, stroke=1 if stroke else 0)
    c.restoreState()

def _text(c, x, y, s, font='Helvetica', size=9, color=None, align='left'):
    c.saveState()
    c.setFont(font, size)
    if color: c.setFillColor(color)
    if align == 'right':
        c.drawRightString(x, y, s)
    elif align == 'center':
        c.drawCentredString(x, y, s)
    else:
        c.drawString(x, y, s)
    c.restoreState()

def _page_footer(c, page_num, analysis, total_pages):
    _rect(c, 0, 0, PAGE_W, 26, fill=C_FOREST)
    _text(c, M, 9, 'DSTAIR  ·  Institutional Integrity Assessment Platform',
          size=6.5, color=HexColor('#6EE7B7'))
    _text(c, PAGE_W - M, 9,
          f'{analysis.country}  ·  Page {page_num} of {total_pages}',
          size=6.5, color=C_MUTED, align='right')

def _section_title(c, x, y, label, width):
    """Bold caps label with orange left tab and green underrule."""
    _rect(c, x, y - 10, 4, 18, fill=C_ORANGE)
    _text(c, x + 10, y, label, font='Helvetica-Bold', size=8, color=C_FOREST)
    _rect(c, x + 10, y - 12, width - 10, 0.6, fill=C_RULE)
    return y - 20


# ── Radar chart ───────────────────────────────────────────────────────────────

def _draw_radar(c, cx, cy, radius, sphere_scores):
    n = len(sphere_scores)
    if n < 3:
        return
    c.saveState()

    # White background disc
    c.setFillColor(C_WHITE)
    c.circle(cx, cy, radius + 18, stroke=0, fill=1)

    # Ring grid
    for pct in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for i in range(n):
            a = math.pi / 2 - 2 * math.pi / n * i
            pts.append((cx + radius * pct * math.cos(a),
                        cy + radius * pct * math.sin(a)))
        c.setStrokeColor(HexColor('#C7F5E1') if pct < 1.0 else HexColor('#86EFAC'))
        c.setLineWidth(0.6 if pct < 1.0 else 1.0)
        p = c.beginPath()
        p.moveTo(*pts[0])
        for pt in pts[1:]: p.lineTo(*pt)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
        # pct label at top spoke
        top_a = math.pi / 2
        lx = cx + radius * pct * math.cos(top_a)
        ly = cy + radius * pct * math.sin(top_a)
        c.setFont('Helvetica', 4.5)
        c.setFillColor(C_MUTED)
        c.drawCentredString(lx, ly + 2, f'{int(pct * 100)}%')

    # Spokes
    c.setStrokeColor(HexColor('#D1FAE5'))
    c.setLineWidth(0.5)
    for i in range(n):
        a = math.pi / 2 - 2 * math.pi / n * i
        c.line(cx, cy,
               cx + radius * math.cos(a),
               cy + radius * math.sin(a))

    # Data polygon fill
    data_pts = []
    for i, (s, norm) in enumerate(sphere_scores):
        v = (norm or 0.0)
        a = math.pi / 2 - 2 * math.pi / n * i
        data_pts.append((cx + radius * v * math.cos(a),
                         cy + radius * v * math.sin(a)))

    c.setFillColor(Color(0.976, 0.451, 0.086, alpha=0.18))
    c.setStrokeColor(C_ORANGE)
    c.setLineWidth(1.8)
    p = c.beginPath()
    p.moveTo(*data_pts[0])
    for pt in data_pts[1:]: p.lineTo(*pt)
    p.close()
    c.drawPath(p, stroke=1, fill=1)

    # Dots
    c.setFillColor(C_ORANGE)
    for pt in data_pts:
        c.circle(pt[0], pt[1], 3.5, stroke=0, fill=1)

    # Axis labels
    lbl_r = radius + 22
    for i, (s, norm) in enumerate(sphere_scores):
        a = math.pi / 2 - 2 * math.pi / n * i
        lx = cx + lbl_r * math.cos(a)
        ly = cy + lbl_r * math.sin(a)
        label = s.label if len(s.label) <= 15 else s.label[:14] + '…'

        c.setFont('Helvetica-Bold', 6.5)
        tw = c.stringWidth(label, 'Helvetica-Bold', 6.5)
        cos_a = math.cos(a)
        if   cos_a >  0.3: tx = lx
        elif cos_a < -0.3: tx = lx - tw
        else:              tx = lx - tw / 2

        sin_a = math.sin(a)
        ty = ly + 3 if sin_a >= -0.15 else ly - 11

        c.setFillColor(C_FOREST)
        c.drawString(tx, ty, label)

        if norm is not None:
            score_s = f'{norm:.2f}'
            c.setFont('Helvetica', 5.5)
            c.setFillColor(_tier_color(norm))
            sw = c.stringWidth(score_s, 'Helvetica', 5.5)
            c.drawString(tx + tw / 2 - sw / 2, ty - 9, score_s)

    c.restoreState()


# ── Main ─────────────────────────────────────────────────────────────────────

def generate_pdf(analysis, spheres, tools, triggered_ids, static_folder,
                 ai_analysis=None, username=None):

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f'{analysis.title} — DSTAIR Report')
    c.setAuthor('DSTAIR Platform')

    answers         = analysis.answers_dict or {}
    country_obj     = analysis.country_obj
    sphere_scores   = _compute_sphere_scores(answers, spheres)
    triggered_tools = [t for t in tools if t.id in triggered_ids]
    date_str        = dt_mod.datetime.now().strftime('%B %d, %Y')
    TOTAL_PAGES     = 3

    # aggregate stats
    all_vals = []
    for s, norm in sphere_scores:
        if norm is not None:
            sa = answers.get(s.name, {})
            all_vals.extend(int(v) for v in sa.values()
                            if v is not None and str(v) not in ('-1', '', 'NA'))
    overall_norm    = round(sum(all_vals) / (len(all_vals) * 7), 3) if all_vals else None
    overall_pct     = f'{overall_norm * 100:.1f}%' if overall_norm is not None else '—'
    answered_count  = len(all_vals)
    total_q         = sum(len(list(s.questions)) for s in spheres)
    spheres_covered = sum(1 for _, n in sphere_scores if n is not None)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — COVER  (clean hero, no text on image)
    # ══════════════════════════════════════════════════════════════════════════

    # ── Brand header ─────────────────────────────────────────────────────────
    HDR_H = 44
    _rect(c, 0, PAGE_H - HDR_H, PAGE_W, HDR_H, fill=C_FOREST)
    _rect(c, 0, PAGE_H - HDR_H, 6, HDR_H, fill=C_ORANGE)
    _text(c, 16, PAGE_H - 20, 'DSTAIR',
          font='Helvetica-Bold', size=14, color=C_ORANGE)
    _text(c, 16, PAGE_H - 33,
          'Institutional Integrity Assessment Platform',
          size=7, color=HexColor('#6EE7B7'))
    _text(c, PAGE_W - M, PAGE_H - 20, date_str,
          size=7.5, color=C_WHITE, align='right')
    if username:
        _text(c, PAGE_W - M, PAGE_H - 33,
              f'Prepared by  {username}',
              size=7, color=HexColor('#A7F3D0'), align='right')

    # ── Hero image — clean, no text overlay ──────────────────────────────────
    y = PAGE_H - HDR_H
    HERO_H = 280

    hero_img = None
    if country_obj and country_obj.image_url:
        hero_img = _local_image(static_folder, country_obj.image_url)

    if hero_img:
        c.drawImage(hero_img, 0, y - HERO_H, PAGE_W, HERO_H,
                    preserveAspectRatio=False, mask='auto')
        # very subtle bottom vignette so the country section below blends cleanly
        c.saveState()
        c.setFillColor(Color(1, 1, 1, alpha=0.18))
        c.rect(0, y - HERO_H, PAGE_W, 22, fill=1, stroke=0)
        c.restoreState()
    else:
        _rect(c, 0, y - HERO_H, PAGE_W, HERO_H, fill=C_EMERALD)

    y -= HERO_H

    # ── Country identity strip (below the image, on white) ───────────────────
    flag_img = None
    if country_obj and country_obj.iso2_code:
        flag_img = _fetch_image(
            f'https://flagcdn.com/w80/{country_obj.iso2_code.lower()}.png')

    ID_H = 56
    _rect(c, 0, y - ID_H, PAGE_W, ID_H, fill=HexColor('#F8FAFC'))
    _rect(c, 0, y - ID_H, PAGE_W, 0.8, fill=C_RULE)  # top border

    id_cy = y - ID_H / 2 - 4
    cx_offset = M
    if flag_img:
        c.drawImage(flag_img, M, id_cy - 13, 40, 27, mask='auto')
        cx_offset = M + 52

    _text(c, cx_offset, id_cy + 10, analysis.country,
          font='Helvetica-Bold', size=20, color=C_FOREST)
    _text(c, cx_offset, id_cy - 5, analysis.title,
          size=8.5, color=C_MUTED)
    _text(c, PAGE_W - M, id_cy + 10, 'Assessment Report',
          font='Helvetica-Bold', size=9, color=C_EMERALD, align='right')
    _text(c, PAGE_W - M, id_cy - 5, date_str,
          size=7.5, color=C_MUTED, align='right')

    y -= ID_H

    # ── Stats band ────────────────────────────────────────────────────────────
    BAND_H = 58
    _rect(c, 0, y - BAND_H, PAGE_W, BAND_H, fill=C_FOREST)

    stats = [
        (overall_pct,                          'OVERALL LEGITIMACY SCORE', C_ORANGE),
        (f'{answered_count} / {total_q}',      'QUESTIONS ANSWERED',       C_WHITE),
        (f'{spheres_covered} / {len(spheres)}', 'SPHERES COVERED',          C_WHITE),
        (str(len(triggered_tools)),             'TOOLS TRIGGERED',          HexColor('#FCD34D')),
    ]
    cell = PAGE_W / 4
    for i, (val, lbl, vc) in enumerate(stats):
        mx = i * cell + cell / 2
        _text(c, mx, y - BAND_H + 32, val,
              font='Helvetica-Bold', size=20, color=vc, align='center')
        _text(c, mx, y - BAND_H + 17, lbl,
              font='Helvetica-Bold', size=5.5, color=HexColor('#6EE7B7'),
              align='center')
        if i > 0:
            _rect(c, i * cell, y - BAND_H + 10, 0.5, 34, fill=HexColor('#065F46'))

    y -= BAND_H

    # ── Logo + website link ───────────────────────────────────────────────────
    LOGO_ROW_H = 36
    _rect(c, 0, y - LOGO_ROW_H, PAGE_W, LOGO_ROW_H,
          fill=HexColor('#F0FDF4'), stroke=None)
    _rect(c, 0, y, PAGE_W, 0.6, fill=HexColor('#D1FAE5'))
    _rect(c, 0, y - LOGO_ROW_H, PAGE_W, 0.6, fill=HexColor('#D1FAE5'))

    logo_img = _local_image(static_folder, 'assets/general/logo.png')
    logo_x = M
    if logo_img:
        c.drawImage(logo_img, logo_x, y - LOGO_ROW_H + 6, 22, 22,
                    preserveAspectRatio=True, mask='auto')
        logo_x += 28

    _text(c, logo_x, y - LOGO_ROW_H + 20, 'DSTAIR',
          font='Helvetica-Bold', size=11, color=C_EMERALD)
    _text(c, logo_x, y - LOGO_ROW_H + 8,
          'Institutional Integrity Assessment Platform',
          size=7, color=C_MUTED)
    _text(c, PAGE_W - M, y - LOGO_ROW_H + 20, 'dstair.in',
          font='Helvetica-Bold', size=9, color=C_EMERALD, align='right')
    _text(c, PAGE_W - M, y - LOGO_ROW_H + 8, 'Secure  ·  Evidence-based  ·  Open Research',
          size=6.5, color=C_MUTED, align='right')

    y -= LOGO_ROW_H

    # ── Definitions / Methodology card ────────────────────────────────────────
    DEF_H = y - 26 - 10    # fill remaining space above footer
    _rect(c, M, 26 + 10, CW, DEF_H, fill=C_LIGHT_BG, stroke=C_RULE, lw=0.5, r=6)

    dy = y - 16

    # Section label
    _text(c, M + 14, dy, 'UNDERSTANDING THIS REPORT',
          font='Helvetica-Bold', size=8, color=C_EMERALD)
    _rect(c, M + 14, dy - 5, CW - 28, 0.5, fill=C_RULE)
    dy -= 18

    # ① Aggregate Score definition
    _text(c, M + 14, dy, 'Aggregate Legitimacy Score',
          font='Helvetica-Bold', size=8, color=C_INK)
    dy -= 12
    agg_def = (
        'The aggregate score is the simple average of all sphere-level scores. '
        'Each sphere score is itself a weighted average of its question responses, '
        'normalised to a 0 – 1 scale (where 1 = highest institutional legitimacy '
        'and 0 = lowest). Questions with higher importance weights contribute '
        'proportionally more to their sphere score.'
    )
    # word-wrap the definition
    words = agg_def.split()
    line, lines = '', []
    for w in words:
        test = (line + ' ' + w).strip()
        if c.stringWidth(test, 'Helvetica', 7.5) < CW - 28:
            line = test
        else:
            lines.append(line); line = w
    if line: lines.append(line)
    for ln in lines:
        _text(c, M + 14, dy, ln, size=7.5, color=C_MUTED)
        dy -= 11

    dy -= 6

    # ② Tier system
    _text(c, M + 14, dy, 'Score Tier Classification',
          font='Helvetica-Bold', size=8, color=C_INK)
    dy -= 13

    tiers = [
        (C_GREEN_MID, 'STRONG',   '0.70 – 1.00',
         'Institutions show high legitimacy and effective reform capacity.'),
        (C_YELLOW,    'MODERATE', '0.40 – 0.69',
         'Moderate institutional health; targeted reforms are recommended.'),
        (C_RED,       'WEAK',     '0.00 – 0.39',
         'Significant institutional deficiencies; urgent intervention required.'),
    ]
    for col, label, rng, desc in tiers:
        _rect(c, M + 14, dy - 5, 8, 8, fill=col, r=2)
        _text(c, M + 26, dy, f'{label}  ({rng})',
              font='Helvetica-Bold', size=7.5, color=col)
        _text(c, M + 26, dy - 10, desc, size=7, color=C_MUTED)
        dy -= 22

    dy -= 4

    # ③ Analysis metadata
    _rect(c, M + 14, dy - 0.5, CW - 28, 0.5, fill=C_RULE)
    dy -= 12

    meta_items = [
        ('Country',  analysis.country),
        ('Analysis', analysis.title),
        ('Analyst',  username or 'N/A'),
        ('Generated', date_str),
    ]
    col_w = (CW - 28) / 2
    for i, (k, v) in enumerate(meta_items):
        mx2 = M + 14 + (i % 2) * col_w
        _text(c, mx2, dy,
              f'{k}:  {v[:38]}',
              size=7.5, color=C_INK)
        if i % 2 == 1:
            dy -= 13

    _page_footer(c, 1, analysis, TOTAL_PAGES)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — RADAR CHART + SPHERE SCORES
    # ══════════════════════════════════════════════════════════════════════════
    c.showPage()

    # Mini header
    _rect(c, 0, PAGE_H - 32, PAGE_W, 32, fill=C_FOREST)
    _rect(c, 0, PAGE_H - 32, 6, 32, fill=C_ORANGE)
    _text(c, 16, PAGE_H - 19, 'DSTAIR',
          font='Helvetica-Bold', size=9, color=C_ORANGE)
    _text(c, 62, PAGE_H - 19,
          f'{analysis.country}  ·  {analysis.title[:40]}',
          size=8, color=C_WHITE)
    _text(c, PAGE_W - M, PAGE_H - 19, 'Assessment Results',
          size=7.5, color=HexColor('#6EE7B7'), align='right')

    y = PAGE_H - 32 - 18

    # ── Radar chart ───────────────────────────────────────────────────────────
    y = _section_title(c, M, y, 'INSTITUTIONAL PROFILE  —  SPIDER CHART', CW)
    y -= 4

    RADAR_R    = 105
    LABEL_GAP  = 22   # must match _draw_radar
    radar_cx   = PAGE_W / 2
    radar_cy   = y - RADAR_R - 20
    _draw_radar(c, radar_cx, radar_cy, RADAR_R, sphere_scores)

    # Advance past the lowest labels (radius + gap + ~12pt font) + 20pt breathing room
    y = radar_cy - RADAR_R - LABEL_GAP - 12 - 20

    # ── Sphere score table ────────────────────────────────────────────────────
    y = _section_title(c, M, y, 'SPHERE-BY-SPHERE SCORES', CW)
    y -= 6

    # Column widths
    NAME_W  = 130
    BAR_W   = CW - NAME_W - 90   # track width
    SCORE_X = M + NAME_W + BAR_W + 8
    TIER_X  = SCORE_X + 35

    # Table header
    _rect(c, M, y - 16, CW, 16, fill=C_FOREST, r=4)
    _text(c, M + 8,          y - 11, 'SPHERE',
          font='Helvetica-Bold', size=6.5, color=HexColor('#6EE7B7'))
    _text(c, M + NAME_W + 6, y - 11, 'SCORE BAR',
          font='Helvetica-Bold', size=6.5, color=HexColor('#6EE7B7'))
    _text(c, SCORE_X,        y - 11, 'SCORE',
          font='Helvetica-Bold', size=6.5, color=HexColor('#6EE7B7'))
    _text(c, TIER_X,         y - 11, 'TIER',
          font='Helvetica-Bold', size=6.5, color=HexColor('#6EE7B7'))
    y -= 16

    ROW_H = 20
    for idx, (s, norm) in enumerate(sphere_scores):
        row_fill = C_LIGHT_BG if idx % 2 == 0 else C_WHITE
        _rect(c, M, y - ROW_H, CW, ROW_H, fill=row_fill)

        # Sphere name
        _text(c, M + 8, y - 13, s.label[:22],
              size=7.5, color=C_INK)

        # Bar track
        bar_x = M + NAME_W + 6
        track_y = y - ROW_H + 6
        _rect(c, bar_x, track_y, BAR_W, 8, fill=C_RULE, r=3)
        if norm is not None and norm > 0:
            fill_w = BAR_W * norm
            _rect(c, bar_x, track_y, fill_w, 8,
                  fill=_tier_color(norm), r=3)

        # Score value
        score_str = f'{norm:.3f}' if norm is not None else '—'
        _text(c, SCORE_X, y - 13, score_str,
              font='Helvetica-Bold', size=8,
              color=_tier_color(norm) if norm is not None else C_MUTED)

        # Tier label
        _text(c, TIER_X, y - 13, _tier_label(norm),
              font='Helvetica-Bold', size=7,
              color=_tier_color(norm) if norm is not None else C_MUTED)

        # Row bottom border
        _rect(c, M, y - ROW_H, CW, 0.4, fill=C_RULE)
        y -= ROW_H

    # Bottom border of table
    _rect(c, M, y, CW, 0.8, fill=C_EMERALD)

    _page_footer(c, 2, analysis, TOTAL_PAGES)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — TRIGGERED TOOLS
    # ══════════════════════════════════════════════════════════════════════════
    c.showPage()

    _rect(c, 0, PAGE_H - 32, PAGE_W, 32, fill=C_FOREST)
    _rect(c, 0, PAGE_H - 32, 6, 32, fill=C_ORANGE)
    _text(c, 16, PAGE_H - 19, 'DSTAIR',
          font='Helvetica-Bold', size=9, color=C_ORANGE)
    _text(c, 62, PAGE_H - 19,
          f'{analysis.country}  ·  {analysis.title[:40]}',
          size=8, color=C_WHITE)
    _text(c, PAGE_W - M, PAGE_H - 19, 'Intervention Tools',
          size=7.5, color=HexColor('#6EE7B7'), align='right')

    y = PAGE_H - 32 - 18

    y = _section_title(c, M, y,
                       f'TRIGGERED INTERVENTION TOOLS  ({len(triggered_tools)} of {len(tools)})',
                       CW)
    y -= 8

    if triggered_tools:
        # Column headers
        _rect(c, M, y - 16, CW, 16, fill=C_FOREST, r=4)
        _text(c, M + 8,       y - 11, '#',
              font='Helvetica-Bold', size=6.5, color=HexColor('#6EE7B7'))
        _text(c, M + 28,      y - 11, 'TOOL NAME',
              font='Helvetica-Bold', size=6.5, color=HexColor('#6EE7B7'))
        _text(c, PAGE_W - M - 70, y - 11, 'STATUS',
              font='Helvetica-Bold', size=6.5, color=HexColor('#6EE7B7'))
        y -= 16

        ROW_H = 22
        triggered_set = set(triggered_ids)
        for idx, tool in enumerate(tools):
            is_triggered = tool.id in triggered_set
            row_fill = HexColor('#FFFBEB') if is_triggered else C_LIGHT_BG
            _rect(c, M, y - ROW_H, CW, ROW_H, fill=row_fill)

            # Number
            _text(c, M + 8, y - 15,
                  str(idx + 1).zfill(2),
                  font='Helvetica-Bold', size=7.5, color=C_MUTED)

            # Tool name
            name_color = HexColor('#78350F') if is_triggered else C_INK
            _text(c, M + 28, y - 15, tool.title[:60],
                  font='Helvetica-Bold' if is_triggered else 'Helvetica',
                  size=8, color=name_color)

            # Status pill
            if is_triggered:
                pill_x = PAGE_W - M - 70
                pill_y = y - ROW_H + 6
                _rect(c, pill_x, pill_y, 62, 12, fill=C_AMBER, r=4)
                _text(c, pill_x + 31, pill_y + 3.5,
                      '✓  TRIGGERED',
                      font='Helvetica-Bold', size=6, color=C_WHITE,
                      align='center')
            else:
                _text(c, PAGE_W - M - 38, y - 15, '—',
                      size=8, color=C_MUTED, align='center')

            _rect(c, M, y - ROW_H, CW, 0.4, fill=C_RULE)
            y -= ROW_H

            if y < 50:
                _page_footer(c, 3, analysis, TOTAL_PAGES)
                c.showPage()
                _rect(c, 0, PAGE_H - 32, PAGE_W, 32, fill=C_FOREST)
                _rect(c, 0, PAGE_H - 32, 6, 32, fill=C_ORANGE)
                y = PAGE_H - 32 - 18

        _rect(c, M, y, CW, 0.8, fill=C_EMERALD)

    else:
        _rect(c, M, y - 40, CW, 40, fill=C_LIGHT_BG, stroke=C_RULE, lw=0.5, r=6)
        _text(c, PAGE_W / 2, y - 22,
              'No tools were triggered by the current assessment scores.',
              size=9, color=C_MUTED, align='center')
        _text(c, PAGE_W / 2, y - 35,
              f'{len(tools)} tools assessed  ·  0 triggered',
              size=7.5, color=C_MUTED, align='center')

    _page_footer(c, 3, analysis, TOTAL_PAGES)

    c.save()
    return buf.getvalue()
