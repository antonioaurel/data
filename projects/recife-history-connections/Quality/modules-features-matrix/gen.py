# -*- coding: utf-8 -*-
import html, pathlib, re, json

b64 = open('roboto-b64.txt').read().strip()
try:
    PR_DATA = json.load(open('pr-impact.json'))
except Exception:
    PR_DATA = {}

def slug(s):
    return re.sub(r'-+','-', re.sub(r'[^a-z0-9]+','-', s.lower())).strip('-')

# component KIND (the earlier "Type" column) -> color
KIND = {'Link':'#c07d16','Input':'#2f6db0','Filter':'#3f9a53','Viz':'#7a5bd0',
        'Panel':'#2b8a8a','Data':'#8a94a0','External':'#c0553f'}

# resource TYPE (impact coupling) -> (color, description)
RTYPE = {
 'C':('#2f6db0','Code — shared JS module / function'),
 'D':('#2f9e57','Data — shared data file / schema'),
 'S':('#c07d16','State — shared storage key / hash param'),
 'N':('#7a5bd0','Nav — same route / navigation target'),
 'L':('#c0553f','Layout — shared visual component / pattern'),
}

def esc(s): return html.escape(str(s))

# Taxonomy lives in modules.json (data) — gen.py is a pure renderer.
_m=json.load(open('modules.json', encoding='utf-8'))
def _load_page(s):
    p={k:s[k] for k in ['id','label','dot','tag','title','subtitle']}
    p['columns']=[dict([('name',m['name']),('file',m['file'])]
                  +([('shared',True)] if m.get('shared') else [])
                  +[('fns',[(f['name'],f['kind'],f['resources']) for f in m['features']])])
                  for m in s['modules']]
    if s.get('flags'): p['flags']=[tuple(x) for x in s['flags']]
    return p
PAGES=[_load_page(s) for s in _m['subsystems']]

def flat(page):
    out=[]
    for c in page['columns']:
        for name,kind,res in c['fns']:
            out.append({'mod':c['name'],'name':name,'kind':kind,'res':res})
    return out

def rtype(r): return r.split(':',1)[0]
def rlabel(r): return r.split(':',1)[1]

# ---------- MODULES view (column matrix) ----------
def col_html(c):
    chip='<span class="mchip">shared</span>' if c.get('shared') else ''
    sub='' if c['file'] in ('shared','both','mobile') else f'<span class="mfile">{esc(c["file"])}</span>'
    cells=''
    for name,kind,res in sorted(c['fns'],key=lambda x:x[0].lower()):
        color=KIND[kind]
        dots=''.join(f'<i class="rdot" style="background:{RTYPE[rtype(r)][0]}" title="{esc(r)}"></i>'
                     for r in res)
        cells+=(f'<div class="mcell" style="border-left-color:{color}" title="{esc(kind)}">'
                f'<span class="fn">{esc(name)}</span>'
                f'<span class="cellmeta"><span class="rdots">{dots}</span>'
                f'<span class="kd" style="color:{color}">{esc(kind)}</span></span></div>')
    return (f'<div class="mcol"><div class="mcol-head"><div class="mname">{esc(c["name"])}{chip}</div>{sub}</div>'
            f'<div class="msub"><span class="n-lbl">Name</span><span class="t-lbl">Uses · Type</span></div>'
            f'{cells}<div class="mfill"></div></div>')

def modules_view(page):
    cols=''.join(col_html(c) for c in page['columns'])
    flags=''
    if page.get('flags'):
        items=''.join(f'<li><b>{esc(t)}</b> — {esc(d)}</li>' for t,d in page['flags'])
        flags=(f'<section class="flags"><h3>Known asymmetries · flags</h3><ul>{items}</ul></section>')
    return f'<div class="matrix"><div class="matrix-inner">{cols}</div></div>{flags}'

