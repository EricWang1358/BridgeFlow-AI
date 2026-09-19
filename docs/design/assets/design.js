/*
 * 设计稿共用脚本：页面导航、中英切换、深浅切换。
 * Shared script for the design reference: page nav, zh/en switch, light/dark switch.
 *
 * 导航从下面这份清单生成，所以加一页只改一处。
 * The nav is generated from the manifest below, so adding a page is a one-line change.
 */
(function () {
  var PAGES = [
    { id: 'index',        file: 'index.html',            zh: '总览',        en: 'Overview' },
    { id: 'foundations',  file: '00-foundations.html',   zh: '0 基础记号',  en: '0 Foundations' },
    { id: 'portal',       file: '01-portal.html',        zh: '1 登录门户',  en: '1 Login portal' },
    { id: 'shell',        file: '02-shell.html',         zh: '2 外壳',      en: '2 Shell' },
    { id: 'intake',       file: '03-intake.html',        zh: '3 数据进入',  en: '3 Intake' },
    { id: 'batch',        file: '04-batch.html',         zh: '4 批次数据',  en: '4 Batch data' },
    { id: 'dictionary',   file: '05-dictionary.html',    zh: '5 字典与口径', en: '5 Dictionary' },
    { id: 'review',       file: '06-review.html',        zh: '6 研判',      en: '6 Review' },
    { id: 'conclusions',  file: '07-conclusions.html',   zh: '7 结论',      en: '7 Conclusions' },
    { id: 'approvals',    file: '08-approvals.html',     zh: '8 审批',      en: '8 Approvals' },
    { id: 'workflow',     file: '09-workflow.html',      zh: '9 流转',      en: '9 Workflow' },
    { id: 'discovery',    file: '10-discovery.html',     zh: '10 立项发现', en: '10 Discovery' },
    { id: 'quotation',    file: '11-quotation.html',     zh: '11 报价',     en: '11 Quotation' },
    { id: 'states',       file: '12-states.html',        zh: '12 空态与失败', en: '12 States' }
  ];

  var STORE_LANG = 'bridgeflow.design.lang';
  var STORE_MODE = 'bridgeflow.design.mode';
  var lang = 'zh';
  var mode = 'light';
  try {
    lang = localStorage.getItem(STORE_LANG) || 'zh';
    mode = localStorage.getItem(STORE_MODE) || 'light';
  } catch (e) { /* file:// with storage blocked still works, just without memory */ }

  var here = (document.body.getAttribute('data-page') || 'index');
  var index = PAGES.findIndex(function (p) { return p.id === here; });

  function label(p) { return lang === 'zh' ? p.zh : p.en; }

  function buildChrome() {
    var slot = document.getElementById('chrome');
    if (!slot) return;
    var top = document.createElement('div');
    top.className = 'top';
    top.innerHTML =
      '<a class="home" href="index.html"><strong>BridgeFlow AI</strong>' +
      '<span class="i18n" data-zh="界面设计稿 · Claude Design System" data-en="UI design reference · Claude Design System"></span></a>' +
      '<div class="spacer"></div>' +
      '<div class="switch" role="group" aria-label="Language">' +
        '<button type="button" data-set-lang="zh">中文</button>' +
        '<button type="button" data-set-lang="en">EN</button></div>' +
      '<div class="switch" role="group" aria-label="Theme">' +
        '<button type="button" data-set-mode="light"><span class="i18n" data-zh="浅色" data-en="Light"></span></button>' +
        '<button type="button" data-set-mode="dark"><span class="i18n" data-zh="深色" data-en="Dark"></span></button></div>';

    var nav = document.createElement('nav');
    nav.className = 'pagenav';
    nav.setAttribute('aria-label', 'Pages');
    PAGES.forEach(function (p) {
      var a = document.createElement('a');
      a.href = p.file;
      a.dataset.pageLink = p.id;
      if (p.id === here) a.setAttribute('aria-current', 'page');
      nav.appendChild(a);
    });

    slot.replaceWith(top, nav);
  }

  function buildPager() {
    var slot = document.getElementById('pager');
    if (!slot || index < 0) return;
    var prev = PAGES[index - 1];
    var next = PAGES[index + 1];
    slot.className = 'pager';
    slot.innerHTML =
      (prev ? '<a href="' + prev.file + '"><span class="n i18n" data-zh="上一页" data-en="Previous"></span>' +
              '<span data-page-link="' + prev.id + '"></span></a>' : '<span></span>') +
      (next ? '<a href="' + next.file + '" style="text-align:right"><span class="n i18n" data-zh="下一页" data-en="Next"></span>' +
              '<span data-page-link="' + next.id + '"></span></a>' : '<span></span>');
  }

  function applyLang() {
    document.documentElement.lang = lang === 'zh' ? 'zh' : 'en';
    document.querySelectorAll('.i18n').forEach(function (node) {
      var value = node.getAttribute(lang === 'zh' ? 'data-zh' : 'data-en');
      if (value === null) return;
      // A grade mark or badge nested inside a translated label must survive the swap.
      var keep = [];
      node.querySelectorAll('.grade, .badge, .st').forEach(function (k) { keep.push(k) });
      node.textContent = value;
      keep.forEach(function (k) { node.appendChild(document.createTextNode(' ')); node.appendChild(k) });
    });
    document.querySelectorAll('[data-page-link]').forEach(function (node) {
      var p = PAGES.find(function (x) { return x.id === node.dataset.pageLink });
      if (p) node.textContent = label(p);
    });
    document.querySelectorAll('[data-set-lang]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.setLang === lang));
    });
  }

  function applyMode() {
    document.documentElement.setAttribute('data-mode', mode);
    document.querySelectorAll('[data-set-mode]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.setMode === mode));
    });
  }

  function remember(key, value) {
    try { localStorage.setItem(key, value) } catch (e) { /* no memory, no failure */ }
  }

  buildChrome();
  buildPager();
  document.addEventListener('click', function (event) {
    var langBtn = event.target.closest('[data-set-lang]');
    if (langBtn) { lang = langBtn.dataset.setLang; remember(STORE_LANG, lang); applyLang(); return }
    var modeBtn = event.target.closest('[data-set-mode]');
    if (modeBtn) { mode = modeBtn.dataset.setMode; remember(STORE_MODE, mode); applyMode() }
  });
  applyMode();
  applyLang();
})();
