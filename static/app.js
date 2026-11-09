/* Интерактив сайта: тема, меню, анимации, уведомления, каталог, вход, матрица.
   Без зависимостей. Всё, что требует DOM-элементов, безопасно пропускается, если их нет. */
(function () {
    'use strict';

    window.__appReady = true;
    var doc = document;
    var root = doc.documentElement;
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
    function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }
    function store(key, value) {
        try {
            if (value === undefined) return localStorage.getItem(key);
            localStorage.setItem(key, value);
        } catch (e) { /* приватный режим */ }
        return null;
    }

    /* ---------- Тема ---------- */
    var themeBtn = $('#theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', function () {
            var next = root.dataset.theme === 'light' ? 'dark' : 'light';
            root.dataset.theme = next;
            store('theme', next);
            var meta = $('meta[name="theme-color"]');
            if (meta) meta.setAttribute('content', next === 'light' ? '#faf7f2' : '#0a0a0a');
        });
    }

    /* ---------- Мобильное меню ---------- */
    var navToggle = $('#nav-toggle');
    var navPanel = $('#nav-panel');
    function setNav(open) {
        if (!navToggle || !navPanel) return;
        navPanel.classList.toggle('is-open', open);
        navToggle.setAttribute('aria-expanded', String(open));
        navToggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    }
    if (navToggle && navPanel) {
        navToggle.addEventListener('click', function () {
            setNav(!navPanel.classList.contains('is-open'));
        });
        navPanel.addEventListener('click', function (e) {
            if (e.target.closest('a')) setNav(false);
        });
        doc.addEventListener('keydown', function (e) { if (e.key === 'Escape') setNav(false); });
        doc.addEventListener('click', function (e) {
            if (!e.target.closest('.navigation')) setNav(false);
        });
    }

    /* ---------- Шапка и кнопка «Наверх» ---------- */
    var header = $('#site-header');
    var toTop = $('#to-top');
    function onScroll() {
        var y = window.scrollY || root.scrollTop;
        if (header) header.classList.toggle('is-scrolled', y > 8);
        if (toTop) toTop.hidden = y < 600;
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    if (toTop) {
        toTop.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
        });
    }

    /* ---------- Появление блоков при прокрутке ---------- */
    var reveals = $$('.reveal');
    if ('IntersectionObserver' in window && !reduceMotion) {
        var revealObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
        reveals.forEach(function (el, i) {
            // лёгкая «лесенка» для соседних карточек
            el.style.transitionDelay = Math.min(i % 4, 3) * 70 + 'ms';
            revealObserver.observe(el);
        });
    } else {
        reveals.forEach(function (el) { el.classList.add('is-visible'); });
    }

    /* ---------- Счётчики ---------- */
    function animateCount(el) {
        var target = parseInt(el.getAttribute('data-count'), 10);
        if (isNaN(target) || reduceMotion || target === 0) return;
        var duration = 1100;
        var start = null;
        function step(ts) {
            if (start === null) start = ts;
            var p = Math.min((ts - start) / duration, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(target * eased).toLocaleString('ru-RU');
            if (p < 1) requestAnimationFrame(step);
        }
        el.textContent = '0';
        requestAnimationFrame(step);
    }
    var counters = $$('[data-count]');
    if ('IntersectionObserver' in window) {
        var countObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCount(entry.target);
                    countObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.6 });
        counters.forEach(function (el) { countObserver.observe(el); });
    }

    /* ---------- Уведомления ---------- */
    $$('.toast').forEach(function (toast) {
        var timer;
        function close() {
            toast.classList.add('is-leaving');
            setTimeout(function () { toast.remove(); }, 320);
        }
        function arm() {
            clearTimeout(timer);
            timer = setTimeout(close, toast.classList.contains('toast--error') ? 9000 : 5500);
        }
        arm();
        toast.addEventListener('mouseenter', function () { clearTimeout(timer); });
        toast.addEventListener('mouseleave', arm);
        var btn = $('.toast__close', toast);
        if (btn) btn.addEventListener('click', close);
    });

    /* ---------- Подтверждения и защита от двойной отправки ---------- */
    doc.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-confirm]');
        if (btn && !window.confirm(btn.getAttribute('data-confirm'))) {
            e.preventDefault();
            e.stopPropagation();
        }
    }, true);

    doc.addEventListener('submit', function (e) {
        var form = e.target;
        if (e.defaultPrevented || !form.matches('form')) return;
        var buttons = $$('button[type="submit"]', form);
        setTimeout(function () { buttons.forEach(function (b) { b.disabled = true; }); }, 0);
    });
    window.addEventListener('pageshow', function () {
        $$('button[type="submit"]:disabled').forEach(function (b) { b.disabled = false; });
    });

    /* ---------- Показ пароля ---------- */
    $$('[data-toggle-password]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var input = doc.getElementById(btn.getAttribute('data-toggle-password'));
            if (!input) return;
            var show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            btn.setAttribute('aria-label', show ? 'Скрыть пароль' : 'Показать пароль');
        });
    });

    /* ---------- Вкладки «Вход / Регистрация» ---------- */
    var tabs = $('#auth-tabs');
    if (tabs) {
        var panels = $$('[data-panel]');
        var titles = $$('[data-title]');
        var tabButtons = $$('[data-tab]', tabs);
        var activate = function (name) {
            tabButtons.forEach(function (b) {
                var on = b.getAttribute('data-tab') === name;
                b.classList.toggle('is-active', on);
                b.setAttribute('aria-selected', String(on));
            });
            panels.forEach(function (p) { p.hidden = p.getAttribute('data-panel') !== name; });
            titles.forEach(function (t) { t.hidden = t.getAttribute('data-title') !== name; });
            var first = $('[data-panel="' + name + '"] input[type="text"]');
            if (first && doc.activeElement === doc.body) first.focus();
        };
        tabButtons.forEach(function (b) {
            b.addEventListener('click', function () { activate(b.getAttribute('data-tab')); });
        });
        activate(tabs.getAttribute('data-initial') === 'register' ? 'register' : 'login');
    }

    var regPass = $('#reg-password');
    var strength = $('#strength');
    var strengthLabel = $('#strength-label');
    if (regPass && strength) {
        var labels = ['Минимум 6 символов.', 'Слабый пароль', 'Средний пароль', 'Хороший пароль', 'Отличный пароль'];
        regPass.addEventListener('input', function () {
            var v = regPass.value;
            var score = 0;
            if (v.length >= 6) score++;
            if (v.length >= 10) score++;
            if (/[a-zа-я]/.test(v) && /[A-ZА-Я]/.test(v)) score++;
            if (/\d/.test(v) && /[^\w\s]/.test(v)) score++;
            if (!v) score = 0;
            strength.setAttribute('data-level', String(score));
            if (strengthLabel) strengthLabel.textContent = labels[score];
        });
    }

    /* ---------- Диалоги ---------- */
    $$('[data-open-dialog]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var dlg = doc.getElementById(btn.getAttribute('data-open-dialog'));
            if (dlg && typeof dlg.showModal === 'function') dlg.showModal();
        });
    });
    $$('dialog').forEach(function (dlg) {
        dlg.addEventListener('click', function (e) {
            if (e.target.closest('[data-close-dialog]')) { dlg.close(); return; }
            if (e.target === dlg) {
                var r = dlg.getBoundingClientRect();
                var outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
                if (outside) dlg.close();
            }
        });
    });

    /* ---------- Каталог ---------- */
    var results = $('#catalog-results');
    var viewToggle = $('#view-toggle');
    if (results && viewToggle) {
        var setView = function (view) {
            results.setAttribute('data-view', view);
            $$('button', viewToggle).forEach(function (b) {
                b.classList.toggle('is-active', b.getAttribute('data-view') === view);
            });
        };
        setView(store('catalog-view') === 'table' ? 'table' : 'grid');
        viewToggle.addEventListener('click', function (e) {
            var b = e.target.closest('button[data-view]');
            if (!b) return;
            setView(b.getAttribute('data-view'));
            store('catalog-view', b.getAttribute('data-view'));
        });
    }

    $$('[data-autosubmit]').forEach(function (el) {
        el.addEventListener('change', function () {
            if (el.form) el.form.requestSubmit ? el.form.requestSubmit() : el.form.submit();
        });
    });

    // Живые подсказки поиска
    var searchInput = $('#q');
    var suggestList = $('#suggest-list');
    if (searchInput && suggestList && 'fetch' in window) {
        var suggestUrl = searchInput.getAttribute('data-suggest-url');
        var debounce, controller, activeIndex = -1;

        var closeSuggest = function () {
            suggestList.hidden = true;
            suggestList.textContent = '';
            activeIndex = -1;
        };
        var render = function (items) {
            suggestList.textContent = '';
            if (!items.length) { closeSuggest(); return; }
            items.forEach(function (item) {
                var li = doc.createElement('li');
                var a = doc.createElement('a');
                a.href = item.url;
                var name = doc.createElement('span');
                name.className = 'suggest__name';
                name.textContent = item.name;
                var meta = doc.createElement('span');
                meta.className = 'suggest__meta';
                meta.textContent = (item.category ? item.category + ' · ' : '') + item.price;
                a.appendChild(name);
                a.appendChild(meta);
                li.appendChild(a);
                suggestList.appendChild(li);
            });
            suggestList.hidden = false;
            activeIndex = -1;
        };

        if (suggestUrl) {
            searchInput.addEventListener('input', function () {
                clearTimeout(debounce);
                var q = searchInput.value.trim();
                if (q.length < 2) { closeSuggest(); return; }
                debounce = setTimeout(function () {
                    if (controller) controller.abort();
                    controller = window.AbortController ? new AbortController() : null;
                    fetch(suggestUrl + '?q=' + encodeURIComponent(q), controller ? { signal: controller.signal } : {})
                        .then(function (r) { return r.ok ? r.json() : []; })
                        .then(render)
                        .catch(function () { /* отмена или сеть — молча */ });
                }, 220);
            });
        }

        searchInput.addEventListener('keydown', function (e) {
            var links = $$('a', suggestList);
            if (e.key === 'Escape') { closeSuggest(); return; }
            if (!links.length || suggestList.hidden) return;
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = (activeIndex + (e.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
                links[activeIndex].focus();
            }
        });
        suggestList.addEventListener('keydown', function (e) {
            var links = $$('a', suggestList);
            var i = links.indexOf(doc.activeElement);
            if (e.key === 'ArrowDown') { e.preventDefault(); links[(i + 1) % links.length].focus(); }
            if (e.key === 'ArrowUp') { e.preventDefault(); (i <= 0 ? searchInput : links[i - 1]).focus(); }
            if (e.key === 'Escape') { closeSuggest(); searchInput.focus(); }
        });
        doc.addEventListener('click', function (e) {
            if (!e.target.closest('.field--search')) closeSuggest();
        });
    }

    /* ---------- Отзывы: счётчик символов ---------- */
    var reviewText = $('#review-text');
    var reviewCounter = $('#review-counter');
    if (reviewText && reviewCounter) {
        reviewText.addEventListener('input', function () {
            reviewCounter.textContent = String(reviewText.value.length);
        });
    }

    /* ---------- Матрица ---------- */
    var canvas = $('#matrix-canvas');
    if (canvas && canvas.getContext) {
        var ctx = canvas.getContext('2d');
        var chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF<>/=+*';
        var fontSize = 18;
        var drops = [];
        var speed = 1;
        var paused = false;
        var last = 0;
        var frameMs = 55;

        var resize = function () {
            var ratio = window.devicePixelRatio || 1;
            var w = canvas.clientWidth;
            var h = canvas.clientHeight;
            canvas.width = w * ratio;
            canvas.height = h * ratio;
            ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
            ctx.fillStyle = '#000';
            ctx.fillRect(0, 0, w, h);
            var cols = Math.ceil(w / fontSize);
            drops = [];
            for (var i = 0; i < cols; i++) drops.push(Math.floor(Math.random() * -h / fontSize));
        };

        var draw = function () {
            var w = canvas.clientWidth;
            var h = canvas.clientHeight;
            ctx.fillStyle = 'rgba(0, 0, 0, 0.09)';
            ctx.fillRect(0, 0, w, h);
            ctx.font = fontSize + 'px monospace';
            for (var i = 0; i < drops.length; i++) {
                var ch = chars.charAt(Math.floor(Math.random() * chars.length));
                var x = i * fontSize;
                var y = drops[i] * fontSize;
                ctx.fillStyle = Math.random() > 0.975 ? '#d6ffe0' : '#00ff41';
                ctx.fillText(ch, x, y);
                if (y > h && Math.random() > 0.975) drops[i] = 0;
                drops[i] += 1;
            }
        };

        var loop = function (ts) {
            if (!paused && ts - last > frameMs / speed) { draw(); last = ts; }
            requestAnimationFrame(loop);
        };

        resize();
        window.addEventListener('resize', resize);
        if (reduceMotion) {
            for (var f = 0; f < 90; f++) draw();   // статичная картинка
        } else {
            requestAnimationFrame(loop);
        }

        var speedBtn = $('#matrix-speed');
        var pauseBtn = $('#matrix-pause');
        if (speedBtn) {
            var speeds = [1, 2, 4, 0.5];
            var si = 0;
            speedBtn.addEventListener('click', function () {
                si = (si + 1) % speeds.length;
                speed = speeds[si];
                speedBtn.textContent = 'Скорость: ×' + speed;
            });
        }
        if (pauseBtn) {
            pauseBtn.addEventListener('click', function () {
                paused = !paused;
                pauseBtn.textContent = paused ? 'Продолжить' : 'Пауза';
            });
        }
    }

    // Печатающийся текст
    var typed = $('#matrix-typed');
    if (typed) {
        var lines = [];
        try { lines = JSON.parse(typed.getAttribute('data-lines') || '[]'); } catch (e) { lines = []; }
        if (lines.length) {
            if (reduceMotion) {
                typed.textContent = lines[0];
            } else {
                var li = 0, ci = 0, deleting = false;
                var tick = function () {
                    var line = lines[li];
                    if (!deleting) {
                        ci++;
                        typed.textContent = line.slice(0, ci);
                        if (ci === line.length) { deleting = true; return setTimeout(tick, 1800); }
                        return setTimeout(tick, 65);
                    }
                    ci--;
                    typed.textContent = line.slice(0, ci);
                    if (ci === 0) { deleting = false; li = (li + 1) % lines.length; return setTimeout(tick, 400); }
                    return setTimeout(tick, 28);
                };
                tick();
            }
        }
    }
})();