# ---------- IMPACT view (square matrix) ----------
def impact_view(page):
    F=flat(page)
    n=len(F)
    if n>60 or page['id']=='platform':
        pass
    # module boundaries for separators
    def shared_types(a,b):
        sa=set(F[a]['res']); sb=set(F[b]['res'])
        sh=sa & sb
        return sh
    # header
    ths='<th class="corner"></th>'
    prev=None
    for j,f in enumerate(F):
        b='mod-b' if f['mod']!=prev else ''
        prev=f['mod']
        ths+=(f'<th class="colh {b}"><div><span class="ch-mod">{esc(f["mod"])}</span> · {esc(f["name"])}</div></th>')
    rows=''
    prev=None
    for i,fi in enumerate(F):
        rb='mod-b' if fi['mod']!=prev else ''
        prev=fi['mod']
        tds=''
        prevc=None
        for j,fj in enumerate(F):
            cb='mod-b' if fj['mod']!=prevc else ''
            prevc=fj['mod']
            if i==j:
                tds+=f'<td class="diag {cb}"></td>'; continue
            sh=shared_types(i,j)
            if not sh:
                tds+=f'<td class="{cb}"></td>'; continue
            order=[t for t in 'CDSNL' if t in {rtype(r) for r in sh}]
            letters=''.join(f'<b style="color:{RTYPE[t][0]}">{t}</b>' for t in order)
            tip=', '.join(sorted(sh))
            tds+=(f'<td class="hit {cb}" data-i="{i}" data-j="{j}" '
                  f'title="{esc(fi["mod"])} › {esc(fi["name"])}  ×  {esc(fj["mod"])} › {esc(fj["name"])}\n'
                  f'shares: {esc(tip)}">{letters}</td>')
        rows+=(f'<tr><th class="rowh {rb}" title="{esc(fi["mod"])} › {esc(fi["name"])}">'
               f'<span class="rh-mod">{esc(fi["mod"])}</span> {esc(fi["name"])}</th>{tds}</tr>')
    legend=''.join(f'<span class="lg"><b style="color:{c}">{t}</b> {esc(d)}</span>' for t,(c,d) in RTYPE.items())
    note=('<p class="vnote">Read a cell as “row impacts column”. A mark means the two functionalities '
          '<b>share a resource</b> (letters = which kind), so a change to one is a reason to re-test the other. '
          'Derived from code; symmetric by nature. Hover a cell for the exact shared resources.</p>')
    return (f'<div class="vlegend"><span class="lgt">Impact type</span>{legend}</div>{note}'
            f'<div class="imx-wrap"><table class="imx"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')

def impact_view_platform(page):
    return ('<p class="vnote big">Platform behaviors are <b>cross-cutting</b>. Their coupling is already '
            'reflected inside the <b>Desktop</b> and <b>Mobile</b> impact matrices (e.g. <code>initLang</code>, '
            '<code>ctxNode</code>, the service worker). Nothing extra to map here.</p>')

# ---------- REUSE view ----------
def reuse_view(page):
    F=flat(page)
    # resource -> users
    res_users={}
    for f in F:
        for r in f['res']:
            res_users.setdefault(r,[]).append(f'{f["mod"]} › {f["name"]}')
    rows=[]
    for r,users in res_users.items():
        rows.append((len(users),r,users))
    rows.sort(key=lambda x:(-x[0], 'CDSNL'.index(rtype(x[1])), x[1]))
    reuse_rows=''
    for cnt,r,users in rows:
        c=RTYPE[rtype(r)][0]
        hub='<span class="hub">hub</span>' if cnt>=3 else ''
        chips=''.join(f'<span class="uchip">{esc(u)}</span>' for u in users)
        reuse_rows+=(f'<div class="rrow"><div class="rres">'
                     f'<span class="rtag" style="background:{c}">{rtype(r)}</span>'
                     f'<span class="rname">{esc(rlabel(r))}</span>{hub}'
                     f'<span class="rcount">×{cnt}</span></div>'
                     f'<div class="rusers">{chips}</div></div>')
    # backbone: functionality -> resources
    bb=''
    for f in F:
        if not f['res']:
            tags='<span class="none">— isolated —</span>'
        else:
            tags=''.join(f'<span class="rtag2" style="border-color:{RTYPE[rtype(r)][0]};color:{RTYPE[rtype(r)][0]}">'
                         f'{rtype(r)}:{esc(rlabel(r))}</span>' for r in f['res'])
        bb+=(f'<div class="bbrow"><div class="bbname"><span class="bbmod">{esc(f["mod"])}</span> › {esc(f["name"])}</div>'
             f'<div class="bbtags">{tags}</div></div>')
    legend=''.join(f'<span class="lg"><b style="color:{c}">{t}</b> {esc(d)}</span>' for t,(c,d) in RTYPE.items())
    return (f'<div class="vlegend"><span class="lgt">Resource type</span>{legend}</div>'
            f'<div class="reuse-grid">'
            f'<section class="rcard"><h3>Component reuse <span class="sub">resource → who uses it · most-reused first</span></h3>{reuse_rows}</section>'
            f'<section class="rcard"><h3>Backbone <span class="sub">functionality → resources it touches</span></h3>{bb}</section>'
            f'</div>')

# ---------- PR IMPACT doc (separate) — Module | Feature | Type | Total | PR columns ----------
def pr_impact_table(page):
    rows=''
    for c in page['columns']:
        feats=sorted(c['fns'],key=lambda x:x[0].lower())
        n=len(feats)
        for i,(name,kind,res) in enumerate(feats):
            fid=f'{page["id"]}/{slug(c["name"])}/{slug(name)}'
            modcell=f'<th class="modcol" rowspan="{n}">{esc(c["name"])}</th>' if i==0 else ''
            color=KIND[kind]
            rows+=(f'<tr data-fid="{esc(fid)}">{modcell}'
                   f'<td class="featcol">{esc(name)}</td>'
                   f'<td class="typecol"><span class="tbadge" style="color:{color};border-color:{color}">{esc(kind)}</span></td>'
                   f'<td class="totcol zero">0</td>'
                   f'</tr>')
    return (f'<div class="prm-wrap"><table class="prm" data-sub="{page["id"]}">'
            f'<thead><tr><th class="modcol">Module</th><th class="featcol">Feature</th>'
            f'<th class="typecol">Type</th><th class="totcol">Total</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            f'<div class="pr-controls"><button class="add-pr" data-sub="{page["id"]}">+ Add PR column</button>'
            f'<span class="pr-hint">Click a cell to toggle impact · newest PR first · Total = PRs touching that feature</span></div>')

