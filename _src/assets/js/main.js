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

  /* ---------- simulateur d'économies et de prime CEE (accueil)
     Hypothèses et sources : voir « Méthode et sources du simulateur » sous le simulateur (index.html).
     Tout est calculé ici, dans le navigateur. simulation.php ne fait qu'envoyer par e-mail les valeurs
     calculées : toute modification du modèle se fait dans ce bloc et dans le texte de méthode. */
  var simu = document.querySelector('[data-simu]');
  if (simu) {
    var ZONE_H1 = '01 02 03 05 08 10 14 15 19 21 23 25 27 28 38 39 42 43 45 51 52 54 55 57 58 59 60 61 62 63 67 68 69 70 71 73 74 75 76 77 78 80 87 88 89 90 91 92 93 94 95'.split(' ');
    var ZONE_H2 = '04 07 09 12 16 17 18 22 24 26 29 31 32 33 35 36 37 40 41 44 46 47 48 49 50 53 56 64 65 72 79 81 82 84 85 86'.split(' ');
    var ZONE_H3 = '06 11 13 20 30 34 66 83'.split(' ');
    var CEE_KWHC = { H1: 160, H2: 170, H3: 270 };   // fiche BAT-EN-112 : kWh cumac par m² de toiture traitée
    var CEE_PRIX = 8.70;                            // €/MWh cumac : indice de prix à terme des CEE classiques, juin 2026
    var INTENSITE = { industrie: 65, logistique: 65, distribution: 110, tertiaire: 126, collectivites: 126, agricole: 19 }; // kWh/m²/an (OID, données 2024)
    var PART_CLIM = { H1: 0.15, H2: 0.20, H3: 0.30, CH: 0.15, IT: 0.30, ES: 0.30 }; // hypothèse ALBEDIA
    var GAIN = 0.20;                                // US EPA : économie moyenne sur la climatisation
    var GAIN_ASPECT = { sombre: 1, clair: 0.5, reflechissant: 0 }; // hypothèse ALBEDIA
    var MULTI_NIVEAUX = { tertiaire: true, collectivites: true };
    var HAUTEUR_NIVEAU = 3.5;
    var CONSO_MAX = 50000000;
    var PAYS = { FR: 'France', CH: 'Suisse', IT: 'Italie', ES: 'Espagne' };

    var sForm = document.getElementById('simu-form');
    var cpInput = document.getElementById('s-cp');
    var zoneTxt = document.getElementById('s-zone');
    var surfaceTxt = document.getElementById('s-surface');
    var consoRange = document.getElementById('s-conso');
    var consoNum = document.getElementById('s-conso-num');
    var consoTag = document.getElementById('s-conso-tag');
    var consoReset = document.getElementById('s-conso-reset');
    var prixRange = document.getElementById('s-prix');
    var prixOut = document.getElementById('s-prix-out');
    var rEur = document.getElementById('r-eur');
    var rUnit = simu.querySelector('.simu-unit');
    var rLine = document.getElementById('r-line');
    var rBarEte = document.getElementById('r-bar-ete');
    var rKwhEte = document.getElementById('r-kwh-ete');
    var rKwhReste = document.getElementById('r-kwh-reste');
    var rCee = document.getElementById('r-cee');
    var rCeeNote = document.getElementById('r-cee-note');
    var rPoints = document.getElementById('r-points');
    var peek = document.getElementById('simu-peek');
    var peekEur = document.getElementById('p-eur');
    var peekCee = document.getElementById('p-cee');
    var consoManuelle = null;   // null : on affiche l'estimation
    var dernier = {};           // dernier calcul, envoyé avec l'e-mail

    var nf = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 });
    var fmt = function (x) { return nf.format(x).replace(/[  ]/g, ' '); };
    var arrondi = function (x) {
      if (x >= 100000) return Math.round(x / 1000) * 1000;
      if (x >= 10000) return Math.round(x / 100) * 100;
      if (x >= 1000) return Math.round(x / 10) * 10;
      return Math.round(x);
    };
    var choix = function (name) {
      var el = sForm.querySelector('input[name="' + name + '"]:checked');
      return el ? el.value : '';
    };
    var nombre = function (id, def, min, max) {
      var v = parseFloat(String(document.getElementById(id).value).replace(',', '.'));
      if (!isFinite(v) || v <= 0) return def;
      return Math.min(max, Math.max(min, v));
    };
    var zoneDe = function (cp) {
      if (!/^\d{5}$/.test(cp)) return null;
      var d = cp.slice(0, 2);
      if (d === '97') return cp.slice(0, 3) === '975' ? 'H1' : 'H3';
      if (ZONE_H1.indexOf(d) >= 0) return 'H1';
      if (ZONE_H2.indexOf(d) >= 0) return 'H2';
      if (ZONE_H3.indexOf(d) >= 0) return 'H3';
      return null;
    };
    var remplir = function (range) {
      var min = parseFloat(range.min) || 0, max = parseFloat(range.max) || 100;
      var pct = max > min ? (parseFloat(range.value) - min) / (max - min) * 100 : 0;
      range.style.setProperty('--fill', Math.max(0, Math.min(100, pct)).toFixed(2) + '%');
    };
    var majConso = function (valeur, estimation, depuisCurseur) {
      if (!depuisCurseur) {
        var max = Math.max(100000, Math.ceil(Math.max(estimation * 2, valeur * 1.25) / 10000) * 10000);
        consoRange.max = String(max);
        consoRange.step = max > 2000000 ? '10000' : '1000';
        consoRange.value = String(valeur);
      }
      remplir(consoRange);
      if (document.activeElement !== consoNum) consoNum.value = fmt(Math.round(valeur));
      consoTag.textContent = consoManuelle === null ? 'Estimation' : 'Votre consommation';
      consoTag.classList.toggle('is-user', consoManuelle !== null);
      consoReset.hidden = consoManuelle === null;
    };
    var lireNombre = function (texte, max) {   // « 440 000 », « 440.000 », « 440000,5 »… ; null si vide
      var t = String(texte).replace(/[\s\u00a0\u202f]/g, '');
      if (t === '') return null;
      var v = /^\d+([.,]\d{1,2})?$/.test(t) ? parseFloat(t.replace(',', '.')) : parseFloat(t.replace(/\D/g, ''));
      return isFinite(v) ? Math.min(v, max) : null;
    };
    var lireConso = function (texte) { return lireNombre(texte, CONSO_MAX); };
    var fmtDec = function (x) { return (Math.round(x * 10) / 10).toFixed(1).replace('.', ','); };
    var point = function (texte) {
      var li = document.createElement('li');
      li.textContent = texte;
      rPoints.appendChild(li);
    };

    var calculer = function (depuisCurseur) {
      var pays = choix('pays') || 'FR';
      var cp = cpInput.value.trim();
      var zone = pays === 'FR' ? zoneDe(cp) : null;
      var cleClimat = pays === 'FR' ? (zone || 'H2') : pays;
      simu.classList.toggle('is-abroad', pays !== 'FR');

      if (pays !== 'FR') zoneTxt.textContent = '';
      else if (zone) zoneTxt.textContent = 'Zone climatique ' + zone + '.';
      else if (cp.length === 5) zoneTxt.textContent = 'Code postal non reconnu : la zone H2 est retenue.';
      else zoneTxt.textContent = 'Indiquez le code postal pour connaître la zone climatique.';

      var secteur = choix('secteur') || 'distribution';
      var L = nombre('s-long', 80, 5, 1000);
      var l = nombre('s-larg', 50, 5, 1000);
      var H = nombre('s-haut', 8, 2, 60);
      var S = Math.round(L * l);
      var niveaux = MULTI_NIVEAUX[secteur] ? Math.max(1, Math.round(H / HAUTEUR_NIVEAU)) : 1;
      surfaceTxt.textContent = 'Surface de toiture : ' + fmt(S) + ' m²' +
        (niveaux > 1 ? ' · ' + niveaux + ' niveaux, soit ' + fmt(S * niveaux) + ' m² de plancher' : ' · bâtiment de plain-pied');

      var estimation = arrondi(S * niveaux * INTENSITE[secteur]);
      var conso = consoManuelle === null ? estimation : consoManuelle;
      majConso(conso, estimation, depuisCurseur);

      var prix = parseFloat(prixRange.value) || 0.2;
      prixOut.textContent = prix.toFixed(2).replace('.', ',') + ' €';
      remplir(prixRange);

      var clim = choix('clim'), chauffage = choix('chauffage'), aspect = choix('aspect') || 'sombre';
      var etat = choix('etat'), couverture = choix('couverture');
      var facteurClim = clim === 'totale' ? 1 : (clim === 'partielle' ? 0.5 : 0);
      var ete = conso * PART_CLIM[cleClimat] * facteurClim;
      var reste = Math.max(0, conso - ete);
      var gainKwh = ete / niveaux * GAIN * GAIN_ASPECT[aspect];
      var gainEur = gainKwh * prix;
      var lieu = pays === 'FR' ? 'en zone ' + cleClimat : 'en ' + PAYS[pays];
      var qualitatif = aspect === 'reflechissant' || facteurClim === 0;
      simu.classList.toggle('is-qualitative', qualitatif);

      if (aspect === 'reflechissant') {
        rEur.textContent = 'Gain faible';
        rLine.textContent = 'Votre toiture est déjà réfléchissante : un nouveau revêtement apporterait peu. Un nettoyage peut lui rendre une partie de sa réflectance.';
      } else if (facteurClim === 0) {
        rEur.textContent = 'Confort d’été';
        rLine.textContent = 'Sans climatisation, pas de facture d’été à réduire, mais moins de surchauffe : en plein été, une toiture traditionnelle sombre dépasse la température de l’air de 31 à 47 °C, une toiture réfléchissante de 6 à 11 °C seulement (US EPA).';
      } else {
        rEur.textContent = '≈ ' + fmt(arrondi(gainEur)) + ' €';
        rLine.textContent = 'Soit environ ' + fmt(arrondi(gainKwh)) + ' kWh de climatisation en moins chaque année, pour une toiture de ' + fmt(S) + ' m² ' + lieu + '.';
      }
      rUnit.hidden = qualitatif;

      var pctEte = conso > 0 ? ete / conso * 100 : 0;
      rBarEte.style.width = pctEte.toFixed(2) + '%';
      rKwhEte.textContent = fmt(arrondi(ete)) + ' kWh';
      rKwhReste.textContent = fmt(arrondi(reste)) + ' kWh';

      /* prime CEE : fiche BAT-EN-112 (bâtiment tertiaire à usage commercial) */
      var cee = null, statut = '', ceeStatut = 'ok', notes = [];
      if (pays !== 'FR') {
        ceeStatut = 'etranger';
        statut = 'Non applicable';
        notes.push('Les CEE sont un dispositif français : d’autres aides peuvent exister en Suisse, en Italie et en Espagne.');
      } else if (secteur === 'industrie' || secteur === 'agricole') {
        ceeStatut = 'secteur';
        statut = 'Non éligible à la fiche BAT-EN-112';
        notes.push('Cette fiche concerne les bâtiments tertiaires à usage commercial. Nous vérifions lors de l’étude si un autre dispositif s’applique à votre site.');
      } else if (aspect === 'reflechissant') {
        ceeStatut = 'reflechissant';
        statut = 'Non éligible';
        notes.push('La fiche BAT-EN-112 exige une toiture sans revêtement réflectif avant les travaux.');
      } else if (facteurClim === 0) {
        ceeStatut = 'sans-clim';
        statut = 'Non éligible';
        notes.push('La toiture doit couvrir un volume fermé et climatisé.');
      } else if (chauffage !== 'pac') {
        ceeStatut = 'chauffage';
        statut = 'Non éligible';
        notes.push('La fiche exige un chauffage et une climatisation assurés par une pompe à chaleur.');
      } else {
        cee = S * facteurClim * CEE_KWHC[cleClimat] / 1000 * CEE_PRIX;
        statut = '≈ ' + fmt(arrondi(cee)) + ' €';
        notes.push('Sous réserve d’éligibilité, sur la base de 8,70 € le MWh cumac (indice de prix des CEE classiques, juin 2026). Le montant versé dépend du financeur.');
        if (facteurClim < 1) notes.push('Calculée sur la moitié de la toiture, au-dessus de la partie climatisée.');
        if (secteur !== 'distribution') notes.push('L’usage commercial du bâtiment, exigé par la fiche, est à vérifier.');
        if (!zone) notes.push('Zone H2 retenue en attendant votre code postal.');
      }
      rCee.textContent = statut;
      rCee.classList.toggle('is-off', cee === null);
      rCeeNote.textContent = notes.join(' ');

      rPoints.innerHTML = '';
      if (consoManuelle === null) point('Consommation estimée : ' + fmt(conso) + ' kWh par an (' + INTENSITE[secteur] + ' kWh par m² de plancher).');
      else point('Votre consommation : ' + fmt(Math.round(conso)) + ' kWh par an.');
      point('Toiture de ' + fmt(S) + ' m² sans ombrage' + (niveaux > 1 ? ', sur ' + niveaux + ' niveaux : le gain porte sur le dernier niveau.' : '.'));
      if (aspect === 'clair') point('Toiture déjà grise ou claire : le gain retenu est la moitié de celui d’une toiture sombre.');
      if (etat === 'degradee') point('Toiture dégradée : une réfection d’étanchéité s’impose avant tout revêtement.');
      else if (etat === 'reprises') point('Quelques reprises à prévoir avant l’application, chiffrées lors de la visite.');
      else point('Toiture en bon état : application après nettoyage et préparation du support.');
      if (couverture === 'fibres-ciment') point('Fibres-ciment : repérage de l’amiante obligatoire avant travaux sur les bâtiments construits avant le 1er juillet 1997.');
      if (chauffage === 'aucun') point('Bâtiment non chauffé : aucun surcoût de chauffage en hiver.');
      else if (aspect !== 'reflechissant') point('En hiver, la toiture capte un peu moins de chaleur solaire : ce léger surcoût de chauffage est en général compensé par les économies d’été (US EPA).');

      if (peek) {
        peekEur.textContent = qualitatif ? rEur.textContent : rEur.textContent + ' / an';
        peekCee.textContent = cee === null ? (pays !== 'FR' ? 'Non applicable' : 'Non éligible') : statut;
      }

      dernier = {
        pays: pays, code_postal: pays === 'FR' ? cp : '', zone: pays === 'FR' ? cleClimat : '', secteur: secteur,
        longueur: L, largeur: l, hauteur: H, surface: S, niveaux: niveaux, couverture: couverture, aspect: aspect,
        etat: etat, clim: clim, chauffage: chauffage, conso: Math.round(conso),
        conso_source: consoManuelle === null ? 'estimation' : 'declaree', prix: prix.toFixed(2),
        conso_ete: Math.round(ete), gain_kwh: Math.round(gainKwh), gain_eur: Math.round(gainEur),
        cee_statut: ceeStatut, cee_eur: cee === null ? '' : Math.round(cee)
      };
      majRoi();
    };

    /* retour sur investissement (page Rentabilité et ROI) */
    var roi = document.querySelector('[data-roi]');
    var roiMontant = roi ? document.getElementById('roi-montant') : null;
    var HORIZON = 20;   // durée de vie conventionnelle de la fiche CEE BAT-EN-112 (pas une garantie de durée)
    var roiSet = function (id, texte, estTexte) {
      var el = document.getElementById(id);
      if (!el) return;
      el.textContent = texte;
      if (estTexte !== undefined) el.classList.toggle('is-text', !!estTexte);
    };
    var majRoi = function () {
      if (!roi) return;
      var d = dernier;
      var eco = d.gain_eur > 0 ? d.gain_eur : 0;
      var cee = d.cee_eur === '' || !d.cee_eur ? 0 : d.cee_eur;
      var S = d.surface || 0;
      var montant = lireNombre(roiMontant.value, 1000000000);
      roiSet('roi-eco', eco > 0 ? '≈\u00a0' + fmt(arrondi(eco)) + '\u00a0€ par an' : 'non chiffrées');
      roiSet('roi-cee', cee > 0 ? '≈\u00a0' + fmt(arrondi(cee)) + '\u00a0€' : (d.pays !== 'FR' ? 'non applicable' : 'non éligible'));
      roiSet('roi-surface', fmt(S) + '\u00a0m²');
      [5, 10, 20].forEach(function (n) {
        var b = cee + eco * n;
        var ok = b > 0;
        roiSet('roi-b' + n, ok ? '≈\u00a0' + fmt(arrondi(b)) + '\u00a0€' : '—');
        roiSet('roi-b' + n + 'm', ok && S > 0 ? 'soit ' + fmtDec(b / S) + '\u00a0€ HT par m²' : '');
      });
      if (eco <= 0) {
        roiSet('roi-retour', 'Non chiffrable', true);
        roiSet('roi-retour-txt', d.aspect === 'reflechissant'
          ? 'Votre toiture est déjà réfléchissante : un nouveau revêtement apporterait peu d’économies.'
          : 'Sans climatisation, il n’y a pas de facture d’été à réduire : la rentabilité se juge sur le confort des équipes, la protection des marchandises et la toiture.');
        roiSet('roi-gain', '—', false);
        roiSet('roi-gain-txt', '');
      } else if (montant === null) {
        roiSet('roi-retour', 'Indiquez votre devis', true);
        roiSet('roi-retour-txt', 'Saisissez le montant de votre devis, ou comparez-le au budget remboursé ci-dessous.');
        roiSet('roi-gain', '—', false);
        roiSet('roi-gain-txt', 'Sur 20 ans, vos économies estimées représentent ≈\u00a0' + fmt(arrondi(eco * HORIZON)) + '\u00a0€.');
      } else {
        var net = Math.max(0, montant - cee);
        var ans = net / eco;
        var gain = eco * HORIZON - net;
        if (net === 0) roiSet('roi-retour', 'Immédiat', true);
        else roiSet('roi-retour', '≈\u00a0' + (ans < 10 ? fmtDec(ans) : fmt(Math.round(ans))) + (ans < 2 ? '\u00a0an' : '\u00a0ans'), false);
        roiSet('roi-retour-txt', net === 0 ? 'La prime CEE estimée couvre le montant de votre devis.' :
          'Pour un investissement net de ' + fmt(arrondi(net)) + '\u00a0€ HT, prime CEE déduite.' +
          (ans > HORIZON ? ' Au-delà de 20 ans, les seules économies d’énergie ne remboursent pas les travaux.' : ''));
        roiSet('roi-gain', (gain < 0 ? '≈\u00a0−' : '≈\u00a0') + fmt(arrondi(Math.abs(gain))) + '\u00a0€', false);
        roiSet('roi-gain-txt', '20 ans d’économies, soit ≈\u00a0' + fmt(arrondi(eco * HORIZON)) + '\u00a0€, moins l’investissement net.');
      }
    };
    if (roiMontant) {
      roiMontant.addEventListener('input', majRoi);
      roiMontant.addEventListener('blur', function () {
        var v = lireNombre(roiMontant.value, 1000000000);
        roiMontant.value = v === null ? '' : fmt(Math.round(v));
      });
    }

    sForm.addEventListener('submit', function (e) { e.preventDefault(); });
    sForm.addEventListener('change', function () { calculer(false); });
    sForm.addEventListener('input', function (e) {
      if (e.target === consoRange) {
        consoManuelle = parseFloat(consoRange.value);
        calculer(true);
      } else if (e.target === consoNum) {
        consoManuelle = lireConso(consoNum.value);   // champ vidé : retour à l'estimation
        calculer(false);
      } else if (e.target.type !== 'radio') {
        calculer(false);
      }
    });
    consoNum.addEventListener('blur', function () { consoNum.value = fmt(dernier.conso || 0); });
    consoReset.addEventListener('click', function () {
      consoManuelle = null;
      calculer(false);
      consoRange.focus();
    });
    calculer(false);

    /* sur mobile, rappel du résultat en bas de l'écran tant que le formulaire est affiché */
    if (peek && 'IntersectionObserver' in window) {
      var formVu = false, resultatVu = false;
      var cible = document.getElementById('simu-resultat');
      var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.target === sForm) formVu = en.isIntersecting;
          else resultatVu = en.isIntersecting;
        });
        peek.classList.toggle('is-on', formVu && !resultatVu);
      });
      obs.observe(sForm);
      obs.observe(cible);
    }

    /* envoi de la simulation par e-mail */
    var mail = document.getElementById('simu-mail');
    var mailStatus = document.getElementById('simu-status');
    var mailBtn = mail.querySelector('button[type="submit"]');
    var mailBtnHtml = mailBtn.innerHTML;
    var mailDebut = Date.now();
    var mailMsg = function (kind, text) {
      mailStatus.className = 'form-status ' + kind;
      mailStatus.textContent = text;
      mailStatus.hidden = false;
    };
    mail.addEventListener('submit', function (e) {
      e.preventDefault();
      var email = mail.elements.email;
      if (!email.value || !email.checkValidity()) {
        mailMsg('err', 'Indiquez une adresse e-mail valide.');
        email.focus();
        return;
      }
      if (mail.getAttribute('data-preview')) {
        mailMsg('info', 'Aperçu du site : l’envoi de la simulation sera actif une fois le site en ligne sur albedia.eu.');
        return;
      }
      var data = new FormData(mail);
      data.append('elapsed', String(Date.now() - mailDebut));
      Object.keys(dernier).forEach(function (k) { data.append(k, String(dernier[k])); });
      mailBtn.disabled = true;
      mailBtn.textContent = 'Envoi en cours…';
      fetch(mail.getAttribute('action'), { method: 'POST', body: data, headers: { 'Accept': 'application/json' } })
        .then(function (res) { return res.json().catch(function () { return { ok: false }; }); })
        .then(function (res) {
          if (res && res.ok) mailMsg('ok', 'C’est envoyé : vous allez recevoir votre simulation par e-mail. Nous revenons vers vous rapidement.');
          else mailMsg('err', (res && res.error) || 'L’envoi n’a pas abouti. Réessayez ou écrivez-nous à contact@albedia.eu.');
        })
        .catch(function () { mailMsg('err', 'L’envoi n’a pas abouti. Vérifiez votre connexion ou écrivez-nous à contact@albedia.eu.'); })
        .then(function () { mailBtn.disabled = false; mailBtn.innerHTML = mailBtnHtml; });
    });
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
