# Momentum Design System — HTML, CSS e SVG

> Documento técnico visual baseado no painel de referência enviado.  
> Objetivo: registrar o design system em formato **Markdown**, com tokens visuais, CSS, HTML e SVG reutilizáveis.

---

## 1. Identidade

**Nome:** Momentum  
**Slogan:** Get 400% more done  
**Assinatura:** by vyre lab  
**Categoria visual:** SaaS premium, produtividade, workspace, dashboard, automação e performance.

A identidade visual combina:

- fundo off-white quente;
- preto/marrom profundo;
- laranja vibrante como cor principal;
- cards arredondados;
- sombra suave;
- grid editorial;
- UI limpa com aparência de produto real;
- ícones lineares com cantos arredondados;
- dashboards com cards, calendário, heatmap e métricas.

---

## 2. Tokens de cor

| Nome | Hex | Uso |
|---|---:|---|
| Black | `#130600` | Texto principal, fundos escuros, sidebar ativa |
| Dark Orange | `#1B0B03` | Profundidade, cards escuros, sombras |
| Off White | `#F5F3F1` | Fundo geral |
| Paper | `#FFFDFB` | Cards principais |
| Peach | `#FFCDB6` | Estados leves, gráficos, fundos de apoio |
| Signal Orange | `#FF5300` | Cor primária, CTA, destaque, logo |
| Orange Tint | `#FF8A4D` | Hover, gráficos, acentos secundários |
| Muted Text | `#918985` | Texto secundário |
| Border | `#E8DDD6` | Bordas leves |

---

## 3. Tipografia

**Fonte:** Outfit  
**Pesos:** Light, Regular, Medium, SemiBold  
**Uso:** títulos, UI, botões, labels, cards e números grandes.

```css
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

:root {
  --font-main: 'Outfit', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

---

## 4. SVG — Logo Momentum

```html
<svg class="momentum-logo" viewBox="0 0 120 120" aria-label="Momentum logo">
  <path d="M60 8 L108 34 L108 86 L60 112 L12 86 L12 34 Z" fill="#FF5300"/>
  <path d="M60 23 L94 41 L76 51 L60 43 L44 51 L26 41 Z" fill="#fff"/>
  <path d="M26 79 L44 69 L60 77 L76 69 L94 79 L60 98 Z" fill="#fff"/>
  <path d="M21 48 L45 60 L21 72 Z" fill="#fff"/>
  <path d="M99 48 L75 60 L99 72 Z" fill="#fff"/>
  <circle cx="60" cy="60" r="18" fill="#FF5300"/>