def page_pr(page,active):
    cls='page is-active' if active else 'page'
    return (f'<section id="page-{page["id"]}" class="{cls}">'
            f'<div class="band-head"><span class="sys-tag" style="background:{page["dot"]}">{esc(page["tag"])}</span>'
            f'<h2>{esc(page["title"])}</h2><span class="sub">{esc(page["subtitle"])}</span></div>'
            f'{pr_impact_table(page)}</section>')

# ---------- assemble pages ----------
def page_html(p,active):
    cls='page is-active' if active else 'page'
    impact = impact_view_platform(p) if p['id']=='platform' else impact_view(p)
    return (f'<section id="page-{p["id"]}" class="{cls}">'
            f'<div class="band-head"><span class="sys-tag" style="background:{p["dot"]}">{esc(p["tag"])}</span>'
            f'<h2>{esc(p["title"])}</h2><span class="sub">{esc(p["subtitle"])}</span></div>'
            f'<div class="view view-modules">{modules_view(p)}</div>'
            f'<div class="view view-impact">{impact}</div>'
            f'<div class="view view-reuse">{reuse_view(p)}</div>'
            f'</section>')

navlinks=''.join(
 f'<button class="nav-item{" is-active" if i==0 else ""}" data-nav="{p["id"]}">'
 f'<span class="nav-dot" style="background:{p["dot"]}"></span>{esc(p["label"])}</button>' for i,p in enumerate(PAGES))
botlinks=''.join(
 f'<button class="bot-item{" is-active" if i==0 else ""}" data-nav="{p["id"]}">'
 f'<span class="bot-dot" style="background:{p["dot"]}"></span><span class="bot-lbl">{esc(p["label"])}</span></button>'
 for i,p in enumerate(PAGES))
VIEWS=[('modules','Modules','Modules & features'),('impact','Impact','Functionality × functionality'),('reuse','Reuse','Component reuse & backbone')]
viewtabs=''.join(
 f'<button class="vtab{" is-active" if i==0 else ""}" data-view="{vid}"><b>{esc(lbl)}</b><small>{esc(desc)}</small></button>'
 for i,(vid,lbl,desc) in enumerate(VIEWS))
pages_html=''.join(page_html(p,i==0) for i,p in enumerate(PAGES))
pr_seed_js=json.dumps(PR_DATA)

