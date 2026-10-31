/* ALBEDIA · scripts du site : menu, sous-menus, simulateur d'albédo, formulaire de devis */
(function () {
  'use strict';

  /* ---------- menu principal (mobile) */
  var header = document.querySelector('.site-header');
  var menuBtn = document.querySelector('.menu-btn');
  function setMenu(open) {
    if (!header || !menuBtn) return;
    header.classList.toggle('nav-open', open);
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      setMenu(!header.classList.contains('nav-open'));
    });
  }

  /* ---------- sous-menus */
  var subs = Array.prototype.slice.call(document.querySelectorAll('.has-sub'));
  function closeSub(li) {
    li.classList.remove('open');
    var b = li.querySelector('.nav-toggle-sub');
    if (b) b.setAttribute('aria-expanded', 'false');
  }
  subs.forEach(function (li) {
    var btn = li.querySelector('.nav-toggle-sub');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var willOpen = !li.classList.contains('open');
      subs.forEach(closeSub);
      if (willOpen) {
        li.classList.add('open');
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest || !e.target.closest('.has-sub')) subs.forEach(closeSub);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var openSub = subs.filter(function (li) { return li.classList.contains('open'); })[0];
    if (openSub) {
      closeSub(openSub);
      var b = openSub.querySelector('.nav-toggle-sub');
      if (b) b.focus();
    } else if (header && header.classList.contains('nav-open')) {
      setMenu(false);
      menuBtn.focus();
    }
  });

  /* ---------- simulateur d'albédo (guide du cool roof) */
  var range = document.getElementById('albedo-range');
  if (range) {
    var out = document.getElementById('albedo-value');
    var refTxt = document.getElementById('albedo-ref');
    var absTxt = document.getElementById('albedo-abs');
    var barRef = document.getElementById('albedo-bar-ref');
    var barAbs = document.getElementById('albedo-bar-abs');
    var msg = document.getElementById('albedo-msg');
    var update = function () {
      var a = parseFloat(range.value);
      var r = Math.round(a * 100);
      out.textContent = a.toFixed(2).replace('.', ',');
      refTxt.textContent = r + ' %';
      absTxt.textContent = (100 - r) + ' %';
      barRef.style.width = r + '%';
      barAbs.style.width = (100 - r) + '%';
      var t;
      if (a <= 0.15) t = 'C’est l’ordre de grandeur d’une toiture traditionnelle sombre, qui renvoie 5 à 15 % du rayonnement (US EPA).';
      else if (a < 0.3) t = 'Comparable à une toiture grise, qui renvoie environ 20 % du rayonnement (Lawrence Berkeley National Laboratory).';
      else if (a < 0.65) t = 'Zone des toitures claires et des teintes « cool » colorées : une toiture qui renvoie 35 % du soleil reste environ 12 °C plus fraîche qu’une toiture sombre du même aspect (LBNL).';
      else if (a < 0.8) t = 'Niveau des matériaux cool roof, qui renvoient plus de 65 % du rayonnement (US EPA).';
      else t = 'Niveau d’une toiture blanche propre, qui renvoie environ 80 % du rayonnement et reste environ 31 °C plus fraîche qu’une toiture grise (LBNL).';
      msg.textContent = t;
    };
    range.addEventListener('input', update);
    update();
  }

  /* ---------- formulaire de devis */
  var form = document.getElementById('devis-form');
  if (form) {
    var started = Date.now();
    var status = document.getElementById('form-status');
    var submitBtn = form.querySelector('button[type="submit"]');
    var submitHtml = submitBtn ? submitBtn.innerHTML : '';

    // pré-remplissage depuis le formulaire rapide de l'accueil
    try {
      var q = new URLSearchParams(window.location.search);
      ['secteur', 'surface', 'code_postal', 'email'].forEach(function (k) {
        var v = q.get(k);
        var el = form.elements[k];
        if (v && el) el.value = v;
      });
    } catch (err) { /* navigateur ancien : pas de pré-remplissage */ }

    var show = function (kind, text) {
      status.className = 'form-status ' + kind;
      status.textContent = text;
      status.hidden = false;
      status.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    };

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (form.elements.elapsed) form.elements.elapsed.value = String(Date.now() - started);
      if (form.getAttribute('data-preview')) {
        show('info', 'Aperçu du site : l’envoi du formulaire sera actif une fois le site en ligne sur albedia.eu.');
        return;
      }
      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Envoi en cours…'; }
      fetch(form.getAttribute('action'), {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      })
        .then(function (res) {
          return res.json().catch(function () { return { ok: false }; });
        })
        .then(function (data) {
          if (data && data.ok) {
            form.reset();
            started = Date.now();
            show('ok', 'Merci, votre demande est bien partie. Nous revenons vers vous rapidement.');
          } else {
            show('err', (data && data.error) || 'L’envoi n’a pas abouti. Réessayez ou écrivez-nous directement à contact@albedia.eu.');
          }
        })
        .catch(function () {
          show('err', 'L’envoi n’a pas abouti. Vérifiez votre connexion ou écrivez-nous directement à contact@albedia.eu.');
        })
        .then(function () {
          if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = submitHtml; }
        });
    });
  }
})();
