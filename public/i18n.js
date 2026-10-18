// Nic's 5 Nips - site-wide language switcher (English / Español / Khmer).
// Paul, 18 Oct 2026: on every page, top right, with little flags.
//
// How it works: English is the page as written. For another language this
// loads i18n/<lang>.json, a map of English -> translation, and swaps matching
// text in place. Whole paragraphs that only hold inline tags (<b>, <em>, ...)
// are swapped as one unit so word order can change; anything holding an
// element with an id (a live counter, say) is left alone and its plain text
// pieces are swapped one by one instead. A MutationObserver catches text the
// page scripts write later (chat, results, stories). Choosing a language
// saves it and reloads, so every page opens in it.
//
// ?i18n-collect gathers every translatable string on the page into
// window.__i18nKeys instead (used to build the dictionaries).
(() => {
  const LANGS = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'km', name: 'ខ្មែរ' },
  ];
  const KEY = 'nics.lang';
  const FLAGS = {
    en: '<svg viewBox="0 0 60 30" aria-hidden="true"><clipPath id="i18n-uk"><path d="M0 0v30h60V0z"/></clipPath><g clip-path="url(#i18n-uk)"><path d="M0 0v30h60V0z" fill="#012169"/><path d="M0 0l60 30m0-30L0 30" stroke="#fff" stroke-width="6"/><path d="M0 0l60 30m0-30L0 30" stroke="#C8102E" stroke-width="2.4"/><path d="M30 0v30M0 15h60" stroke="#fff" stroke-width="10"/><path d="M30 0v30M0 15h60" stroke="#C8102E" stroke-width="6"/></g></svg>',
    es: '<svg viewBox="0 0 60 30" aria-hidden="true"><path fill="#AA151B" d="M0 0h60v30H0z"/><path fill="#F1BF00" d="M0 7.5h60v15H0z"/></svg>',
    km: '<svg viewBox="0 0 60 30" aria-hidden="true"><path fill="#032EA1" d="M0 0h60v30H0z"/><path fill="#E00025" d="M0 7.5h60v15H0z"/><path fill="#fff" d="M19 20.5h22v1.2H19zM21 19h18v1.5H21zM22.5 15.5h2v3.5h-2zM35.5 15.5h2v3.5h-2zM28.5 13h3v6h-3zM26 15.5h2v3.5h-2zM32 15.5h2v3.5h-2zM29.3 10.2h1.4v2.8h-1.4zM23 14l.5-2 .5 2zM36 14l.5-2 .5 2zM26.5 14.5l.5-1.8.5 1.8zM32.5 14.5l.5-1.8.5 1.8z"/></svg>',
  };

  let lang = 'en';
  try { lang = localStorage.getItem(KEY) || 'en'; } catch (e) {}
  if (!LANGS.some(l => l.code === lang)) lang = 'en';
  const params = new URLSearchParams(location.search);
  const COLLECT = params.has('i18n-collect');
  if (params.get('lang') && LANGS.some(l => l.code === params.get('lang'))) {
    lang = params.get('lang');
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }
  if (COLLECT) lang = 'en';
  document.documentElement.lang = lang;

  // Hide the English for a moment while the dictionary loads, so a Spanish
  // visitor does not see the page flip. Never longer than 1.5s.
  if (lang !== 'en') {
    const veil = document.createElement('style');
    veil.id = 'i18n-veil';
    veil.textContent = 'body{opacity:0!important}';
    document.head.appendChild(veil);
    setTimeout(() => veil.remove(), 1500);
  }

  const css = document.createElement('style');
  css.textContent = `
.i18n-bar{display:flex;gap:4px;align-items:center;background:rgba(10,10,10,.9);border:1px solid rgba(201,168,76,.45);border-radius:999px;padding:4px;z-index:1000;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 4px 18px rgba(0,0,0,.45)}
.i18n-bar.i18n-float{position:fixed;top:10px;right:10px}
.i18n-bar button{display:flex;align-items:center;gap:5px;background:none;border:0;border-radius:999px;padding:4px 8px;cursor:pointer;color:rgba(255,255,255,.75);font:600 11px/1 inherit;letter-spacing:.5px}
.i18n-bar button svg{width:22px;height:11px;border-radius:2px;box-shadow:0 0 0 1px rgba(255,255,255,.25);flex:none}
.i18n-bar button:hover{color:#fff;background:rgba(201,168,76,.15)}
.i18n-bar button.on{background:#c9a84c;color:#111}
.i18n-bar button.on svg{box-shadow:0 0 0 1px rgba(0,0,0,.35)}
@media(max-width:600px){.i18n-bar button .i18n-name{display:none}.i18n-bar button{padding:5px 7px}}`;
  document.head.appendChild(css);

  function buildBar() {
    const bar = document.createElement('div');
    bar.className = 'i18n-bar';
    bar.setAttribute('data-noi18n', '');
    bar.setAttribute('role', 'group');
    bar.setAttribute('aria-label', 'Language');
    LANGS.forEach(l => {
      const b = document.createElement('button');
      b.type = 'button';
      b.title = l.name;
      b.className = l.code === lang ? 'on' : '';
      b.innerHTML = FLAGS[l.code] + '<span class="i18n-name">' + l.name + '</span>';
      b.addEventListener('click', () => {
        if (l.code === lang) return;
        try { localStorage.setItem(KEY, l.code); } catch (e) {}
        const u = new URL(location.href);
        u.searchParams.delete('lang');
        location.replace(u.toString());
      });
      bar.appendChild(b);
    });
    // A page can say where the flags go; otherwise the right end of the top
    // nav bar; otherwise pinned to the top right corner.
    const slot = document.querySelector('[data-i18n-slot]');
    const nav = document.querySelector('body > nav');
    if (slot) slot.appendChild(bar);
    else if (nav) { bar.style.marginLeft = '12px'; nav.appendChild(bar); }
    else { bar.classList.add('i18n-float'); document.body.appendChild(bar); }
  }

  // ---------- finding text ----------
  const INLINE = new Set(['B', 'I', 'EM', 'STRONG', 'SPAN', 'BR', 'A', 'SMALL', 'SUP', 'SUB', 'U', 'MARK', 'ABBR', 'S', 'DEL', 'INS', 'CODE', 'FONT', 'BLINK', 'BIG']);
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'CANVAS', 'TEXTAREA', 'INPUT', 'SELECT', 'OPTION', 'IFRAME', 'TEMPLATE']);
  const ATTRS = ['placeholder', 'title', 'alt', 'aria-label'];
  const norm = s => s.replace(/\s+/g, ' ').trim();
  const hasWords = s => /\p{L}{2,}/u.test(s);

  function isUnit(el) {
    // Only inline tags inside, no ids underneath, some real words.
    if (!el.firstChild || SKIP.has(el.tagName)) return false;
    if (!el.children.length) return false;
    for (const d of el.querySelectorAll('*')) {
      if (!INLINE.has(d.tagName) || d.id || d.hasAttribute('data-noi18n')) return false;
    }
    return hasWords(el.textContent);
  }

  function walk(root, onUnit, onText, onAttr) {
    if (root.nodeType === 3) { onText(root); return; }
    if (root.nodeType !== 1) return;
    if (SKIP.has(root.tagName) || root.hasAttribute('data-noi18n')) return;
    for (const a of ATTRS) if (root.hasAttribute(a)) onAttr(root, a);
    if (isUnit(root)) { onUnit(root); return; }
    for (const c of Array.from(root.childNodes)) walk(c, onUnit, onText, onAttr);
  }

  // ---------- collect mode ----------
  if (COLLECT) {
    const keys = new Set();
    const grab = root => walk(root,
      el => keys.add(norm(el.innerHTML)),
      t => { const k = norm(t.nodeValue); if (hasWords(k)) keys.add(k); },
      (el, a) => { const k = norm(el.getAttribute(a)); if (hasWords(k)) keys.add(k); });
    window.__i18nKeys = keys;
    const go = () => {
      buildBar();
      if (hasWords(document.title)) keys.add(norm(document.title));
      grab(document.body);
      new MutationObserver(ms => ms.forEach(m => {
        if (m.type === 'characterData') grab(m.target.parentNode || m.target);
        m.addedNodes.forEach(grab);
        if (m.type === 'childList' && m.target.nodeType === 1) grab(m.target);
      })).observe(document.body, { childList: true, subtree: true, characterData: true });
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
    return;
  }

  // ---------- translate mode ----------
  let dict = null;
  const done = new WeakMap(); // node -> the value we last wrote, so we never loop

  function tr(k) { return dict && Object.prototype.hasOwnProperty.call(dict, k) ? dict[k] : null; }

  function apply(root) {
    if (!dict) return;
    walk(root,
      el => {
        const cur = norm(el.innerHTML);
        if (done.get(el) === cur) return;
        const t = tr(cur);
        if (t != null) { el.innerHTML = t; done.set(el, norm(el.innerHTML)); }
        else for (const c of Array.from(el.childNodes)) if (c.nodeType === 3) textNode(c);
      },
      textNode,
      (el, a) => { const t = tr(norm(el.getAttribute(a))); if (t != null) el.setAttribute(a, t); });
  }

  function textNode(n) {
    const raw = n.nodeValue;
    const k = norm(raw);
    if (!k || done.get(n) === raw) return;
    const t = tr(k);
    if (t == null) return;
    const lead = raw.match(/^\s*/)[0], tail = raw.match(/\s*$/)[0];
    n.nodeValue = lead + t + tail;
    done.set(n, n.nodeValue);
  }

  // Lets page scripts translate strings they build themselves.
  window.i18n = { lang, t: s => (lang === 'en' ? s : (tr(norm(s)) ?? s)) };

  function start() {
    buildBar();
    if (lang === 'en') return;
    fetch('i18n/' + lang + '.json', { cache: 'no-cache' })
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(d => {
        dict = d;
        const tt = tr(norm(document.title)); if (tt) document.title = tt;
        apply(document.body);
        // Pages that built text before the dictionary arrived can rebuild it now.
        window.dispatchEvent(new Event('i18n-ready'));
        let queued = new Set();
        new MutationObserver(ms => {
          ms.forEach(m => {
            if (m.type === 'characterData') queued.add(m.target);
            else { queued.add(m.target); m.addedNodes.forEach(n => queued.add(n)); }
          });
          requestAnimationFrame(() => {
            const q = queued; queued = new Set();
            q.forEach(n => { if (n.isConnected) apply(n.nodeType === 3 ? n : n); });
          });
        }).observe(document.body, { childList: true, subtree: true, characterData: true });
      })
      .catch(e => console.error('[i18n] could not load ' + lang + ' dictionary', e))
      .finally(() => { const v = document.getElementById('i18n-veil'); if (v) v.remove(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