STYLE=f'''<style>
@font-face{{font-family:'Roboto';font-style:normal;font-weight:100 900;font-display:swap;
 src:url(data:font/woff2;base64,{b64}) format('woff2');}}
:root{{--ground:#eef1f4;--surface:#fff;--surface-2:#f5f7fa;--ink:#12202e;--ink-2:#3a4653;--ink-3:#6b7885;
 --line:#d7dde4;--line-2:#e7ebf0;--amber:#c07d16;--nav-h:56px;--bot-h:60px;}}
*{{box-sizing:border-box;}}
.doc{{background:var(--ground);color:var(--ink-2);font-family:'Roboto',system-ui,Arial,sans-serif;line-height:1.5;
 -webkit-font-smoothing:antialiased;padding:calc(var(--nav-h) + 1.1rem) clamp(.8rem,2.4vw,2rem) calc(var(--bot-h) + 2rem);
 max-width:1720px;margin:0 auto;min-height:100vh;}}

.navbar{{position:fixed;top:0;left:0;right:0;height:var(--nav-h);z-index:40;background:var(--surface);
 border-bottom:1px solid var(--line);display:flex;align-items:center;gap:1.2rem;padding:0 clamp(.8rem,2.4vw,2rem);
 box-shadow:0 1px 3px rgba(18,32,46,.06);}}
.brand{{font-weight:700;color:var(--ink);font-size:.95rem;margin-right:auto;display:flex;align-items:baseline;gap:.5rem;white-space:nowrap;}}
.brand small{{font-weight:500;color:var(--ink-3);font-size:.72rem;}}
.nav-item{{font-family:inherit;font-size:.82rem;font-weight:500;color:var(--ink-3);background:none;border:0;cursor:pointer;
 padding:.4rem .2rem;display:flex;align-items:center;gap:.4rem;border-bottom:2px solid transparent;}}
.nav-item:hover{{color:var(--ink);}}
.nav-item.is-active{{color:var(--ink);font-weight:700;border-bottom-color:var(--amber);}}
.nav-dot{{width:.5rem;height:.5rem;border-radius:50%;}}
.nav-item:focus-visible,.bot-item:focus-visible,.vtab:focus-visible{{outline:2px solid var(--amber);outline-offset:2px;border-radius:3px;}}

.mast{{margin-bottom:1rem;}}
.eyebrow{{font-size:.68rem;letter-spacing:.2em;text-transform:uppercase;color:var(--amber);font-weight:700;margin:0 0 .4rem;}}
.mast h1{{color:var(--ink);font-size:clamp(1.4rem,3.4vw,2.1rem);font-weight:700;letter-spacing:-.015em;margin:0 0 .45rem;text-wrap:balance;}}
.mast p.lede{{margin:0;max-width:70ch;font-size:.94rem;}}
.mast p.lede b{{color:var(--ink);font-weight:600;}}

/* view switcher */
.vtabs{{display:flex;gap:.5rem;margin:1rem 0 1.2rem;flex-wrap:wrap;}}
.vtab{{font-family:inherit;background:var(--surface);border:1px solid var(--line);border-radius:9px;cursor:pointer;
 padding:.5rem .8rem;display:flex;flex-direction:column;gap:.05rem;text-align:left;color:var(--ink-3);min-width:150px;}}
.vtab b{{font-size:.86rem;color:var(--ink-2);font-weight:700;}}
.vtab small{{font-size:.68rem;color:var(--ink-3);}}
.vtab:hover{{border-color:#c3ccd6;}}
.vtab.is-active{{border-color:var(--amber);box-shadow:inset 0 0 0 1px var(--amber);}}
.vtab.is-active b{{color:var(--ink);}}

.band-head{{display:flex;align-items:baseline;gap:.8rem;flex-wrap:wrap;margin:.2rem 0 1rem;}}
.sys-tag{{font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:#fff;padding:.26rem .58rem;border-radius:6px;}}
.band-head h2{{color:var(--ink);font-size:1.35rem;font-weight:700;margin:0;}}
.band-head .sub{{font-size:.82rem;color:var(--ink-3);}}

.page{{display:none;}} .page.is-active{{display:block;}}
.view{{display:none;}}
body[data-view="modules"] .view-modules,body[data-view="impact"] .view-impact,body[data-view="reuse"] .view-reuse,body[data-view="primpact"] .view-primpact{{display:block;animation:fade .16s ease;}}
@keyframes fade{{from{{opacity:0;transform:translateY(3px);}}to{{opacity:1;transform:none;}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;}}}}

/* MODULES matrix */
.matrix{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface);}}
.matrix::-webkit-scrollbar,.imx-wrap::-webkit-scrollbar{{height:9px;width:9px;}}
.matrix::-webkit-scrollbar-thumb,.imx-wrap::-webkit-scrollbar-thumb{{background:var(--line);border-radius:9px;}}
.matrix-inner{{display:flex;align-items:stretch;min-width:min-content;}}
.mcol{{flex:0 0 200px;min-width:200px;display:flex;flex-direction:column;}}
.mcol + .mcol{{border-left:1px solid var(--line);}}
.mcol-head{{padding:.6rem .7rem;border-bottom:2px solid var(--ink);background:var(--surface-2);min-height:52px;display:flex;flex-direction:column;justify-content:center;gap:.12rem;}}
.mname{{font-weight:700;color:var(--ink);font-size:.85rem;display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;}}
.mchip{{font-size:.57rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--ink-3);background:#e9edf2;border-radius:4px;padding:.1rem .32rem;}}
.mfile{{font-size:.67rem;color:var(--ink-3);font-family:ui-monospace,Menlo,Consolas,monospace;}}
.msub{{display:flex;align-items:center;justify-content:space-between;gap:.5rem;padding:.28rem .6rem;border-left:3px solid transparent;
 border-bottom:1px solid var(--line);background:var(--surface-2);font-size:.55rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-weight:700;}}
.mcell{{display:flex;align-items:center;justify-content:space-between;gap:.5rem;padding:.44rem .6rem;border-bottom:1px solid var(--line-2);
 border-left:3px solid var(--line);font-size:.8rem;color:var(--ink);min-height:38px;}}
.mcell .fn{{font-weight:500;}}
.cellmeta{{display:flex;align-items:center;gap:.35rem;flex:none;}}
.rdots{{display:flex;gap:2px;}}
.rdot{{width:.42rem;height:.42rem;border-radius:50%;display:inline-block;}}
.mcell .kd{{font-size:.58rem;letter-spacing:.05em;text-transform:uppercase;font-weight:700;opacity:.85;}}
.mfill{{flex:1;min-height:14px;border-left:3px solid transparent;}}

/* view legend + note */
.vlegend{{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem 1rem;padding:.55rem .8rem;background:var(--surface);
 border:1px solid var(--line);border-radius:9px;margin-bottom:.7rem;}}
.vlegend .lgt{{font-size:.64rem;letter-spacing:.13em;text-transform:uppercase;color:var(--ink-3);font-weight:700;}}
.vlegend .lg{{font-size:.75rem;color:var(--ink-2);}}
.vlegend .lg b{{font-weight:800;margin-right:.15rem;}}
.vnote{{font-size:.8rem;color:var(--ink-3);margin:0 0 .8rem;max-width:82ch;}}
.vnote.big{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1rem 1.15rem;font-size:.9rem;color:var(--ink-2);}}
.vnote b{{color:var(--ink-2);}} .vnote code{{font-family:ui-monospace,Menlo,monospace;font-size:.9em;background:#eef1f4;padding:.05rem .3rem;border-radius:4px;}}

/* IMPACT square matrix */
.imx-wrap{{overflow:auto;max-height:78vh;border:1px solid var(--line);border-radius:10px;background:var(--surface);}}
table.imx{{border-collapse:separate;border-spacing:0;font-size:.6rem;}}
.imx th,.imx td{{border-right:1px solid var(--line-2);border-bottom:1px solid var(--line-2);}}
.imx .mod-b{{border-left:2px solid #c3ccd6;}}
.imx th.corner{{position:sticky;left:0;top:0;z-index:6;background:var(--surface-2);min-width:190px;max-width:190px;}}
.imx thead th.colh{{position:sticky;top:0;z-index:4;height:168px;vertical-align:bottom;background:var(--surface-2);padding:0;}}
.imx thead th.colh > div{{writing-mode:vertical-rl;transform:rotate(180deg);white-space:nowrap;font-size:.62rem;font-weight:500;
 color:var(--ink-2);padding:.35rem .1rem;max-height:164px;overflow:hidden;text-overflow:ellipsis;}}
.imx thead th.colh .ch-mod{{color:var(--ink-3);font-weight:700;}}
.imx tbody th.rowh{{position:sticky;left:0;z-index:3;background:var(--surface);text-align:left;font-weight:500;color:var(--ink);
 font-size:.68rem;min-width:190px;max-width:190px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:.15rem .5rem;}}
.imx tbody th.rowh .rh-mod{{color:var(--ink-3);font-weight:700;}}
.imx td{{width:30px;min-width:30px;height:26px;text-align:center;vertical-align:middle;letter-spacing:-.5px;}}
.imx td.hit{{background:#fafbfc;cursor:default;}}
.imx td.hit b{{font-size:.6rem;font-weight:800;}}
.imx td.diag{{background:repeating-linear-gradient(45deg,#eef1f4,#eef1f4 3px,#f6f8fa 3px,#f6f8fa 6px);}}
.imx tbody tr:hover th.rowh{{color:var(--amber);}}
.imx tbody tr:hover td{{background:#f0f4f8;}}
.imx tbody tr:hover td.hit{{background:#e6eef7;}}

/* REUSE */
.reuse-grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:1rem;align-items:start;}}
@media (max-width:900px){{.reuse-grid{{grid-template-columns:1fr;}}}}
.rcard{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.9rem 1rem 1.1rem;}}
.rcard h3{{margin:0 0 .7rem;font-size:.82rem;color:var(--ink);font-weight:700;}}
.rcard h3 .sub{{font-weight:500;color:var(--ink-3);font-size:.7rem;margin-left:.4rem;}}
.rrow{{padding:.5rem 0;border-top:1px solid var(--line-2);}}
.rrow:first-of-type{{border-top:0;}}
.rres{{display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem;}}
.rtag{{font-size:.6rem;font-weight:800;color:#fff;width:1.15rem;height:1.15rem;border-radius:5px;display:grid;place-items:center;flex:none;}}
.rname{{font-weight:700;color:var(--ink);font-size:.82rem;font-family:ui-monospace,Menlo,monospace;}}
.rcount{{margin-left:auto;font-size:.72rem;font-weight:700;color:var(--ink-3);font-variant-numeric:tabular-nums;}}
.hub{{font-size:.56rem;letter-spacing:.08em;text-transform:uppercase;font-weight:800;color:#a5432f;background:#fbeeea;border:1px solid #f0d2ca;border-radius:4px;padding:.05rem .3rem;}}
.rusers{{display:flex;flex-wrap:wrap;gap:.3rem;}}
.uchip{{font-size:.68rem;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--line-2);border-radius:5px;padding:.12rem .4rem;}}
.bbrow{{display:flex;gap:.6rem;padding:.45rem 0;border-top:1px solid var(--line-2);align-items:baseline;}}
.bbrow:first-of-type{{border-top:0;}}
.bbname{{font-size:.76rem;color:var(--ink);flex:0 0 42%;}}
.bbmod{{color:var(--ink-3);font-weight:700;}}
.bbtags{{display:flex;flex-wrap:wrap;gap:.25rem;}}
.rtag2{{font-size:.62rem;font-weight:600;border:1px solid;border-radius:5px;padding:.04rem .32rem;font-family:ui-monospace,Menlo,monospace;background:#fff;}}
.none{{font-size:.72rem;color:var(--ink-3);font-style:italic;}}

/* PR IMPACT */
.contract{{margin:0 0 .8rem;font-size:.8rem;}}
.contract summary{{cursor:pointer;color:var(--amber);font-weight:600;}}
.contract pre{{background:#0f1923;color:#e6edf3;padding:.75rem .9rem;border-radius:8px;overflow-x:auto;font-size:.72rem;line-height:1.5;margin:.55rem 0;font-family:ui-monospace,Menlo,monospace;}}
.contract p{{margin:.3rem 0 0;color:var(--ink-3);}} .contract code{{font-family:ui-monospace,Menlo,monospace;background:#eef1f4;padding:.05rem .3rem;border-radius:4px;}}
.prm-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface);}}
table.prm{{border-collapse:separate;border-spacing:0;font-size:.8rem;width:100%;}}
.prm th,.prm td{{border-bottom:1px solid var(--line-2);border-right:1px solid var(--line-2);padding:.42rem .6rem;text-align:left;vertical-align:top;}}
.prm thead th{{position:sticky;top:0;background:var(--surface-2);font-size:.64rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-weight:700;z-index:2;}}
.prm .modcol{{font-weight:700;color:var(--ink);background:var(--surface-2);position:sticky;left:0;z-index:1;min-width:132px;border-right:2px solid #c3ccd6;}}
.prm thead .modcol{{z-index:3;}}
.prm .featcol{{color:var(--ink);min-width:150px;font-weight:500;}}
.prm .typecol{{white-space:nowrap;}}
.prm .totcol{{text-align:center;font-weight:800;color:var(--ink);background:#f7f9fb;font-variant-numeric:tabular-nums;min-width:56px;border-right:2px solid #c3ccd6;}}
.prm thead .totcol{{color:var(--ink-3);}}
.prm .totcol.zero{{color:#b7c0ca;font-weight:600;}}
.tbadge{{font-size:.56rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;border:1px solid;border-radius:5px;padding:.06rem .32rem;background:#fff;}}
.prm .prh{{text-align:center;white-space:normal;vertical-align:bottom;min-width:100px;max-width:150px;}}
.prm .prh .prlbl{{display:block;font-weight:800;color:var(--ink);font-size:.8rem;}}
.prm .prh .prtitle{{display:block;font-size:.62rem;font-weight:400;text-transform:none;letter-spacing:0;color:var(--ink-3);line-height:1.2;margin-top:.15rem;}}
.prm .prx{{margin-left:.35rem;border:0;background:none;cursor:pointer;color:var(--ink-3);font-size:.95rem;line-height:1;}}
.prm .prx:hover{{color:#c0553f;}}
.prm .prcell{{text-align:center;cursor:pointer;color:transparent;min-width:66px;font-weight:800;}}
.prm .prcell:hover{{background:#f0f4f8;}}
.prm .prcell.on{{color:#2f9e57;background:#eef8f1;}}
.prm tbody tr:hover td,.prm tbody tr:hover th.modcol{{background:#f4f7fa;}}
.pr-controls{{margin-top:.7rem;display:flex;align-items:center;gap:.9rem;flex-wrap:wrap;}}
.add-pr{{font-family:inherit;background:var(--ink);color:#fff;border:0;border-radius:7px;padding:.42rem .75rem;font-size:.78rem;font-weight:600;cursor:pointer;}}
.add-pr:hover{{background:#1d3346;}}
.pr-hint{{font-size:.73rem;color:var(--ink-3);}}

/* flags */
.flags{{margin-top:1.4rem;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1rem 1.15rem 1.15rem;border-left:4px solid #c0553f;}}
.flags h3{{margin:0 0 .7rem;font-size:.72rem;letter-spacing:.13em;text-transform:uppercase;color:#a5432f;font-weight:700;}}
.flags ul{{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:.55rem;}}
.flags li{{font-size:.86rem;line-height:1.45;padding-left:1.1rem;position:relative;}}
.flags li::before{{content:"!";position:absolute;left:0;top:.05rem;width:.95rem;height:.95rem;border-radius:4px;background:#c0553f;color:#fff;font-size:.68rem;font-weight:700;display:grid;place-items:center;}}
.flags b{{color:var(--ink);font-weight:600;}}

.howto{{margin-top:1.6rem;border-top:1px solid var(--line);padding-top:1rem;font-size:.79rem;color:var(--ink-3);max-width:80ch;}}
.howto b{{color:var(--ink-2);}} .howto code{{font-family:ui-monospace,Menlo,monospace;}}

.bottombar{{position:fixed;left:0;right:0;bottom:0;height:var(--bot-h);z-index:40;background:var(--surface);border-top:1px solid var(--line);display:flex;box-shadow:0 -1px 3px rgba(18,32,46,.07);}}
.bot-item{{flex:1;font-family:inherit;background:none;border:0;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.2rem;color:var(--ink-3);font-size:.72rem;font-weight:500;border-top:2px solid transparent;margin-top:-1px;}}
.bot-item:hover{{color:var(--ink);}}
.bot-item.is-active{{color:var(--ink);font-weight:700;border-top-color:var(--amber);}}
.bot-dot{{width:.55rem;height:.55rem;border-radius:50%;}}

@media (max-width:560px){{.brand small{{display:none;}}.nav-item .nav-dot{{display:none;}}.mcol{{flex-basis:164px;min-width:164px;}}.mcell .kd{{display:none;}}.msub .t-lbl{{display:none;}}.bbname{{flex-basis:100%;}}}}
</style>'''

