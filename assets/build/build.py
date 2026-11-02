"""Build the nlhogsten profile SVGs from the approved round-10 mock.

Each SVG embeds subset WOFF2 fonts (GitHub serves README SVGs as <img>, which can't
fetch web fonts but can use data: URIs). Text stays real <text>, so it's selectable
when the SVG is opened directly. Usage: build.py <fonts-dir> <out-dir>
"""
import base64, io, os, sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

FONTS, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

PAL = {
    'dark':  dict(bg='#0b1020', fg='#eef1f8', body='#c9cfdc', mute='#8a93a8', red='#ff5a4e', cyan='#3fd8ff', blue='#6c78ff', violet='#b07cff', blend='screen'),
    'light': dict(bg='#f6f7fa', fg='#121726', body='#2c3344', mute='#5d6679', red='#d6362a', cyan='#0a8db3', blue='#3a47d6', violet='#7040d6', blend='multiply'),
}

# ---------- fonts ----------
_src = {}
def font(fam, w):
    k = (fam, w)
    if k not in _src:
        if fam == 'Syne':
            f = TTFont(os.path.join(FONTS, 'Syne%5Bwght%5D.ttf'))
            f = instancer.instantiateVariableFont(f, {'wght': w})
        else:
            name = {400: 'Regular', 500: 'Medium', 600: 'SemiBold'}[w]
            f = TTFont(os.path.join(FONTS, f'IBMPlexMono-{name}.ttf'))
        _src[k] = f
    return _src[k]

def width(s, fam, w, size, ls=0):
    f = font(fam, w)
    cmap, hmtx, upm = f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm
    adv = sum(hmtx[cmap.get(ord(ch), cmap[ord('?')])][0] for ch in s)
    return adv * size / upm + ls * len(s)

def woff2(fam, w, chars):
    buf = io.BytesIO()
    font(fam, w).save(buf)
    buf.seek(0)
    f = TTFont(buf)
    opts = subset.Options(); opts.flavor = 'woff2'; opts.layout_features = ['kern', 'liga']
    opts.name_IDs = []; opts.drop_tables += ['DSIG']
    s = subset.Subsetter(opts); s.populate(text=chars + ' '); s.subset(f)
    out = io.BytesIO(); f.flavor = 'woff2'; f.save(out)
    return base64.b64encode(out.getvalue()).decode()

# ---------- svg helpers ----------
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')

class Doc:
    def __init__(self, c):
        self.c, self.uid, self.used = c, 0, {}
    def id(self, p):
        self.uid += 1; return f'{p}{self.uid}'
    def T(self, x, y, s, size=14, fill=None, mono=False, w=None, ls=0, anchor=None, raw=False, plain=None):
        fam = 'IBM Plex Mono' if mono else 'Syne'
        w = w or (400 if mono else 700)
        self.used.setdefault((fam, w), set()).update(plain if plain is not None else s)
        a = f' text-anchor="{anchor}"' if anchor else ''
        return (f'<text x="{x:g}" y="{y:g}" fill="{fill or self.c["fg"]}" font-family="{fam}" '
                f'font-size="{size:g}" font-weight="{w}" letter-spacing="{ls:g}"{a}>{s if raw else esc(s)}</text>')
    def svg(self, W, H, body, label):
        faces = ''
        for (fam, w), chars in sorted(self.used.items()):
            key = 'Syne' if fam == 'Syne' else 'Mono'
            faces += (f"@font-face{{font-family:'{fam}';font-weight:{w};"
                      f"src:url(data:font/woff2;base64,{woff2(key, w, ''.join(sorted(chars)))}) format('woff2')}}")
        style = (faces +
                 '@keyframes drift{0%{transform:translate(0,0)}100%{transform:translate(-80px,-14px)}}'
                 '@keyframes breathe{0%,100%{opacity:.45}50%{opacity:1}}'
                 '@media (prefers-reduced-motion:reduce){*{animation:none!important}}')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" width="{W:g}" height="{H:g}" '
                f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title><style>{style}</style>'
                f'<rect width="{W:g}" height="{H:g}" rx="12" fill="{self.c["bg"]}"/>{body}</svg>')

