(() => {
  'use strict';
  const theme = document.querySelector('#theme');
  const media = matchMedia('(prefers-color-scheme:dark)');
  const root = document.documentElement;
  let preference = root.dataset.themePreference || 'system';
  const applyTheme = () => {
    root.dataset.themePreference = preference;
    root.dataset.theme = preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
    theme.value = preference;
  };
  theme.addEventListener('change', () => {
    preference = theme.value;
    try { localStorage.setItem('paperreading-theme', preference); } catch {}
    applyTheme();
  });
  media.addEventListener('change', () => { if (preference === 'system') applyTheme(); });
  window.addEventListener('storage', event => {
    if (event.key === 'paperreading-theme') {
      preference = ['light', 'dark', 'system'].includes(event.newValue) ? event.newValue : 'system';
      applyTheme();
    }
  });
  applyTheme();

  const search = document.querySelector('#paper-search');
  const links = [...document.querySelectorAll('.quick-index a')];
  const status = document.querySelector('#search-status');
  search.addEventListener('input', () => {
    const q = search.value.trim().toLocaleLowerCase();
    let count = 0;
    links.forEach(a => {
      const match = (a.dataset.name + ' ' + a.textContent + ' ' + a.hash).toLocaleLowerCase().includes(q);
      a.hidden = !match;
      if (match) count++;
    });
    status.textContent = count ? `${count} 篇匹配论文` : '没有匹配论文，请试试英文简称或路线名称。';
  });

  const mapButton = document.querySelector('#map-toggle');
  const map = document.querySelector('#map-frame');
  mapButton.addEventListener('click', () => {
    const expanded = map.classList.toggle('expanded');
    mapButton.setAttribute('aria-expanded', String(expanded));
    mapButton.textContent = expanded ? '收起路线图' : '展开路线图';
  });

  const dialog = document.querySelector('#figure-dialog');
  const art = document.querySelector('#dialog-art');
  const caption = document.querySelector('#dialog-caption');
  let trigger = null;
  document.querySelectorAll('.zoom').forEach(button => button.addEventListener('click', () => {
    trigger = button;
    const fig = button.closest('figure');
    art.replaceChildren(...[...fig.querySelectorAll('img')].map(im => {
      const clone = im.cloneNode(true); clone.loading = 'eager'; return clone;
    }));
    caption.textContent = fig.querySelector('figcaption').textContent;
    dialog.showModal();
    document.querySelector('#close-dialog').focus();
  }));
  document.querySelector('#close-dialog').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => trigger?.focus());

  const nav = document.querySelector('.main-nav');
  const navLinks = [...nav.querySelectorAll('a')];
  const sections = navLinks.map(a => document.querySelector(a.hash));
  const updateCurrent = () => {
    let current = null;
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= nav.offsetHeight + 40) current = section.id;
    }
    navLinks.forEach(a => {
      if (a.hash === '#' + current) a.setAttribute('aria-current', 'location');
      else a.removeAttribute('aria-current');
    });
  };
  new ResizeObserver(() => {
    root.style.setProperty('--nav-height', `${nav.offsetHeight}px`);
    updateCurrent();
  }).observe(nav);
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { updateCurrent(); ticking = false; });
  }, {passive: true});

  // Old overview, section, classic, figure, and embedded-reading links stay usable.
  const aliases = {
    overview: 'map', fewstep: 'flowmaps', solvers: 'sampling', caching: 'sampling',
    spatial: 'adaptive', compression: 'representation', deployment: 'systems',
    'complete-reading': 'further-reading', 'expanded-reading': 'content',
    'expanded-reading-frame': 'content', 'map-zoom': 'map-toggle',
    edition: 'top', primer: 'background', lineage: 'map', selection: 'practice',
    accounting: 'background', atlas: 'map', cost: 'background', timeline: 'map',
    'theme-select': 'theme'
  };
  for (const classic of document.querySelectorAll('.classic[id]')) {
    aliases[classic.id.replace('classic-', 'paper-')] = classic.id;
  }
  for (const [oldId, newId] of Object.entries(aliases)) {
    if (document.getElementById(oldId)) continue;
    const anchor = document.createElement('span');
    anchor.id = oldId; anchor.className = 'legacy-anchor'; anchor.setAttribute('aria-hidden', 'true');
    document.getElementById(newId).before(anchor);
  }
  const routeHash = () => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    if (!id) return;
    const original = id;
    if (id.startsWith('expanded-reading--')) id = id.slice(18);
    if (aliases[id]) id = aliases[id];
    const tree = id.match(/^tree-(fewstep|solvers|caching|spatial|compression|deployment)-/);
    if (tree) id = aliases[tree[1]];
    const figure = id.match(/^paper-figure:(p[\d-]+):/);
    if (figure) id = aliases['paper-' + figure[1]] || 'paper-' + figure[1];
    const newFigure = id.match(/^newfig-(\d{4})-(\d{4,5})$/);
    if (newFigure) id = 'paper-p' + newFigure[1] + '-' + newFigure[2];
    const target = document.getElementById(id);
    if (target) {
      let parent = target.parentElement;
      while (parent) { if (parent.tagName === 'DETAILS') parent.open = true; parent = parent.parentElement; }
      requestAnimationFrame(() => target.scrollIntoView({block: 'start', behavior: 'instant'}));
      if (id !== original) history.replaceState(null, '', location.pathname + location.search + '#' + id);
      updateCurrent();
      return;
    }
    if (legacyIds.has(id) || id.startsWith('material-')) {
      location.replace('image-acceleration-summary-20261105.html' + location.search + '#' + original);
    }
  };
  // Populated from the prior page's exact mainIds/auxIds manifest.
  const legacyIds = new Set(["caching", "complete-reading", "compression", "deployment", "fewstep", "map-frame", "map-zoom", "overview", "paper-figure:p2501-15420:1-art", "paper-figure:p2501-15420:1-title", "paper-figure:p2607-02461:1-art", "paper-figure:p2607-02461:1-title", "paper-p2411-01738", "paper-p2501-15420", "paper-p2508-17356", "paper-p2602-16968", "paper-p2606-03746", "paper-p2607-02461", "paper-p2610-03577", "solvers", "spatial", "top", "tree-caching-caption", "tree-caching-narrow-desc", "tree-caching-narrow-title", "tree-caching-wide-desc", "tree-caching-wide-title", "tree-compression-caption", "tree-compression-narrow-desc", "tree-compression-narrow-title", "tree-compression-wide-desc", "tree-compression-wide-title", "tree-deployment-caption", "tree-deployment-narrow-desc", "tree-deployment-narrow-title", "tree-deployment-wide-desc", "tree-deployment-wide-title", "tree-fewstep-caption", "tree-fewstep-narrow-desc", "tree-fewstep-narrow-title", "tree-fewstep-wide-desc", "tree-fewstep-wide-title", "tree-solvers-caption", "tree-solvers-narrow-desc", "tree-solvers-narrow-title", "tree-solvers-wide-desc", "tree-solvers-wide-title", "tree-spatial-caption", "tree-spatial-narrow-desc", "tree-spatial-narrow-title", "tree-spatial-wide-desc", "tree-spatial-wide-title", "accounting", "atlas", "background", "benchmark", "caching", "catalog", "catalog-count", "catalog-search", "catalog-status", "compression", "cost", "deployment", "edition", "fewstep", "lineage", "local-materials", "new-audit", "newfig-2311-05556", "newfig-2404-14507", "newfig-2410-10733", "newfig-2505-21136", "newfig-2506-14603", "newfig-2506-16054", "newfig-2511-20549", "newfig-2512-02899", "newfig-2512-05150", "newfig-2602-03139", "newfig-2602-16968", "newfig-2607-26004", "open-questions", "overview", "paper-figure:p2402-19481:1-art", "paper-figure:p2402-19481:1-title", "paper-figure:p2404-13686:1-art", "paper-figure:p2404-13686:1-title", "paper-figure:p2410-10629:1-art", "paper-figure:p2410-10629:1-title", "paper-figure:p2411-05007:1-art", "paper-figure:p2411-05007:1-title", "paper-figure:p2501-15420:1-art", "paper-figure:p2501-15420:1-title", "paper-figure:p2502-08690:1-art", "paper-figure:p2502-08690:1-title", "paper-figure:p2509-25180:1-art", "paper-figure:p2509-25180:1-title", "paper-figure:p2510-27684:1-art", "paper-figure:p2510-27684:1-title", "paper-figure:p2511-22677:1-art", "paper-figure:p2511-22677:1-title", "paper-figure:p2605-06376:1-art", "paper-figure:p2605-06376:1-title", "paper-figure:p2605-23902:1-art", "paper-figure:p2605-23902:1-title", "paper-figure:p2607-02461:1-art", "paper-figure:p2607-02461:1-title", "paper-figure:p2607-19064:1-art", "paper-figure:p2607-19064:1-title", "paper-p2010-02502", "paper-p2202-00512", "paper-p2205-14135", "paper-p2206-00364", "paper-p2206-00927", "paper-p2211-01095", "paper-p2302-04304", "paper-p2302-04867", "paper-p2303-01469", "paper-p2303-17604", "paper-p2309-06380", "paper-p2310-04378", "paper-p2310-14189", "paper-p2311-05556", "paper-p2311-17042", "paper-p2311-18828", "paper-p2312-00858", "paper-p2402-13929", "paper-p2402-19481", "paper-p2403-12015", "paper-p2404-02747", "paper-p2404-13686", "paper-p2404-14507", "paper-p2405-07510", "paper-p2405-14430", "paper-p2405-14867", "paper-p2406-02540", "paper-p2406-06911", "paper-p2406-08552", "paper-p2407-01425", "paper-p2410-10629", "paper-p2410-10733", "paper-p2411-01738", "paper-p2411-05007", "paper-p2412-18653", "paper-p2501-15420", "paper-p2502-08690", "paper-p2502-10389", "paper-p2502-20126", "paper-p2503-06923", "paper-p2503-07703", "paper-p2503-09641", "paper-p2504-11346", "paper-p2505-13447", "paper-p2505-21136", "paper-p2506-05083", "paper-p2506-14603", "paper-p2506-16054", "paper-p2508-17356", "paper-p2509-20427", "paper-p2509-23951", "paper-p2509-24006", "paper-p2509-25180", "paper-p2510-27684", "paper-p2511-20549", "paper-p2511-22677", "paper-p2511-22699", "paper-p2512-02899", "paper-p2512-05150", "paper-p2602-03139", "paper-p2602-16968", "paper-p2603-05105", "paper-p2603-24800", "paper-p2604-18168", "paper-p2605-06376", "paper-p2605-10730", "paper-p2605-23902", "paper-p2606-03746", "paper-p2607-02461", "paper-p2607-19064", "paper-p2607-26004", "paper-p2610-03577", "primer", "research-audit", "selection", "sensenova", "solvers", "spatial", "theme-select", "timeline", "tm-supplement-script", "tm-supplement-style", "top"]);
  window.addEventListener('hashchange', routeHash);
  window.addEventListener('load', routeHash, {once: true});
  routeHash();
})();