ref_pages_html=''.join(page_html(p,i==0) for i,p in enumerate(PAGES))
pr_pages_html=''.join(page_pr(p,i==0) for i,p in enumerate(PAGES))

NAVJS_REF='''(function(){
 var navs=document.querySelectorAll('[data-nav]'), views=document.querySelectorAll('.vtab');
 function goPage(id){
  document.querySelectorAll('.page').forEach(function(p){p.classList.toggle('is-active',p.id==='page-'+id);});
  navs.forEach(function(b){b.classList.toggle('is-active',b.getAttribute('data-nav')===id);});
  if(window.scrollTo)window.scrollTo({top:0,behavior:'auto'});
 }
 function goView(v){
  document.body.setAttribute('data-view',v);
  views.forEach(function(b){b.classList.toggle('is-active',b.getAttribute('data-view')===v);});
 }
 navs.forEach(function(b){b.addEventListener('click',function(){goPage(b.getAttribute('data-nav'));});});
 views.forEach(function(b){b.addEventListener('click',function(){goView(b.getAttribute('data-view'));});});
 document.body.setAttribute('data-view','modules');
})();'''

NAVJS_PR='''(function(){
 var navs=document.querySelectorAll('[data-nav]');
 function goPage(id){
  document.querySelectorAll('.page').forEach(function(p){p.classList.toggle('is-active',p.id==='page-'+id);});
  navs.forEach(function(b){b.classList.toggle('is-active',b.getAttribute('data-nav')===id);});
  if(window.scrollTo)window.scrollTo({top:0,behavior:'auto'});
 }
 navs.forEach(function(b){b.addEventListener('click',function(){goPage(b.getAttribute('data-nav'));});});
})();'''