</svg>
```

---

## 5. SVG — Ícones lineares

Os ícones usam `stroke-width: 2`, `stroke-linecap: round` e `stroke-linejoin: round`.

```html
<svg class="icon" viewBox="0 0 24 24"><path d="M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/><path d="M9 21v-6h6v6"/></svg>
<svg class="icon" viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>
<svg class="icon" viewBox="0 0 24 24"><path d="M7 3h8l4 4v14H7z"/><path d="M15 3v5h5"/><path d="M10 12h6M10 16h6"/></svg>
<svg class="icon accent" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01M16 17h.01"/></svg>
<svg class="icon" viewBox="0 0 24 24"><path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5z"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.05.05a2 2 0 1 1-2.83 2.83l-.05-.05A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .6 1.8 1.8 0 0 0-.5 1.27V21a2 2 0 1 1-4 0v-.1A1.8 1.8 0 0 0 8 19.4a1.8 1.8 0 0 0-1.98.36l-.05.05a2 2 0 1 1-2.83-2.83l.05-.05A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-.6-1 1.8 1.8 0 0 0-1.27-.5H3a2 2 0 1 1 0-4h.1A1.8 1.8 0 0 0 4.6 8a1.8 1.8 0 0 0-.36-1.98l-.05-.05a2 2 0 1 1 2.83-2.83l.05.05A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-.6 1.8 1.8 0 0 0 .5-1.27V3a2 2 0 1 1 4 0v.1A1.8 1.8 0 0 0 16 4.6a1.8 1.8 0 0 0 1.98-.36l.05-.05a2 2 0 1 1 2.83 2.83l-.05.05A1.8 1.8 0 0 0 19.4 9c.2.36.5.7.95.95.38.22.8.32 1.25.32H21a2 2 0 1 1 0 4h-.1A1.8 1.8 0 0 0 19.4 15z"/></svg>
<svg class="icon" viewBox="0 0 24 24"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M7 15c2-5 4 2 6-3 1-3 3-4 5-2"/></svg>
<svg class="icon accent" viewBox="0 0 24 24"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M8 14a7 7 0 1 1 8 0c-.8.7-1 1.7-1 3H9c0-1.3-.2-2.3-1-3z"/></svg>
<svg class="icon" viewBox="0 0 24 24"><path d="M21 12a8 8 0 0 1-8 8H8l-5 3 1.6-5A8 8 0 1 1 21 12z"/><path d="M9 12h6"/></svg>
<svg class="icon" viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="3"/><circle cx="12" cy="10" r="3"/><path d="M7.5 18a5 5 0 0 1 9 0"/></svg>
<svg class="icon" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8 12l2.5 2.5L16 9"/><path d="M17.5 5.5 20 3"/></svg>
```

---

## 6. HTML completo — Design System fiel ao painel

> Copie o bloco abaixo para um arquivo `momentum-design-system.html` e abra no navegador.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Momentum Design System</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {
  --black: #130600;
  --dark-orange: #1B0B03;
  --off-white: #F5F3F1;
  --paper: #FFFDFB;
  --paper-2: #FAF3EF;
  --peach: #FFCDB6;
  --signal-orange: #FF5300;
  --orange-tint: #FF8A4D;
  --muted: #918985;
  --muted-2: #B7AEA8;
  --line: #E8DDD6;
  --font-main: 'Outfit', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --radius-xl: 34px;
  --radius-lg: 24px;
  --radius-md: 18px;
  --shadow-soft: 0 24px 70px rgba(27, 11, 3, .08);
  --shadow-card: 0 16px 40px rgba(27, 11, 3, .055);
}

* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; }
body {
  font-family: var(--font-main);
  color: var(--black);
  background:
    radial-gradient(circle at 10% 5%, rgba(255,205,182,.40), transparent 28%),
    radial-gradient(circle at 90% 0%, rgba(255,83,0,.10), transparent 32%),
    linear-gradient(135deg, #F5F3F1 0%, #FFFDFB 48%, #F4E9E3 100%);
  -webkit-font-smoothing: antialiased;
}

.design-board {
  width: 100%;
  max-width: 1448px;
  min-height: 1086px;
  margin: 0 auto;
  padding: 28px;
  display: grid;
  grid-template-columns: 380px 1fr 395px;
  grid-template-rows: 285px 250px 282px 246px;
  gap: 14px;
}

.panel {
  background: rgba(255,253,251,.82);
  border: 1px solid rgba(232,221,214,.78);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 24px;
  overflow: hidden;
}

.section-title {
  font-size: 13px;
  font-weight: 900;
  letter-spacing: .02em;
  text-transform: uppercase;
  margin: 0 0 22px;
}

/* Brand / Header */
.brand-panel {
  grid-column: 1 / 2;
  grid-row: 1 / 2;
  background: transparent;
  border: 0;
  box-shadow: none;
  padding: 16px 18px;
}

.brand-panel h1 {
  font-size: 52px;
  line-height: .95;
  letter-spacing: -.055em;
  margin: 0 0 12px;
  font-weight: 800;
}

.brand-panel .subtitle {
  color: var(--muted);
  font-size: 19px;
  margin: 0 0 34px;
  font-weight: 400;
}

.brand-lockup {
  display: grid;
  grid-template-columns: 82px 1fr;
  gap: 18px;
  align-items: center;
}

.momentum-logo { width: 80px; height: 80px; display: block; }
.brand-lockup strong {
  display: block;
  font-size: 44px;
  letter-spacing: -.05em;
  line-height: 1;
}
.brand-lockup span {
  display: block;
  color: var(--muted);
  font-size: 22px;
  margin-top: 5px;
}
.brand-lockup small {
  display: block;
  color: var(--muted);
  font-size: 14px;
  margin-top: 7px;
}
.brand-lockup small b { color: var(--signal-orange); }

/* Palette */
.palette-panel {
  grid-column: 2 / 3;
  grid-row: 1 / 2;
}
.swatches {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
}
.swatch-box {
  height: 92px;
  border-radius: 12px;
  border: 1px solid rgba(19,6,0,.10);
  margin-bottom: 14px;
}
.swatch-name { font-size: 12px; font-weight: 700; margin-bottom: 3px; }
.swatch-hex { font-size: 12px; color: var(--muted); }

/* Typography */
.type-panel {
  grid-column: 3 / 4;
  grid-row: 1 / 2;
  position: relative;
}
.type-panel .font-name {
  font-size: 42px;
  letter-spacing: -.045em;
  line-height: .95;
  margin-bottom: 9px;
}
.type-panel .weights { font-size: 18px; line-height: 1.28; color: var(--black); }
.type-panel .weights b { font-weight: 800; }
.type-panel .sample {
  position: absolute;
  right: 36px;
  top: 54px;
  font-size: 124px;
  line-height: .8;
  color: var(--signal-orange);
  letter-spacing: -.08em;
  font-weight: 400;
}
.type-panel .alphabet {
  position: absolute;
  left: 24px;
  bottom: 24px;
  color: var(--muted-2);
  font-size: 13px;
  line-height: 1.45;
}

/* UI Components */
.components-panel {
  grid-column: 1 / 3;
  grid-row: 2 / 4;
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 20px;
}
.sidebar-ui {
  background: var(--paper);
  border-radius: 16px;
  padding: 14px 12px;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--line);
}
.mini-logo-row { display: flex; gap: 8px; align-items: center; margin-bottom: 18px; }
.mini-logo { width: 24px; height: 24px; }
.mini-logo-row strong { font-size: 10px; display: block; }
.mini-logo-row span { display: block; color: var(--muted); font-size: 7px; }
.side-section { font-size: 9px; color: var(--muted-2); margin: 15px 0 7px; text-transform: uppercase; }
.side-item {
  height: 27px;
  display: grid;
  grid-template-columns: 18px 1fr auto;
  align-items: center;
  font-size: 10px;
  color: var(--black);
  padding: 0 8px;
  border-radius: 7px;
  margin-bottom: 4px;
}
.side-item.active { background: var(--dark-orange); color: #fff; }
.side-item .count { color: var(--muted); font-size: 9px; }
.avatar-line { display: flex; align-items: center; gap: 6px; font-size: 9px; margin: 7px 0; }
.avatar { width: 16px; height: 16px; border-radius: 50%; background: linear-gradient(135deg, var(--peach), var(--dark-orange)); }
.pro-btn {
  margin-top: 18px;
  height: 32px;
  border-radius: 8px;
  border: 0;
  width: 100%;
  color: #fff;
  background: var(--signal-orange);
  font-size: 9px;
  font-weight: 700;
}
.component-area { min-width: 0; }
.button-row { display: grid; grid-template-columns: 160px 160px 44px 100px; gap: 18px; margin: 20px 0; align-items: center; }
.btn { height: 40px; border-radius: 9px; border: 1px solid var(--line); font-family: var(--font-main); font-weight: 700; font-size: 12px; }
.btn.primary { background: var(--signal-orange); color: #fff; border-color: var(--signal-orange); }
.btn.secondary { background: #fff; color: var(--black); }
.btn.icon-only { width: 44px; background: #fff; }
.cards-grid { display: grid; grid-template-columns: 1fr 1.25fr; gap: 12px; }
.ui-card {
  background: linear-gradient(145deg,#fff,#FFF8F4);
  border: 1px solid var(--line);
  border-radius: 17px;
  padding: 16px;
  min-height: 155px;
}
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.card-title { display: flex; gap: 8px; align-items: center; font-weight: 700; font-size: 13px; }
.tiny-icon { width: 22px; height: 22px; border-radius: 50%; background: var(--black); color: #fff; display: inline-grid; place-items: center; font-size: 10px; }
.view-all { background: rgba(19,6,0,.05); border: 0; border-radius: 999px; padding: 6px 12px; font-size: 10px; }
.big-num { font-size: 32px; letter-spacing: -.04em; margin: 0; }
.card-copy { font-size: 12px; color: var(--muted); margin: 2px 0 12px; }
.mini-chart { height: 58px; display: grid; grid-template-columns: 1fr 36px .45fr; gap: 6px; align-items: stretch; margin-top: 18px; }
.striped {
  border-radius: 14px;
  background: repeating-linear-gradient(75deg, rgba(255,83,0,.35), rgba(255,83,0,.35) 3px, transparent 3px, transparent 7px), #FFE3D7;
  position: relative;
}
.striped::after { content: '1,302'; position: absolute; left: 42%; top: 45%; transform: translate(-50%,-50%); font-weight: 800; font-size: 18px; }
.solid-bar { border-radius: 15px; background: var(--signal-orange); }
.chart-labels { display: flex; justify-content: space-between; font-size: 11px; font-weight: 700; margin-top: 9px; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.heatmap { display: grid; grid-template-columns: repeat(12, 1fr); gap: 5px; margin-top: 18px; }
.heatmap span { height: 18px; border-radius: 4px; background: var(--peach); opacity: .55; }
.heatmap span.hot { background: var(--signal-orange); opacity: 1; }
.heatmap span.mid { background: var(--orange-tint); opacity: .85; }
.legend { display: flex; gap: 12px; font-size: 10px; color: var(--muted); margin-top: 8px; }
.legend i { width: 7px; height: 7px; border-radius: 50%; display: inline-block; background: var(--signal-orange); margin-right: 4px; }
.calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 9px; text-align: center; font-size: 12px; margin-top: 22px; }
.calendar-grid b { color: var(--muted-2); font-weight: 500; }
.calendar-grid .active-day { background: var(--signal-orange); color: #fff; border-radius: 50%; width: 24px; height: 24px; display: inline-grid; place-items: center; margin: 0 auto; }
.task-box { display: flex; align-items: center; gap: 12px; margin-top: 24px; }
.check { width: 18px; height: 18px; border-radius: 50%; border: 1px solid var(--muted-2); display: grid; place-items: center; }
.task-text strong { display: block; font-size: 13px; }
.task-text span { color: var(--muted); font-size: 11px; }

/* Icons */
.icons-panel { grid-column: 3 / 4; grid-row: 2 / 3; }
.icon-grid { display: grid; grid-template-columns: repeat(5, 1fr); row-gap: 24px; align-items: center; justify-items: center; }
.icon { width: 34px; height: 34px; fill: none; stroke: var(--black); stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; }
.icon.accent { stroke: var(--signal-orange); }
.icon-caption { color: var(--muted); font-size: 12px; text-align: center; margin-top: 20px; }

/* Metrics */
.metrics-panel { grid-column: 3 / 4; grid-row: 3 / 4; position: relative; }
.metrics-panel .label { font-size: 13px; color: var(--black); margin-bottom: 10px; }
.metrics-panel .metric-number { font-size: 80px; color: var(--signal-orange); letter-spacing: -.055em; line-height: 1; font-weight: 400; }
.metric-chart { position: absolute; left: 28px; bottom: 46px; width: 220px; height: 92px; display: grid; grid-template-columns: 1fr 1fr; align-items: end; }
.metric-chart .left-bars { height: 82px; background: repeating-linear-gradient(to bottom, rgba(255,255,255,.45), rgba(255,255,255,.45) 1px, transparent 1px, transparent 25px), var(--orange-tint); border-radius: 14px 14px 0 0; opacity: .75; }
.metric-card { position: absolute; right: 34px; bottom: 38px; width: 150px; height: 130px; background: #fff; border-radius: 22px; box-shadow: var(--shadow-card); padding: 22px; }
.metric-card strong { color: var(--signal-orange); font-size: 25px; }
.metric-card .bar { position: absolute; right: 32px; bottom: 0; width: 54px; height: 70px; background: var(--signal-orange); border-radius: 10px 10px 0 0; }
.metric-caption { position: absolute; left: 28px; bottom: 17px; color: var(--muted); font-size: 12px; }

/* Timeline */
.timeline-panel { grid-column: 1 / 2; grid-row: 4 / 5; background: linear-gradient(145deg,#171515,#232020); color: #fff; border-radius: 20px; padding: 24px; }
.timeline-panel .section-title { color: #fff; margin-bottom: 32px; }
.timeline-date { position: absolute; }
.timeline-head { display: flex; justify-content: space-between; color: rgba(255,255,255,.72); font-size: 12px; margin-bottom: 18px; }
.gantt { height: 145px; position: relative; display: grid; grid-template-columns: repeat(12,1fr); gap: 0; }
.gantt::before { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(to right, transparent, transparent 55px, rgba(255,255,255,.10) 56px, transparent 57px); }
.phase { font-size: 12px; color: rgba(255,255,255,.75); font-weight: 500; }
.phase span { color: rgba(255,255,255,.32); margin-left: 8px; }
.bar-pill { position: absolute; height: 32px; border-radius: 999px; background: #2A2828; display: flex; align-items: center; padding: 0 24px; font-size: 11px; color: #fff; }
.bar-orange { background: var(--signal-orange); color: var(--black); }

/* Mockups */
.mockups-panel { grid-column: 2 / 3; grid-row: 3 / 5; background: transparent; border: 0; box-shadow: none; padding: 0 8px; overflow: visible; }
.mockup-title { font-size: 13px; font-weight: 900; margin: 5px 0 12px; }
.laptop { height: 300px; position: relative; }
.laptop-screen { width: 380px; height: 235px; background: #111; border-radius: 18px 18px 8px 8px; padding: 10px; margin: 0 auto; box-shadow: 0 28px 55px rgba(19,6,0,.23); }
.screen-ui { height: 100%; background: var(--paper); border-radius: 9px; display: grid; grid-template-columns: 70px 1fr; overflow: hidden; }
.screen-side { background: #fff; border-right: 1px solid var(--line); padding: 8px; }
.screen-main { padding: 12px; background: linear-gradient(145deg,#FFFDFB,#FFF3EC); }
.screen-hero { height: 86px; background: radial-gradient(circle at 65% 35%, var(--signal-orange), var(--black)); border-radius: 10px; margin: 10px 0; }
.screen-cards { display: grid; grid-template-columns: repeat(3,1fr); gap: 7px; }
.screen-cards span { height: 45px; border-radius: 8px; background: #fff; border: 1px solid var(--line); }
.laptop-base { width: 455px; height: 22px; background: linear-gradient(#444,#222); border-radius: 0 0 30px 30px; margin: -1px auto 0; }
.device-row { display: flex; gap: 24px; align-items: flex-end; justify-content: center; margin-top: 12px; }
.phone { width: 105px; height: 220px; border-radius: 24px; background: #111; padding: 7px; box-shadow: 0 18px 40px rgba(19,6,0,.18); }
.phone-ui { height: 100%; background: var(--paper); border-radius: 18px; padding: 12px 9px; }
.phone-card { height: 62px; border-radius: 12px; background: linear-gradient(145deg,#fff,#FFE4D6); margin: 10px 0; }
.phone-chart { height: 42px; border-radius: 9px; background: repeating-linear-gradient(75deg,rgba(255,83,0,.35),rgba(255,83,0,.35) 3px,transparent 3px,transparent 6px),#FFE4D6; }
.watch { width: 105px; height: 124px; border-radius: 32px; background: #111; padding: 10px; box-shadow: 0 18px 40px rgba(19,6,0,.18); }
.watch-ui { height: 100%; background: #080707; color: #fff; border-radius: 24px; padding: 12px; }
.watch-ui strong { font-size: 22px; display: block; }
.watch-chart { height: 35px; border-radius: 8px; background: repeating-linear-gradient(75deg,rgba(255,83,0,.65),rgba(255,83,0,.65) 3px,transparent 3px,transparent 6px),#4A1606; margin-top: 12px; }

/* Brand Applications */
.applications { display: grid; grid-template-columns: 70px 70px 160px; gap: 18px; align-items: end; margin-top: 14px; }
.app-icon, .social-avatar { width: 64px; height: 64px; border-radius: 14px; display: grid; place-items: center; }
.app-icon { background: var(--signal-orange); }
.social-avatar { background: linear-gradient(145deg,var(--black),#6A2307); }
.app-icon svg, .social-avatar svg { width: 42px; height: 42px; }
.app-label { font-size: 11px; text-align: center; margin-top: 8px; }
.profile-card { width: 160px; height: 100px; background: #fff; border-radius: 8px; border: 1px solid var(--line); overflow: hidden; font-size: 7px; }
.profile-cover { height: 35px; background: linear-gradient(135deg,var(--black),var(--signal-orange)); }
.profile-body { padding: 8px; position: relative; }
.follow { position: absolute; right: 8px; top: -12px; background: var(--black); color: #fff; border: 0; border-radius: 99px; font-size: 6px; padding: 4px 10px; }
.profile-body strong { display: block; font-size: 8px; }
.profile-body p { margin: 4px 0 0; font-size: 6px; color: var(--black); }

@media (max-width: 1100px) {
  .design-board { grid-template-columns: 1fr; grid-template-rows: auto; min-height: auto; }
  .brand-panel, .palette-panel, .type-panel, .components-panel, .icons-panel, .metrics-panel, .timeline-panel, .mockups-panel { grid-column: 1; grid-row: auto; }
  .components-panel { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<main class="design-board">
  <section class="brand-panel panel">
    <h1>Momentum<br>Design System</h1>
    <p class="subtitle">Brand, UI and product language</p>
    <div class="brand-lockup">
      <svg class="momentum-logo" viewBox="0 0 120 120" aria-label="Momentum logo">
        <path d="M60 8 L108 34 L108 86 L60 112 L12 86 L12 34 Z" fill="#FF5300"/>
        <path d="M60 23 L94 41 L76 51 L60 43 L44 51 L26 41 Z" fill="#fff"/>
        <path d="M26 79 L44 69 L60 77 L76 69 L94 79 L60 98 Z" fill="#fff"/>
        <path d="M21 48 L45 60 L21 72 Z" fill="#fff"/>
        <path d="M99 48 L75 60 L99 72 Z" fill="#fff"/>
        <circle cx="60" cy="60" r="18" fill="#FF5300"/>
      </svg>
      <div>
        <strong>Momentum</strong>
        <span>Get 400% more done</span>
        <small>by <b>vyre lab</b></small>
      </div>
    </div>
  </section>

  <section class="palette-panel panel">
    <h2 class="section-title">01. Color Palette</h2>
    <div class="swatches">
      <div><div class="swatch-box" style="background:#130600"></div><div class="swatch-name">Black</div><div class="swatch-hex">#130600</div></div>
      <div><div class="swatch-box" style="background:#1B0B03"></div><div class="swatch-name">Dark Orange</div><div class="swatch-hex">#1B0B03</div></div>
      <div><div class="swatch-box" style="background:#F5F3F1"></div><div class="swatch-name">Off White</div><div class="swatch-hex">#F5F3F1</div></div>
      <div><div class="swatch-box" style="background:#FFCDB6"></div><div class="swatch-name">Peach</div><div class="swatch-hex">#FFCDB6</div></div>
      <div><div class="swatch-box" style="background:#FF5300"></div><div class="swatch-name">Signal Orange</div><div class="swatch-hex">#FF5300</div></div>
      <div><div class="swatch-box" style="background:#FF8A4D"></div><div class="swatch-name">Orange Tint</div><div class="swatch-hex">#FF8A4D</div></div>
    </div>
  </section>

  <section class="type-panel panel">
    <h2 class="section-title">02. Typography – Outfit</h2>
    <div class="font-name">Outfit</div>
    <div class="weights">Light<br>Regular<br><b>Medium</b><br><b>SemiBold</b></div>
    <div class="sample">Aa</div>
    <div class="alphabet">Aa Bb Cc Dd Ee Ff Gg Hh Ii Jj Kk Ll Mm Nn<br>Oo Pp Qq Rr Ss Tt Uu Vv Ww Xx Yy Zz<br>0123456789 !@#$%^&amp;*()_+</div>
  </section>

  <section class="components-panel panel">
    <aside class="sidebar-ui">
      <div class="mini-logo-row">
        <svg class="mini-logo" viewBox="0 0 120 120"><path d="M60 8 L108 34 L108 86 L60 112 L12 86 L12 34 Z" fill="#FF5300"/><path d="M60 23 L94 41 L76 51 L60 43 L44 51 L26 41 Z" fill="#fff"/><path d="M26 79 L44 69 L60 77 L76 69 L94 79 L60 98 Z" fill="#fff"/><circle cx="60" cy="60" r="18" fill="#FF5300"/></svg>
        <div><strong>Momentum</strong><span>Team's workspace</span></div>
      </div>
      <div class="side-section">General</div>
      <div class="side-item active"><span>⌂</span><span>Dashboard</span></div>
      <div class="side-item"><span>□</span><span>Templates</span></div>
      <div class="side-item"><span>◌</span><span>Products</span><span class="count">13</span></div>
      <div class="side-item"><span>⌘</span><span>Docs</span><span class="count">56</span></div>
      <div class="side-item"><span>◔</span><span>Messages</span><span class="count">4</span></div>
      <div class="side-section">More</div>
      <div class="side-item"><span>☑</span><span>To do lists</span></div>
      <div class="side-item" style="color:#ff4667"><span>✦</span><span>AI Assistants</span></div>
      <div class="side-section">Interactions</div>
      <div class="avatar-line"><i class="avatar"></i>Dann Petty</div>
      <div class="avatar-line"><i class="avatar"></i>Flux Academy</div>
      <div class="avatar-line"><i class="avatar"></i>Michelle Choi</div>
      <div class="side-item" style="color:var(--muted)"><span>⌄</span><span>Show more (14)</span></div>
      <button class="pro-btn">Upgrade to PRO</button>
    </aside>

    <div class="component-area">
      <h2 class="section-title">03. UI Components</h2>
      <div class="button-row">
        <button class="btn primary">Primary Button</button>
        <button class="btn secondary">Secondary Button</button>
        <button class="btn icon-only">↻</button>
        <span style="font-size:12px;font-weight:700">Icon Button</span>
      </div>
      <div class="cards-grid">
        <div class="ui-card">
          <div class="card-top"><div class="card-title"><span class="tiny-icon">✺</span>Updates</div><button class="view-all">View all</button></div>
          <h3 class="big-num">1,892</h3>
          <p class="card-copy">Total updates for the project</p>
          <div class="mini-chart"><div class="striped"></div><div class="solid-bar"></div><div class="striped"></div></div>
          <div class="chart-labels"><span>90%</span><span>6%</span><span>4%</span></div>
        </div>
        <div class="ui-card">
          <div class="card-top"><div class="card-title"><span class="tiny-icon">▣</span>KPI</div><button class="view-all">View all</button></div>
          <h3 class="big-num">3.78</h3>
          <p class="card-copy">-5.6% from previous weeks</p>
          <div class="legend"><span><i style="background:#FFCDB6"></i>Low</span><span><i style="background:#FF8A4D"></i>Medium</span><span><i></i>High</span><span><i style="background:#C93C00"></i>Fully Occupied</span></div>
          <div class="heatmap">
            <span></span><span class="mid"></span><span></span><span></span><span class="hot"></span><span class="mid"></span><span></span><span class="hot"></span><span></span><span class="mid"></span><span></span><span></span>
            <span></span><span></span><span class="hot"></span><span></span><span class="hot"></span><span class="hot"></span><span class="mid"></span><span></span><span class="hot"></span><span class="hot"></span><span></span><span></span>
            <span class="mid"></span><span class="hot"></span><span class="hot"></span><span class="mid"></span><span class="hot"></span><span class="hot"></span><span></span><span class="hot"></span><span class="mid"></span><span></span><span class="hot"></span><span></span>
          </div>
        </div>
        <div class="ui-card">
          <div class="card-top"><div class="card-title"><span class="tiny-icon">◷</span>Calendar</div></div>
          <div style="text-align:center;font-weight:700;margin:12px 0">February 2026</div>
          <div class="calendar-grid"><b>Mon</b><b>Tue</b><b>Wed</b><b>Thu</b><b>Fri</b><b>Sat</b><b>Sun</b><span>16</span><span>17</span><span>18</span><span><span class="active-day">19</span></span><span>20</span><span>21</span><span>22</span></div>
        </div>
        <div class="ui-card">
          <div class="card-top"><div class="card-title"><span class="tiny-icon">☷</span>Task / List Item</div></div>
          <div class="task-box"><span class="check">✓</span><div class="task-text"><strong>Prepare technical specifications</strong><span>Due in 2 days</span></div></div>
        </div>
      </div>
    </div>
  </section>

  <section class="icons-panel panel">
    <h2 class="section-title">04. Icons</h2>
    <div class="icon-grid">
      <svg class="icon" viewBox="0 0 24 24"><path d="M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/><path d="M9 21v-6h6v6"/></svg>
      <svg class="icon" viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>
      <svg class="icon" viewBox="0 0 24 24"><path d="M7 3h8l4 4v14H7z"/><path d="M15 3v5h5"/><path d="M10 12h6M10 16h6"/></svg>
      <svg class="icon accent" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01M16 17h.01"/></svg>
      <svg class="icon" viewBox="0 0 24 24"><path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5z"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.05.05a2 2 0 1 1-2.83 2.83l-.05-.05A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .6 1.8 1.8 0 0 0-.5 1.27V21a2 2 0 1 1-4 0v-.1A1.8 1.8 0 0 0 8 19.4a1.8 1.8 0 0 0-1.98.36l-.05.05a2 2 0 1 1-2.83-2.83l.05-.05A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-.6-1 1.8 1.8 0 0 0-1.27-.5H3a2 2 0 1 1 0-4h.1A1.8 1.8 0 0 0 4.6 8a1.8 1.8 0 0 0-.36-1.98l-.05-.05a2 2 0 1 1 2.83-2.83l.05.05A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-.6 1.8 1.8 0 0 0 .5-1.27V3a2 2 0 1 1 4 0v.1A1.8 1.8 0 0 0 16 4.6a1.8 1.8 0 0 0 1.98-.36l.05-.05a2 2 0 1 1 2.83 2.83l-.05.05A1.8 1.8 0 0 0 19.4 9c.2.36.5.7.95.95.38.22.8.32 1.25.32H21a2 2 0 1 1 0 4h-.1A1.8 1.8 0 0 0 19.4 15z"/></svg>
      <svg class="icon" viewBox="0 0 24 24"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M7 15c2-5 4 2 6-3 1-3 3-4 5-2"/></svg>
      <svg class="icon accent" viewBox="0 0 24 24"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M8 14a7 7 0 1 1 8 0c-.8.7-1 1.7-1 3H9c0-1.3-.2-2.3-1-3z"/></svg>
      <svg class="icon" viewBox="0 0 24 24"><path d="M21 12a8 8 0 0 1-8 8H8l-5 3 1.6-5A8 8 0 1 1 21 12z"/><path d="M9 12h6"/></svg>
      <svg class="icon" viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="3"/><circle cx="12" cy="10" r="3"/><path d="M7.5 18a5 5 0 0 1 9 0"/></svg>
      <svg class="icon" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8 12l2.5 2.5L16 9"/><path d="M17.5 5.5 20 3"/></svg>
    </div>
    <p class="icon-caption">Consistent line weight, rounded joins, friendly tech feel.</p>
  </section>

  <section class="metrics-panel panel">
    <h2 class="section-title">08. Impact / Metrics</h2>
    <div class="label">Hours Saved</div>
    <div class="metric-number">92,400</div>
    <div class="metric-chart"><div class="left-bars"></div></div>
    <div class="metric-card"><strong>+12,7K</strong><div class="bar"></div></div>
    <div class="metric-caption">Total hours saved across all projects this month.</div>
  </section>

  <section class="timeline-panel panel">
    <div style="display:flex;justify-content:space-between;align-items:center"><h2 class="section-title">05. Roadmap / Timeline</h2><span style="font-size:12px;color:rgba(255,255,255,.62)">Oct – Dec 2025</span></div>
    <div class="timeline-head"><div class="phase">DISCOVERY <span>8 DAYS</span></div><div class="phase">STRATEGY <span>16 DAYS</span></div><div class="phase">SOLUTIONS <span>32 DAYS</span></div></div>
    <div class="gantt">
      <div class="bar-pill" style="left:0;top:18px;width:180px">Analysis</div>
      <div class="bar-pill" style="left:62px;top:64px;width:160px">Research</div>
      <div class="bar-pill" style="left:210px;top:18px;width:110px">Branding</div>
      <div class="bar-pill" style="left:250px;top:64px;width:185px">Functional development</div>
      <div class="bar-pill" style="left:330px;top:110px;width:145px">Wireframing</div>
      <div class="bar-pill bar-orange" style="right:0;top:64px;width:210px">UX/UI Design</div>
      <div class="bar-pill" style="right:0;top:110px;width:155px">Design system</div>
    </div>
  </section>

  <section class="mockups-panel panel">
    <h2 class="mockup-title">07. Mockups</h2>
    <div class="laptop">
      <div class="laptop-screen"><div class="screen-ui"><div class="screen-side"></div><div class="screen-main"><strong>Hi, Oliver!<br>Let's customize your workspace!</strong><div class="screen-hero"></div><div class="screen-cards"><span></span><span></span><span></span></div></div></div></div>
      <div class="laptop-base"></div>
    </div>
    <div class="device-row">
      <div class="phone"><div class="phone-ui"><small>Monthly</small><h4>Hi, Oliver!</h4><div class="phone-card"></div><div class="phone-chart"></div></div></div>
      <div class="watch"><div class="watch-ui"><small>Updates</small><strong>1,892</strong><div class="watch-chart"></div></div></div>
    </div>
    <h2 class="mockup-title" style="margin-top:14px">06. Brand Applications</h2>
    <div class="applications">
      <div><div class="app-icon"><svg viewBox="0 0 120 120"><path d="M60 23 L94 41 L76 51 L60 43 L44 51 L26 41 Z" fill="#fff"/><path d="M26 79 L44 69 L60 77 L76 69 L94 79 L60 98 Z" fill="#fff"/><path d="M21 48 L45 60 L21 72 Z" fill="#fff"/><path d="M99 48 L75 60 L99 72 Z" fill="#fff"/><circle cx="60" cy="60" r="18" fill="#FF5300"/></svg></div><div class="app-label">App Icon</div></div>
      <div><div class="social-avatar"><svg viewBox="0 0 120 120"><path d="M60 23 L94 41 L76 51 L60 43 L44 51 L26 41 Z" fill="#FF5300"/><path d="M26 79 L44 69 L60 77 L76 69 L94 79 L60 98 Z" fill="#FF5300"/><circle cx="60" cy="60" r="18" fill="#1B0B03"/></svg></div><div class="app-label">Social Avatar</div></div>
      <div class="profile-card"><div class="profile-cover"></div><div class="profile-body"><button class="follow">Follow</button><strong>Momentum – Replace all<br>your software</strong><span>@momentum</span><p>60% of work is lost in context — and AI is lost without it.</p><small>582.7K Followers &nbsp; 58 Following</small></div></div>
    </div>
  </section>
</main>
</body>
</html>
```

---

## 7. Estrutura fiel das seções

| Seção | Nome | Conteúdo preservado |
|---:|---|---|
| 01 | Color Palette | 6 cores, nomes e hexadecimais |
| 02 | Typography — Outfit | Nome da fonte, pesos, alfabeto, amostra `Aa` |
| 03 | UI Components | Sidebar, botões, cards, calendário, heatmap, task card |
| 04 | Icons | 10 ícones lineares e caption |
| 05 | Roadmap / Timeline | Fases, datas, barras e destaque laranja |
| 06 | Brand Applications | App icon, social avatar, profile card |
| 07 | Mockups | Laptop, smartphone e smartwatch |
| 08 | Impact / Metrics | 92,400, Hours Saved, +12,7K e gráfico |

---

## 8. Observações de fidelidade

Este arquivo replica a composição visual, hierarquia e conteúdo do painel enviado em formato implementável. Algumas microdiferenças são inevitáveis porque o painel original é uma imagem estática renderizada e o código acima recria a UI em HTML/CSS/SVG editável.

