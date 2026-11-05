# Site albedia.eu (ALBEDIA, cool roof)

Site vitrine d'ALBEDIA, marque commerciale déposée à l'INPI et exploitée par la SAS CGBI
(CONTRACTANT GENERAL EN BATIMENTS INDUSTRIELS, Grenoble), filiale de GROUPE NOVELIA. ALBEDIA applique
des revêtements réfléchissants (cool roof) sur les toitures des bâtiments professionnels.
Site statique HTML/CSS/JS, en français, avec un formulaire de devis en PHP. L'éditeur du site
(mentions légales, confidentialité) est CGBI ; le directeur de la publication est M. Stéphane JOUGLARD.

## Mise en ligne : chaque push sur `main` publie le site

L'hébergement OVHcloud de albedia.eu est relié à ce dépôt (onglet « Mes sites », colonne Git) :
le contenu de la branche `main` est copié dans le dossier `www` de l'hébergement. Un webhook GitHub
déclenche ce déploiement à chaque push ; sans lui, le propriétaire clique sur « Déployer Git » chez OVH.

Donc :
- ne jamais pousser sur `main` sans l'accord explicite du propriétaire (Stéphane) ;
- lui montrer d'abord un aperçu : `python3 _src/build.py preview /tmp/albedia-preview`, puis publier
  ce dossier comme artifact (le fichier `index.html` comme page principale, les autres fichiers à côté) ;
- ne jamais mettre de mot de passe, clé ou donnée confidentielle dans le dépôt : il est public.

## Structure