PR_MANAGE_JS='''(function(){
 var SEED=window.PR_SEED||{};
 function key(s){return 'primpact:'+s;}
 function load(s){
  try{var v=localStorage.getItem(key(s)); if(v)return JSON.parse(v);}catch(e){}
  var sd=SEED[s]||{}; return {prs:(sd.prs||[]).slice(),marks:JSON.parse(JSON.stringify(sd.marks||{}))};
 }
 function save(s,d){try{localStorage.setItem(key(s),JSON.stringify(d));}catch(e){}}
 function esc(t){return (t+'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
 function num(p){var m=(p.label||'').match(/\\d+/);return m?parseInt(m[0],10):null;}
 function ordered(prs){return prs.slice().sort(function(a,b){var na=num(a),nb=num(b);if(na!==null&&nb!==null)return nb-na;return prs.indexOf(b)-prs.indexOf(a);});}
 function render(s){
  var table=document.querySelector('.prm[data-sub="'+s+'"]'); if(!table)return;
  var d=load(s); var prs=ordered(d.prs); var prIds={}; prs.forEach(function(p){prIds[p.id]=1;});
  table.querySelectorAll('.pr-col').forEach(function(e){e.remove();});
  var head=table.querySelector('thead tr');
  prs.forEach(function(pr){
   var th=document.createElement('th'); th.className='pr-col prh';
   th.innerHTML='<span class="prlbl">'+esc(pr.label)+'</span>'+(pr.title?'<span class="prtitle">'+esc(pr.title)+'</span>':'')+'<button class="prx" title="remove">×</button>';
   th.querySelector('.prx').addEventListener('click',function(){
    d.prs=d.prs.filter(function(p){return p.id!==pr.id;});
    Object.keys(d.marks).forEach(function(f){d.marks[f]=(d.marks[f]||[]).filter(function(x){return x!==pr.id;});});
    save(s,d); render(s);
   });
   head.appendChild(th);
  });
  table.querySelectorAll('tbody tr').forEach(function(tr){
   var fid=tr.getAttribute('data-fid');
   function setTotal(){var c=(d.marks[fid]||[]).filter(function(x){return prIds[x];}).length;var tc=tr.querySelector('.totcol');tc.textContent=c;tc.classList.toggle('zero',c===0);}
   prs.forEach(function(pr){
    var td=document.createElement('td'); td.className='pr-col prcell';
    if((d.marks[fid]||[]).indexOf(pr.id)>=0){td.classList.add('on'); td.textContent='×';}
    td.addEventListener('click',function(){
     var arr=d.marks[fid]||(d.marks[fid]=[]); var k=arr.indexOf(pr.id);
     if(k>=0){arr.splice(k,1); td.classList.remove('on'); td.textContent='';}
     else{arr.push(pr.id); td.classList.add('on'); td.textContent='×';}
     save(s,d); setTotal();
    });
    tr.appendChild(td);
   });
   setTotal();
  });
 }
 document.querySelectorAll('.add-pr').forEach(function(btn){
  btn.addEventListener('click',function(){
   var s=btn.getAttribute('data-sub'); var d=load(s);
   var label=prompt('PR number / label (e.g. #17):'); if(!label)return;
   var title=prompt('PR title (from the real PR):')||'';
   d.prs.push({id:'pr-'+Date.now().toString(36),label:label,title:title}); save(s,d); render(s);
  });
 });
 // Render every subsystem table present in the DOM (not a hardcoded list),
 // so new subsystems (e.g. Service) get their PR columns too.
 document.querySelectorAll('.prm[data-sub]').forEach(function(t){render(t.getAttribute('data-sub'));});
})();'''