def wrap(text, maxw, fam, w, size):
    lines, cur = [], ''
    for word in text.split(' '):
        t = (cur + ' ' + word).strip()
        if cur and width(t, fam, w, size) > maxw:
            lines.append(cur); cur = word
        else:
            cur = t
    if cur: lines.append(cur)
    return lines

def rings(cx, cy, col, n, step, sw):
    return ''.join(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"/>'
                   for r in range(step, n * step, step))

def spec_line(d, x, y0, y1, col, dashed, dur, delay):
    f = d.id('sl'); da = ' stroke-dasharray="6 5"' if dashed else ''
    return (f'<defs><filter id="{f}" x="-300%" y="-10%" width="700%" height="120%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
            f'<g style="animation:breathe {dur}s ease-in-out {delay}s infinite">'
            f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{col}" stroke-width="8" filter="url(#{f})" opacity="0.75"{da}/>'
            f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{col}" stroke-width="2"{da}/></g>')

# ---------- pieces ----------
def hero(c, narrow):
    d = Doc(c)
    W = 440 if narrow else 880
    target = W - (36 if narrow else 80)
    z = min(150, 100 * target / width('HOGSTEN', 'Syne', 800, 100))
    b1 = round(30 + 0.72 * z); b2 = round(b1 + 0.92 * z)
    cy = (b1 + b2) / 2 - 0.3 * z
    ax, bx = W * 400 / 880, W * 480 / 880
    A, B = rings(ax, cy, c['cyan'], 56, 9, 1.7), rings(bx, cy + 10, c['red'], 56, 9, 1.7)
    tags = ([('AI PLATFORM', 'red'), (' + ', None), ('FULL-STACK', 'cyan'), (' ENGINEERING', None)],
            [('B.S. CHEMISTRY', 'blue'), (', UH MĀNOA  ·  HONOLULU', None)])
    if not narrow:
        tags = (tags[0] + [('  ·  ', None)] + tags[1],)
    tag0 = b2 + (40 if narrow else 46)
    H = tag0 + 18 * (len(tags) - 1) + 30
    mid = d.id('im')
    def field():
        return (f'<g style="isolation:isolate"><g style="mix-blend-mode:{c["blend"]}">{A}</g>'
                f'<g style="mix-blend-mode:{c["blend"]}"><g style="animation:drift 15s ease-in-out infinite alternate">{B}</g></g></g>')
    s = (f'<mask id="{mid}"><rect width="{W}" height="{H}" fill="black"/>'
         + d.T(W / 2, b1, 'NATE', size=z, fill='white', w=800, anchor='middle')
         + d.T(W / 2, b2, 'HOGSTEN', size=z, fill='white', w=800, anchor='middle') + '</mask>'
         f'<clipPath id="{mid}c"><rect width="{W}" height="{H}" rx="12"/></clipPath>'
         f'<g clip-path="url(#{mid}c)"><g opacity="0.12">{field()}</g><g mask="url(#{mid})">{field()}</g></g>')
    for i, parts in enumerate(tags):
        raw = ''.join(f'<tspan fill="{c[k]}">{esc(t)}</tspan>' if k else esc(t) for t, k in parts)
        plain = ''.join(t for t, _ in parts)
        s += d.T(W / 2, tag0 + 18 * i, raw, size=11 if narrow else 12, fill=c['mute'], mono=True, w=500,
                 ls=0.4, anchor='middle', raw=True, plain=plain)
    return d.svg(W, H, s, 'Nate Hogsten. AI platform and full-stack engineering. B.S. Chemistry, UH Mānoa. Honolulu.')

def section(c, narrow, title=None, tag=None, col='red', dashed=False, dur=5, delay=0, paras=(), big=False, items=()):
    d = Doc(c); col = c[col]
    W = 440 if narrow else 880
    lx, x = (18, 36) if narrow else (28, 52)
    maxw = W - x - (20 if narrow else 36)
    lh, body, y = 18, '', 40
    if title:
        body += d.T(x, y, title, size=22, fill=col, ls=1)
        if tag: body += d.T(x, y + 20, tag, size=10, fill=c['mute'], mono=True, w=500, ls=0.6)
        y += 48 if tag else 30
    else:
        y = 42
    for pi, p in enumerate(paras):
        isbig = big and pi == 0
        fam, w, size, plh = ('Syne', 600, 13.5, 22) if isbig else ('IBM Plex Mono', 400, 11.5, lh)
        for l in wrap(p, maxw, 'Syne' if isbig else 'Mono', w, size):
            body += d.T(x, y, l, size=size, fill=c['fg'] if isbig else c['body'], mono=not isbig, w=w)
            y += plh
        y += 12
    for label, kcol, text in items:
        icol = c[kcol] if kcol else col
        lines = wrap(f'{label} — {text}', maxw, 'Mono', 400, 11.5)
        for j, l in enumerate(lines):
            if j == 0:
                n = len(label)
                d.used.setdefault(('IBM Plex Mono', 600), set()).update(label)
                raw = f'<tspan fill="{icol}" font-weight="600">{esc(l[:n])}</tspan>{esc(l[n:])}'
                body += d.T(x, y, raw, size=11.5, fill=c['body'], mono=True, raw=True, plain=l[n:])
            else:
                body += d.T(x, y, l, size=11.5, fill=c['body'], mono=True)
            y += lh
        y += 9
    H = y + 14
    s = spec_line(d, lx, 26, H - 24, col, dashed, dur, delay) + body
    label = '. '.join(filter(None, [title] + list(paras))) + ' ' + ' '.join(f'{a}: {t}' for a, _, t in items)
    return d.svg(W, H, s, label.strip())

BIO = ['AI platform and full-stack engineer based in Honolulu, architecting an internal AI developer platform and building production systems across the stack, from frontend apps and backend services to data warehouses, pipelines, and cloud infrastructure. Trained as a chemist at UH Mānoa, with a background in lab research and environmental data analysis, and the founder of Kaimuki Compost Collective, which ran from 2022 to 2025 on software built in-house.',
       'A personal GitHub for creative projects and experiments; professional work lives in private repositories.']
SKILLS = [
    ('AI PLATFORM', None, 'architecture of internal AI developer platforms: agent harnesses across Claude Code, Codex and Cursor, MCP servers and routing, shared skills and context, hooks, permissions and governed sessions, run tracking with audit trails, and the CLI that ties it together.'),
    ('FRONTEND', 'cyan', 'production web apps and data-heavy dashboards in TypeScript, React, Next.js and Vite, with Tailwind, component systems, charting, and end-to-end testing in Playwright.'),
    ('BACKEND', 'cyan', 'services and APIs in TypeScript (Node, Express, NestJS, Bun/Hono), Python (FastAPI) and Rust: REST APIs, auth, background jobs, and Postgres / Supabase data layers.'),
    ('DATA WAREHOUSES + PIPELINES', 'blue', 'Snowflake and Postgres warehouses modeled with dbt and SQL, ingestion orchestrated on AWS Step Functions and ECS, backfills, data quality checks, and the analytics layers that APIs and dashboards read from.'),
    ('CI/CD + INFRASTRUCTURE', 'blue', 'GitHub Actions and Azure DevOps pipelines, infrastructure as code in Terraform, Docker, and cloud across AWS, Azure and Google Cloud.'),
]
TUSK = 'Gives AI coding agents one shared setup across Claude Code, Codex and Cursor: the same skills and rules in every tool, secrets they can use without ever seeing, a window for asking a person for input or approval, and run records that survive context compaction.'

for mode, c in PAL.items():
    for narrow in (False, True):
        sfx = f'{mode}{"-narrow" if narrow else ""}'
        files = {
            'hero': hero(c, narrow),
            'bio': section(c, narrow, col='cyan', dur=4.5, delay=-0.8, big=True, paras=BIO),
            'skills': section(c, narrow, col='red', dur=5, delay=-1.5, items=SKILLS),
            'tusk': section(c, narrow, title='TUSK', tag='PRIVATE · PRE-RELEASE', col='violet', dashed=True, dur=6, paras=[TUSK]),
        }
        for k, v in files.items():
            with open(os.path.join(OUT, f'{k}-{sfx}.svg'), 'w') as fh:
                fh.write(v)
print('ok')
