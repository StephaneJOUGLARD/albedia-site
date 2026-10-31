# Site albedia.eu (ALBEDIA, cool roof)

Site vitrine d'ALBEDIA, société de GROUPE NOVELIA qui applique des revêtements réfléchissants
(cool roof) sur les toitures des bâtiments professionnels. Site statique HTML/CSS/JS, en français,
avec un formulaire de devis en PHP.

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
    automatique, balises SEO, sitemap. Réglages en tête : `SITE_URL`, `EMAIL`, `PHONE`, `LASTMOD`.
  - `pages/*.html` : le contenu de chaque page (balises `{{…}}` remplacées au build).
  - `pages/secteurs.json` : contenu des six pages secteur. `pages/faq.json` : questions et réponses.
  - `partials/` : logo, soleil, illustrations SVG et icônes.
  - `assets/` : feuille de style, script, police auto-hébergée (Plus Jakarta Sans, licence OFL), logos, favicons.
  - `php/contact.php` (formulaire de devis, fonction `mail()` d'OVH) et `php/.htaccess`.
- À la racine : le site généré (pages `.html`, `assets/`, `contact.php`, `.htaccess`, `sitemap.xml`,
  `robots.txt`). **Ne pas modifier ces fichiers à la main** : ils sont écrasés à chaque build.

Après toute modification de `_src/` : `python3 _src/build.py`, puis commit des sources ET des fichiers
générés. Si une page est renommée ou supprimée, supprimer aussi l'ancien fichier `.html` à la racine.

Test local : `php -S 127.0.0.1:8765 -t .` (le `.htaccess` n'y est pas appliqué).

## Balises disponibles dans les pages

`{{EYEBROW}}` (soleil + slogan de la page), `{{SLOGAN}}`, `{{BREADCRUMB}}`, `{{icon:nom}}`,
`{{include:fichier.svg}}`, `{{EMAIL}}`, `{{EMAIL_LINK}}`, `{{PHONE}}`, `{{SECTOR_TILES}}`,
`{{SECTOR_OPTIONS}}`, `{{FAQ_HOME}}`, `{{FAQ_FULL}}`, `{{TODO:texte}}` (information à compléter,
affichée surlignée en jaune).

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

## Informations encore à compléter

Mentions légales (forme juridique, capital, siège, ville du RCS, SIREN, TVA, téléphone, directeur
de la publication) et adresse du siège dans la politique de confidentialité : balises `{{TODO:…}}`
dans `_src/pages/mentions-legales.html` et `_src/pages/confidentialite.html`. Téléphone : `PHONE`
dans `build.py`.