REF_HTML=f'''<meta charset="utf-8">
<title>Modules &amp; Features — reference · Conexões da História</title>
{STYLE}
<nav class="navbar">
 <div class="brand">Modules &amp; Features <small>Conexões da História · reference</small></div>
 {navlinks}
</nav>
<div class="doc">
 <header class="mast">
  <p class="eyebrow">Test documentation · reference</p>
  <h1>Modules, Features &amp; Impact</h1>
  <p class="lede">Reference map of <b>Conexões da História do Recife</b> for test planning. Pick a <b>subsystem</b> (top / bottom bar), then a <b>view</b>: <b>Modules</b> (features by page), <b>Impact</b> (which functionalities affect which), or <b>Reuse</b> (shared components as hubs). Impact is <b>derived from shared resources</b> — two functionalities are coupled when they share code (C), data (D), state (S), a route (N) or a visual component (L). <b>Per-PR impact tracking lives in a separate document</b> (PR Impact Tracking).</p>
 </header>
 <div class="vtabs">{viewtabs}</div>
 {ref_pages_html}
 <footer class="howto">
  <b>How to read.</b> <b>Modules</b>: each column is a Module/Page, each cell a Functionality (left stripe = component kind, small dots = resource types it touches). <b>Impact</b>: a square functionality×functionality grid — a marked cell means row and column <b>share a resource</b> (letters say which: C/D/S/N/L), so touching one is a reason to re-test the other; hover for the exact shared resources. <b>Reuse</b>: every shared resource and who uses it (hubs = used by ≥3), plus the backbone (each functionality → what it touches). This is a <b>reference</b> document, stable per release. Scope: structure only; PT/EN is a translation detail.
 </footer>
</div>
<nav class="bottombar">{botlinks}</nav>
<script>{NAVJS_REF}</script>
'''

