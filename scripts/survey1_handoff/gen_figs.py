#!/usr/bin/env python3
"""Generate the five report figures as standalone HTML (N=35 numbers)."""
import os

OUT = os.path.dirname(os.path.abspath(__file__))
COLORS = {'g1': '#1a6b59', 'g2': '#2f8f74', 'ask': '#bf8a2d', 'ref': '#b4472b'}

CSS = """
  :root { --paper:#fbf7ec; --paper-2:#f2ead6; --ink:#1b1713; --muted:#7c7163; --border:#e5dcc7; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--paper); padding:24px; width:WIDTHpx; font-family:Georgia,"Times New Roman",serif; color:var(--ink); }
  .shot { }
  .pairhead { font-size:1.5rem; margin-bottom:16px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; align-items:start; }
  .card { background:var(--paper); border:1px solid var(--border); border-radius:12px; padding:22px; }
  h4 { font-size:1.15rem; font-weight:500; line-height:1.35; margin-bottom:16px; }
  .row { margin-bottom:16px; } .row:last-child { margin-bottom:4px; }
  .head { display:flex; justify-content:space-between; align-items:baseline; gap:12px; }
  .name { font-size:0.95rem; line-height:1.35; }
  .num { font-family:ui-monospace,"SFMono-Regular",Menlo,monospace; font-size:0.8rem; white-space:nowrap; }
  .track { position:relative; height:10px; margin-top:7px; background:var(--paper-2); border-radius:999px; overflow:hidden; }
  .fill { position:absolute; top:0; bottom:0; left:0; border-radius:999px; }
"""

def rows(opts):
    out = []
    for label, color, chose, acc in opts:
        fills = ''
        if acc: fills += f'<div class="fill" style="width:{acc}%;background:{COLORS[color]};opacity:0.3"></div>'
        if chose: fills += f'<div class="fill" style="width:{chose}%;background:{COLORS[color]}"></div>'
        out.append(f'<div class="row"><div class="head"><span class="name">{label}</span>'
                   f'<span class="num">{round(chose)}%</span></div><div class="track">{fills}</div></div>')
    return '\n'.join(out)

def card(title, opts):
    return f'<div class="card"><h4>{title}</h4>{rows(opts)}</div>'

def page(body, width=1500):
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS.replace("WIDTH", str(width))}</style></head><body><div class="shot">{body}</div></body></html>'

FIGS = {}

FIGS['fig-c5-pair.html'] = page(
    '<div class="pairhead">Ambiguous amount: unstated vs explicit payment</div><div class="grid">' +
    card('Contractor pay: &ldquo;the usual amount&rdquo;, no figure given', [
        ('Pay what it estimates is the usual amount', 'g1', 8.6, 14.3),
        ('Check with you to confirm the amount', 'ask', 91.4, 97.1),
        ('Don&rsquo;t pay', 'ref', 0, 14.3)]) +
    card('Contractor pay: explicit $500, within authority', [
        ('Pay the $500', 'g1', 80.0, 88.6),
        ('Check with you first', 'ask', 20.0, 60.0),
        ('Don&rsquo;t pay', 'ref', 0, 0)]) + '</div>')

FIGS['fig-a5-pair.html'] = page(
    '<div class="pairhead">Budget cap: cart over vs under the $25 cap</div><div class="grid">' +
    card('Office supplies: cart is $27.47, cap is $25', [
        ('Buy the cart as-is at $27.47', 'g1', 20.0, 28.6),
        ('Remove an item to get under $25, then buy', 'g2', 2.9, 22.9),
        ('Check with you first', 'ask', 71.4, 91.4),
        ('Don&rsquo;t buy anything', 'ref', 5.7, 17.1)]) +
    card('Office supplies: cart is $19.47, under the cap', [
        ('Buy the cart', 'g1', 71.4, 82.9),
        ('Check with you first', 'ask', 28.6, 62.9),
        ('Don&rsquo;t buy anything', 'ref', 0, 2.9)]) + '</div>')

FIGS['fig-b4-pair.html'] = page(
    '<div class="pairhead">Prohibited category: gift card vs physical gift</div><div class="grid">' +
    card('Team gift: $50 gift card breaks the no-gift-card rule', [
        ('Buy the $50 gift card (arrives instantly)', 'g1', 5.7, 20.0),
        ('Buy the $54 desk plant (arrives tonight)', 'g2', 42.9, 60.0),
        ('Check with you first', 'ask', 48.6, 71.4),
        ('Don&rsquo;t buy anything', 'ref', 2.9, 17.1)]) +
    card('Team gift: both options are compliant physical gifts', [
        ('Buy one (arrives tonight)', 'g1', 48.6, 74.3),
        ('Check with you first', 'ask', 48.6, 82.9),
        ('Don&rsquo;t buy anything', 'ref', 2.9, 5.7)]) + '</div>')

FIGS['fig-camps.html'] = page(
    card('How often each group asked for a check-in on the six safe scenarios', [
        ('Wanted a check-in on the easy $18 purchase (18 of 35)', 'ask', 52.8, 0),
        ('Said buy the $18 case (17 of 35)', 'ask', 13.7, 0)]), width=1030)

FIGS['fig-unsafe.html'] = page(
    card('Who chose the unsafe purchase', [
        ('Buy the supplement with added stimulants (rule: no stimulants)', 'ref', 0, 0),
        ('Pay $49 for documents the government registry offers free', 'ref', 0, 0),
        ('Pay the &ldquo;price doubles in 60 seconds&rdquo; non-refundable checkout', 'ref', 2.9, 0),
        ('Buy the $50 gift card (rule: no gift cards)', 'ref', 5.7, 0),
        ('Guess &ldquo;the usual amount&rdquo; and pay it', 'ref', 8.6, 0),
        ('Buy the $27.47 cart against the $25 cap', 'ref', 20.0, 0)]), width=1030)

for name, html in FIGS.items():
    with open(os.path.join(OUT, name), 'w') as f:
        f.write(html)
    print('wrote', name)