- `_src/` : les sources. **On ne modifie que ce dossier**, puis on régénère.
  - `build.py` : gabarits communs (en-tête, menu, pied de page, bandeau final), liste des pages
    (`PAGES`, dont l'ordre fixe l'alternance des slogans), secteurs (`SECTORS`), typographie française
    automatique, balises SEO, sitemap. Réglages en tête : `SITE_URL`, `EMAIL`, `PHONE`, `LASTMOD`,
    `BASELINE` (« Augmentez votre albédo ! » sous le logo, en SVG justifié sur la largeur du mot « albedia »
    par `textLength` : voir `brand()` et `.brand-tag`), `SUPPORTS` (pages par type de toiture),
    `MENUS` (menu principal à sous-menus) et `FOOTER_COLS` (colonnes du pied de page). Une nouvelle page
    s'ajoute dans `PAGES` (et dans `MENUS` / `FOOTER_COLS` si elle doit y figurer).
  - `?v=` des liens vers `style.css` et `main.js` (dans `build.py`) : à incrémenter à chaque modification
    de la feuille de style ou du script, sinon les visiteurs gardent l'ancienne version en cache un mois.
  - `pages/*.html` : le contenu de chaque page (balises `{{…}}` remplacées au build).
  - `pages/secteurs.json` : contenu des six pages secteur. `pages/faq.json` : questions et réponses.
  - Pages de contenu ajoutées en novembre 2026 : `rentabilite-cool-roof.html` (avec le simulateur et le calcul
    du retour sur investissement), cinq pages par type de toiture (`cool-roof-*.html`), `decret-tertiaire.html`,
    `chaleur-au-travail.html`, `indice-sri.html`, `zones-intervention.html`. Leurs questions fréquentes sont dans
    `pages/faq-*.json` (clé `faq` de la page dans `PAGES`, balise `{{FAQ_PAGE}}`, données structurées FAQPage).
  - Toitures photovoltaïques (`cool-roof-photovoltaique.html`) et page « Vous êtes un particulier ? »
    (`particuliers.html`) : les particuliers sont orientés vers France Rénov’ (choix du propriétaire).
  - Pages ville (« Le cool roof à … ») générées depuis `pages/villes.json` (climat, contexte, zone CEE, villes
    proches) par `city_page()` : fichiers `cool-roof-<ville>.html`, données structurées Service, lien vers le
    simulateur prérempli (`?cp=` ou `?pays=CH`). Les régions et départements (`REGIONS`, `DEPTS`, zones CEE) sont
    dans `build.py` ; balises `{{REGIONS}}` et `{{VILLES}}` pour la page Zones d'intervention. La liste « Le cool
    roof par ville » du pied de page reprend toutes les villes du fichier. Pour ajouter une ville : une entrée
    dans `villes.json` (textes originaux et exacts, sans chiffre non sourcé), puis rebuild.
  - Carte des zones climatiques (balise `{{CARTE_ZONES}}`, page Zones d'intervention) : départements colorés selon
    leur zone (H1, H2, H3), orange avec une bulle « Nom (n°) / Zone climatique Hx » au survol ou au toucher, encadré
    agrandi pour Paris et la petite couronne. Tracés dans `partials/carte-departements.json`, produits une fois pour
    toutes par `_src/carte.py` (Lambert-93, simplification qui garde les frontières communes) à partir des contours
    IGN ADMIN EXPRESS 2018 (Licence Ouverte) publiés par France GeoJSON : la source est créditée sous la carte et
    dans les mentions légales. Noms et zones viennent de `DEPTS` et `zone_of()` ; le comportement est dans
    `main.js` (bloc « carte des zones climatiques »).
  - Plaquette de présentation : `assets/docs/plaquette-albedia.pdf` (constante `PLAQUETTE`), rendue depuis l'artifact
    Design « Plaquette ALBEDIA » (A3 plié en A4 : deux planches, extérieur et intérieur). Le PDF suit l'ordre de lecture
    (couverture A4, intérieur A3, dos A4), avec des photos en JPEG à environ deux fois leur taille d'affichage pour rester
    léger (1,4 Mo). Liens : menu ALBEDIA, pied de page, bandeau final, page Qui sommes-nous (`#plaquette`, vignette
    `assets/img/plaquette-albedia.webp`) et devis ; balises `{{PLAQUETTE_HREF}}` (lien avec une empreinte `?v=` du
    fichier, recalculée au build), `{{PLAQUETTE_ATTR}}` et `{{PLAQUETTE_TAILLE}}`. Nouvelle version : remplacer le PDF
    et la vignette, puis rebuild. La plaquette ne parle de CGBI qu'en pied de la dernière page (choix du propriétaire).
  - `i18n/en/`, `i18n/it/`, `i18n/es/` : versions anglaise, italienne et espagnole de 13 pages (voir « Langues »).
  - `partials/` : logo, soleil, illustrations SVG et icônes.
  - `assets/` : feuille de style, script, police auto-hébergée (Plus Jakarta Sans, licence OFL), logos, favicons.
  - `php/contact.php` (formulaire de devis, fonction `mail()` d'OVH), `php/simulation.php` (envoi par e-mail
    d'une simulation, au visiteur et à contact@albedia.eu) et `php/.htaccess`.
- À la racine : le site généré (pages `.html`, dossiers `en/`, `it/` et `es/`, `assets/`, `contact.php`, `.htaccess`,
  `sitemap.xml`, `robots.txt`). **Ne pas modifier ces fichiers à la main** : ils sont écrasés à chaque build.

Après toute modification de `_src/` : `python3 _src/build.py`, puis commit des sources ET des fichiers
générés. Si une page est renommée ou supprimée, supprimer aussi l'ancien fichier `.html` à la racine.

Test local : `php -S 127.0.0.1:8765 -t .` (le `.htaccess` n'y est pas appliqué).

## Balises disponibles dans les pages

`{{EYEBROW}}` (soleil + slogan de la page), `{{SLOGAN}}`, `{{BREADCRUMB}}`, `{{icon:nom}}`,
`{{include:fichier.svg}}`, `{{EMAIL}}`, `{{EMAIL_LINK}}`, `{{PHONE}}`, `{{PHONE_LINK}}`, `{{AREA}}`
(zone d'intervention : « en France, en Suisse, en Italie et en Espagne »), `{{SECTOR_TILES}}`, `{{SECTOR_OPTIONS}}`,
`{{FAQ_HOME}}`, `{{FAQ_FULL}}`, `{{FAQ_PAGE}}`, `{{PHOTO_CREDITS}}`, `{{CARTE_ZONES}}`, `{{SIMULATEUR}}` (simulateur, partagé
entre l'accueil et la page Rentabilité : `partials/simulateur.html`), `{{TODO:texte}}` (information à compléter,
affichée surlignée en jaune).

Photos : `{{img:slug}}` (ou `{{img:slug|sizes}}`) dans une `<figure class="photo">`, `{{bg:slug}}` en fond
d'un en-tête (`page-head--photo`, `hero--photo`, chargée en priorité) et `{{bg-lazy:slug}}` en fond d'un
bandeau plus bas (`photo-band`).

## Photos

- Registre : `_src/pages/photos.json` (texte alternatif, cadrage `pos`, largeurs, auteur, lien Unsplash).
  Fichiers : `_src/assets/img/photos/<slug>-<largeur>.webp` (640, 1280, 1920, parfois 2400 px).
- Ce sont des photos d'illustration Unsplash (licence Unsplash), toutes créditées automatiquement dans les
  mentions légales. Ne jamais les présenter comme des chantiers ou réalisations d'ALBEDIA (pas de légende
  du type « nos réalisations ») ; n'utiliser que des photos « gratuites », jamais Unsplash+.
- Retouches déjà faites : logo effacé sur la casquette (`application-toiture`), haut de l'image recadré
  pour retirer des inscriptions (`atelier-industriel`).
- Pour ajouter une photo : `python3 _src/photos.py <image.jpg> <nom-court> --alt … --auteur … --compte …
  --source …` (WebP qualité 70 aux largeurs 640/1280/1920 et entrée dans `photos.json`), puis rebuild.
- Les secteurs (`SECTORS` dans `build.py`) ont une photo de vignette/en-tête (`photo`) et une photo de
  contenu (`photo2`).

## Simulateur (accueil, `#simulateur`)

Le simulateur d'économies et de prime CEE est calculé en JavaScript dans `assets/js/main.js` (bloc « simulateur »,
qui calcule aussi le retour sur investissement de la page Rentabilité, `[data-roi]`). Son balisage est dans
`partials/simulateur.html`. Ses hypothèses et sources sont exposées sous le simulateur (« Méthode et sources du
simulateur », dans ce même partiel) :
toute modification d'une valeur (intensités OID, part de la climatisation, gain EPA, barème BAT-EN-112, prix du
MWh cumac) se fait aux deux endroits, ainsi que dans les versions traduites (`_src/i18n/*/simulateur.html` pour la
méthode, `_src/i18n/*/js.json` pour les textes de résultat). `simulation.php` ne recalcule rien : il contrôle les valeurs reçues (listes
autorisées, nombres bornés) et envoie un récapitulatif au texte fixe. Le prix du MWh cumac (indice du ministère)
est à actualiser de temps en temps.

## Langues

Versions traduites (novembre 2026) : 13 pages existent en anglais, en italien et en espagnol, publiées dans `/en/`,
`/it/` et `/es/` : accueil, solutions, guide, rentabilité (avec le simulateur), les six secteurs, qui sommes-nous,
zones d'intervention et devis. Sources dans `_src/i18n/<langue>/` :
- `ui.json` : textes communs (en-tête, menus, pied de page, bandeau final), libellés des secteurs, textes
  alternatifs des photos, textes de la carte, et les pages traduites (`pages` : titre, description, fil d'Ariane,
  FAQ, second bouton du bandeau). La clé `pages` de la première langue fixe la liste `TRANSLATED` de `build.py`.
  La signature sous le logo (`baseline`) doit rester assez courte pour tenir sur la largeur du mot « albedia ».
- `secteurs.json` (pages secteur), `faq-home.json`, `faq-rentabilite.json`, `pages/*.html` (contenu des pages) et
  `simulateur.html`, sans l'envoi par e-mail (le récapitulatif de `simulation.php` est en français). Pays par défaut
  du simulateur : France en anglais, Italie en italien, Espagne en espagnol.
- `js.json` : textes et formats (séparateur décimal, place du symbole €) lus par `main.js`, injectés dans chaque page
  traduite (`<script type="application/json" id="i18n-js">`). Dans `main.js`, chaque texte passe par
  `tr('clé', 'texte français')` : une clé absente garde le texte français.

Contenu adapté à chaque pays, sans chiffre nouveau : les CEE ne valent qu'en France ; Italie : décret sur les
exigences minimales du 28 octobre 2025 (réflectance d'au moins 0,65 en toiture plate et 0,30 en pente) ; Espagne :
Real Decreto 36/2023 ; Suisse : compétence des cantons (Constitution fédérale, art. 89). Les exemples chiffrés de la
page Rentabilité sont ceux du simulateur, avec ses hypothèses par défaut. Les liens vers les pages restées en français
pointent vers `../page.html` avec la mention « en français ». Toute modification d'un texte réglementaire ou chiffré
(CEE, décret tertiaire, hypothèses du simulateur) est à reporter dans les trois langues. Une relecture par des
locuteurs natifs reste conseillée.

Formulaire de devis traduit : les valeurs envoyées restent en français (celles qu'attend `contact.php`), seuls les
libellés sont traduits ; deux champs en plus : `langue` (caché) et `pays`. `contact.php` répond dans la langue du
visiteur, renvoie vers `<langue>/devis.html` sans JavaScript, et indique la langue et le pays dans l'e-mail reçu, qui
reste en français.

Sur les 13 pages traduites, les boutons FR, EN, IT et ES mènent aux vraies versions de la page (`lang_switch` dans
`build.py`), avec les balises hreflang et les entrées du sitemap. Sur les autres pages, EN, IT et ES ouvrent la page
traduite par Google Traduction (simple lien vers translate.google.com, `LANGS` dans `build.py`) : aucun script ni
cookie sur albedia.eu. C'est décrit dans `confidentialite.html` et `mentions-legales.html`.

La page traduite est servie par Google à l'adresse albedia-eu.translate.goog. Google y réécrit nos liens EN, IT, ES
vers son propre service, ce qui imbrique deux traductions et affiche « Can't translate this page ». Le bloc « langues »
de `main.js` corrige cela sur ces pages : chaque bouton mène directement à la traduction voulue, FR devient un lien
vers la page d'origine et la langue affichée est mise en avant. Le sélecteur porte `translate="no"` (sinon Google
traduit « EN » en « IN »). Vérifié en conditions réelles le 5 novembre 2026.

## Règles de contenu

- Textes originaux uniquement. Le site concurrent covalba.fr a servi de référence pour la structure :
  ne jamais en reprendre les textes, images ou mise en page.
- Aucun chiffre sans source. Les chiffres actuels viennent de l'US EPA, du Lawrence Berkeley National
  Laboratory, de la Fédération française du bâtiment et de la fiche CEE BAT-EN-112 (liens sur
  `guide-cool-roof.html`). Ne jamais inventer de références clients, témoignages, réalisations, prix,
  garanties ou certifications : n'ajouter que ce que le propriétaire fournit.
- Slogans, en alternance d'une page à l'autre : « Vos toitures réfléchissent ! » et « Augmentez votre albédo ! ».
- Le site s'adresse aux clients en les vouvoyant. Nom de la société en capitales : ALBEDIA.
- Identité : logo « albedia » en minuscules grasses avec un soleil sur le i ; bleu marine #0F2B46,
  orange #EC7A14, bleu ciel #1E96D6.
- Le site affirme ne déposer aucun cookie : tout ajout de mesure d'audience ou de service tiers
  impose de mettre à jour `confidentialite.html` et `mentions-legales.html`.

## Référencement

L'adresse officielle du site est https://albedia.eu (sans www) : le `.htaccess` y renvoie les visites
en http:// et sur www.albedia.eu. Le site est validé dans Google Search Console par la balise
`GSC_VERIFICATION` de `build.py` (placée sur l'accueil) : ne pas la retirer. La propriété Search Console
à utiliser est https://albedia.eu/ (une première propriété avait été créée avec www).