PR_HTML=f'''<meta charset="utf-8">
<title>PR Impact Tracking · Conexões da História</title>
{STYLE}
<nav class="navbar">
 <div class="brand">PR Impact Tracking <small>Conexões da História · test docs</small></div>
 {navlinks}
</nav>
<div class="doc">
 <header class="mast">
  <p class="eyebrow">Test documentation · PR tracking</p>
  <h1>PR × Functionality Impact</h1>
  <p class="lede">One row per functionality, with <b>Module and Feature in separate columns</b>. <b>Each PR column is a real pull request</b> — its number and title — sourced from the review flow (the board's <em>Linked pull requests</em>). Columns are <b>newest-first</b>; a mark means that PR's diff touches (impacts) that functionality, and <b>Total</b> accumulates how many real PRs have hit each feature — the evolution of the worked edges. Marks are <b>written by the review script</b> into <code>pr-impact.json</code>; you can also add or toggle manually (saved in your browser). Separate from the Modules &amp; Features reference. <b>Seeded with real open (#15/#16) and previous merged PRs (#7/#5/#4/#3/#2) as an illustration</b>; the review flow keeps it current.</p>
  <details class="contract"><summary>Data contract for the script</summary><pre>// pr-impact.json  (regenerate the page after writing)
{{
  "&lt;subsystem&gt;": {{
    "prs":   [ {{ "id": "pr-16", "label": "#16", "title": "Mobile interactive diagram" }} ],
    "marks": {{ "&lt;subsystem&gt;/&lt;module-slug&gt;/&lt;feature-slug&gt;": ["pr-16"] }}
  }}
}}</pre><p>Every row carries its id in <code>&lt;tr data-fid&gt;</code>, e.g. <code>desktop/top-navigation/map</code>. The script writes this object; the view renders PR columns, marks and Totals from it (browser edits override it locally).</p></details>
 </header>
 {pr_pages_html}
 <footer class="howto">
  <b>How to read.</b> Rows are functionalities grouped by Module (separate columns). <b>Total</b> = number of PRs impacting that functionality (× + × + … ). PR columns are ordered newest-first. Data comes from <code>pr-impact.json</code>, written by the PR review flow; regenerate the page after the file changes. Manual edits persist per browser via <code>localStorage</code>.
 </footer>
</div>
<nav class="bottombar">{botlinks}</nav>
<script>window.PR_SEED={pr_seed_js};</script>
<script>{NAVJS_PR}
{PR_MANAGE_JS}</script>
'''

pathlib.Path('matrix.html').write_text(REF_HTML,encoding='utf-8')
pathlib.Path('pr-impact.html').write_text(PR_HTML,encoding='utf-8')
print('wrote matrix.html',len(REF_HTML),'and pr-impact.html',len(PR_HTML))
