#!/usr/bin/env python3
"""Assemble le site ALBEDIA à partir des sources de _src/.

Utilisation (depuis la racine du dépôt) :
  python3 _src/build.py                     régénère le site à la racine du dépôt (ce que publie OVH)
  python3 _src/build.py preview <dossier>   produit un aperçu (polices Google Fonts, formulaire inactif)
                                            dans un dossier HORS du dépôt, pour le publier comme artifact
"""
import hashlib, html, json, os, re, shutil, sys, tempfile
from urllib.parse import quote

SRC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SRC)

SITE_URL = 'https://albedia.eu'
EMAIL = 'contact@albedia.eu'
PHONE = '06 83 48 06 15'   # affiché sur le site (pied de page, devis, mentions légales)
PHONE_TEL = '+33683480615'                     # même numéro, format international pour les liens « tel: »
LASTMOD = '2026-11-04'
GSC_VERIFICATION = 'ymRFVKE_Tfryz-8vZf1Ez11ze668aD4px2rOz4EN0yQ'   # Google Search Console, balise placée sur l'accueil
SLOGANS = ['Vos toitures réfléchissent\u00a0!', 'Augmentez votre albédo\u00a0!']

AREA = 'en France, en Suisse, en Italie et en Espagne'   # zone d'intervention affichée sur le site
COUNTRIES = ('France', 'Suisse', 'Italie', 'Espagne')   # pays de la zone d'intervention (données structurées)
BASELINE = 'Augmentez votre albédo\u00a0!'   # signature affichée sous le logo (en-tête et pied de page)

# plaquette de présentation à télécharger (PDF rendu depuis l'artifact « Plaquette ALBEDIA », voir CLAUDE.md)
PLAQUETTE = 'assets/docs/plaquette-albedia.pdf'
PLAQUETTE_ATTR = ' target="_blank" rel="noopener" type="application/pdf"'


def plaquette_href():
    """Lien vers la plaquette, avec une empreinte du fichier : une nouvelle version n'est jamais servie depuis le cache."""
    data = open(os.path.join(SRC, PLAQUETTE), 'rb').read()
    return '%s?v=%s' % (PLAQUETTE, hashlib.sha1(data).hexdigest()[:8])


def plaquette_taille(lang='fr'):
    mo = os.path.getsize(os.path.join(SRC, PLAQUETTE)) / 1e6
    if lang == 'fr':
        return ('PDF, %.1f Mo' % mo).replace('.', ',')
    return UI[lang]['pdf_size'].replace('{n}', ('%.1f' % mo).replace('.', UI[lang]['dec']))


# photo = vignette de l'accueil et bandeau de la page secteur ; photo2 = photo dans le contenu de la page
SECTORS = [
    dict(slug='industrie', label='Industrie', short='Ateliers et sites de production', icon='industrie',
         photo='site-industriel', photo2='atelier-industriel'),
    dict(slug='logistique', label='Logistique', short='Entrepôts et plateformes', icon='logistique',
         photo='plateforme-logistique', photo2='entrepot-toit-blanc'),
    dict(slug='distribution', label='Commerce et distribution', short='Magasins et surfaces de vente', icon='distribution',
         photo='zone-commerciale', photo2='centre-commercial'),
    dict(slug='tertiaire', label='Bureaux et tertiaire', short='Bureaux et bâtiments d’activité', icon='tertiaire',
         photo='parc-activites', photo2='immeuble-bureaux'),
    dict(slug='collectivites', label='Collectivités', short='Écoles, gymnases, équipements', icon='collectivites',
         photo='ecole-vue-aerienne', photo2='batiment-scolaire'),
    dict(slug='agricole', label='Agricole', short='Élevage, stockage, transformation', icon='agricole',
         photo='ferme-toits-blancs', photo2='hangar-agricole'),
]

# Langues proposées : traduction automatique de la page courante par Google Traduction (simple lien,
# aucun script ni cookie sur albedia.eu)
LANGS = [('en', 'EN', 'English', 'Translate this page into English (Google Translate)'),
         ('it', 'IT', 'Italiano', 'Traduci questa pagina in italiano (Google Traduttore)'),
         ('es', 'ES', 'Español', 'Traducir esta página al español (Google Traductor)')]

# Pages par type de toiture : (fichier, libellé court pour les menus)
SUPPORTS = [('cool-roof-bac-acier.html', 'Bac acier'),
            ('cool-roof-membrane.html', 'Membranes PVC, TPO, EPDM'),
            ('cool-roof-bitume.html', 'Étanchéité bitumineuse'),
            ('cool-roof-toit-terrasse-beton.html', 'Toit-terrasse en béton'),
            ('cool-roof-fibres-ciment.html', 'Fibres-ciment'),
            ('cool-roof-photovoltaique.html', 'Toitures photovoltaïques')]

# Menu principal : (clé « nav » des pages, libellé, entrées (fichier, icône, libellé) ou ('-', intertitre))
MENUS = [
    ('solutions', 'Solutions', [
        ('solutions.html', 'chantier', 'Notre solution cool roof'),
        ('guide-cool-roof.html', 'thermo', 'Le cool roof, comment ça marche'),
        ('indice-sri.html', 'mesure', 'Indice SRI et performances'),
        ('-', 'Par type de toiture')] + [(f, 'couches', label) for f, label in SUPPORTS]),
    ('secteurs', 'Secteurs', [(s['slug'] + '.html', s['icon'], s['label']) for s in SECTORS]),
    ('rentabilite', 'Rentabilité', [
        ('rentabilite-cool-roof.html', 'euro', 'Rentabilité et ROI'),
        ('rentabilite-cool-roof.html#simulateur', 'calendrier', 'Simulateur d’économies'),
        ('aides-reglementation.html', 'document', 'Prime CEE et aides')]),
    ('ressources', 'Ressources', [
        ('decret-tertiaire.html', 'bouclier', 'Décret tertiaire'),
        ('chaleur-au-travail.html', 'thermo', 'Chaleur au travail'),
        ('faq.html', 'question', 'Questions fréquentes')]),
    ('albedia', 'ALBEDIA', [
        ('qui-sommes-nous.html', 'interlocuteur', 'Qui sommes-nous'),
        ('zones-intervention.html', 'lieu', 'Zones d’intervention'),
        ('zones-intervention.html#villes', 'lieu', 'Le cool roof par ville'),
        ('particuliers.html', 'question', 'Vous êtes un particulier ?'),
        (PLAQUETTE, 'document', 'Plaquette de présentation (PDF)'),
        ('devis.html', 'mail', 'Devis et contact')]),
]

# Zones climatiques des fiches CEE, par département (France métropolitaine)
ZONE_H1 = '01 02 03 05 08 10 14 15 19 21 23 25 27 28 38 39 42 43 45 51 52 54 55 57 58 59 60 61 62 63 67 68 69 70 71 73 74 75 76 77 78 80 87 88 89 90 91 92 93 94 95'.split()
ZONE_H3 = '06 11 13 2A 2B 30 34 66 83'.split()
def zone_of(dep):
    return 'H1' if dep in ZONE_H1 else ('H3' if dep in ZONE_H3 else 'H2')
CEE_KWHC = {'H1': 160, 'H2': 170, 'H3': 270}   # fiche BAT-EN-112, kWh cumac par m²
CEE_PRIX = 8.70                                # €/MWh cumac, indice de prix des CEE classiques de juin 2026

DEPTS = dict(x.split(':') for x in (
    '01:Ain|02:Aisne|03:Allier|04:Alpes-de-Haute-Provence|05:Hautes-Alpes|06:Alpes-Maritimes|07:Ardèche|08:Ardennes|'
    '09:Ariège|10:Aube|11:Aude|12:Aveyron|13:Bouches-du-Rhône|14:Calvados|15:Cantal|16:Charente|17:Charente-Maritime|'
    '18:Cher|19:Corrèze|2A:Corse-du-Sud|2B:Haute-Corse|21:Côte-d’Or|22:Côtes-d’Armor|23:Creuse|24:Dordogne|25:Doubs|'
    '26:Drôme|27:Eure|28:Eure-et-Loir|29:Finistère|30:Gard|31:Haute-Garonne|32:Gers|33:Gironde|34:Hérault|'
    '35:Ille-et-Vilaine|36:Indre|37:Indre-et-Loire|38:Isère|39:Jura|40:Landes|41:Loir-et-Cher|42:Loire|43:Haute-Loire|'
    '44:Loire-Atlantique|45:Loiret|46:Lot|47:Lot-et-Garonne|48:Lozère|49:Maine-et-Loire|50:Manche|51:Marne|'
    '52:Haute-Marne|53:Mayenne|54:Meurthe-et-Moselle|55:Meuse|56:Morbihan|57:Moselle|58:Nièvre|59:Nord|60:Oise|'
    '61:Orne|62:Pas-de-Calais|63:Puy-de-Dôme|64:Pyrénées-Atlantiques|65:Hautes-Pyrénées|66:Pyrénées-Orientales|'
    '67:Bas-Rhin|68:Haut-Rhin|69:Rhône|70:Haute-Saône|71:Saône-et-Loire|72:Sarthe|73:Savoie|74:Haute-Savoie|75:Paris|'
    '76:Seine-Maritime|77:Seine-et-Marne|78:Yvelines|79:Deux-Sèvres|80:Somme|81:Tarn|82:Tarn-et-Garonne|83:Var|'
    '84:Vaucluse|85:Vendée|86:Vienne|87:Haute-Vienne|88:Vosges|89:Yonne|90:Territoire de Belfort|91:Essonne|'
    '92:Hauts-de-Seine|93:Seine-Saint-Denis|94:Val-de-Marne|95:Val-d’Oise').split('|'))

# Régions de France métropolitaine : (nom, ancre, départements, grandes villes)
REGIONS = [
    ('Auvergne-Rhône-Alpes', 'auvergne-rhone-alpes', '01 03 07 15 26 38 42 43 63 69 73 74',
     ['Lyon', 'Grenoble', 'Saint-Étienne', 'Clermont-Ferrand', 'Annecy', 'Chambéry', 'Valence']),
    ('Bourgogne-Franche-Comté', 'bourgogne-franche-comte', '21 25 39 58 70 71 89 90', ['Dijon', 'Besançon', 'Chalon-sur-Saône']),
    ('Bretagne', 'bretagne', '22 29 35 56', ['Rennes', 'Brest', 'Lorient']),
    ('Centre-Val de Loire', 'centre-val-de-loire', '18 28 36 37 41 45', ['Orléans', 'Tours', 'Bourges']),
    ('Corse', 'corse', '2A 2B', ['Ajaccio', 'Bastia']),
    ('Grand Est', 'grand-est', '08 10 51 52 54 55 57 67 68 88', ['Strasbourg', 'Reims', 'Metz', 'Nancy', 'Mulhouse']),
    ('Hauts-de-France', 'hauts-de-france', '02 59 60 62 80', ['Lille', 'Amiens', 'Dunkerque']),
    ('Île-de-France', 'ile-de-france', '75 77 78 91 92 93 94 95', ['Paris']),
    ('Normandie', 'normandie', '14 27 50 61 76', ['Rouen', 'Caen', 'Le Havre']),
    ('Nouvelle-Aquitaine', 'nouvelle-aquitaine', '16 17 19 23 24 33 40 47 64 79 86 87',
     ['Bordeaux', 'Limoges', 'Poitiers', 'La Rochelle', 'Pau']),
    ('Occitanie', 'occitanie', '09 11 12 30 31 32 34 46 48 65 66 81 82', ['Toulouse', 'Montpellier', 'Nîmes', 'Perpignan']),
    ('Pays de la Loire', 'pays-de-la-loire', '44 49 53 72 85', ['Nantes', 'Angers', 'Le Mans']),
    ('Provence-Alpes-Côte d’Azur', 'provence-alpes-cote-d-azur', '04 05 06 13 83 84',
     ['Marseille', 'Nice', 'Toulon', 'Aix-en-Provence', 'Avignon']),
]
VILLES = json.load(open(os.path.join(SRC, 'pages', 'villes.json'), encoding='utf-8'))
VILLE_PAR_NOM = {v['nom']: v for v in VILLES}
VILLE_PAR_SLUG = {v['slug']: v for v in VILLES}

# Pied de page : colonnes de liens (titre, [(lien, libellé)])
FOOTER_COLS = [
    ('Solutions', [('solutions.html', 'Notre solution cool roof'), ('solutions.html#methode', 'Notre méthode'),
                   ('guide-cool-roof.html', 'Le cool roof, comment ça marche'), ('indice-sri.html', 'Indice SRI'),
                   ('solutions.html#entretien', 'Entretien de la toiture')]),
    ('Toitures', [(f, label) for f, label in SUPPORTS]),
    ('Secteurs', [(s['slug'] + '.html', s['label']) for s in SECTORS]),
    ('Rentabilité et aides', [('rentabilite-cool-roof.html', 'Rentabilité et ROI'),
                              ('rentabilite-cool-roof.html#simulateur', 'Simulateur d’économies'),
                              ('aides-reglementation.html#bat-en-112', 'Prime CEE BAT-EN-112'),
                              ('decret-tertiaire.html', 'Décret tertiaire'),
                              ('chaleur-au-travail.html', 'Chaleur au travail')]),
    ('ALBEDIA', [('qui-sommes-nous.html', 'Qui sommes-nous'), ('zones-intervention.html', 'Zones d’intervention'),
                 ('faq.html', 'Questions fréquentes'), ('particuliers.html', 'Vous êtes un particulier ?'),
                 ('devis.html', 'Demander un devis')]),
]

# Ordre = ordre d'alternance des slogans (0, 1, 0, 1…)
PAGES = [
    dict(file='index.html', src='index.html', title='Cool roof pour toitures professionnelles | ALBEDIA',
         og='ALBEDIA, le cool roof pour les toitures professionnelles',
         desc='ALBEDIA applique des revêtements réfléchissants (cool roof) sur les toitures des entrepôts, usines, commerces et bureaux pour garder les bâtiments plus frais l’été.',
         crumbs=None, nav=None, cta=True, cta_bg='paper'),
    dict(file='guide-cool-roof.html', src='guide-cool-roof.html', title='Le cool roof : principe, albédo, bénéfices et limites | ALBEDIA',
         desc='Comprendre le cool roof : albédo, émissivité, indice SRI, chiffres de référence sourcés, intérêt selon le bâtiment, effet en hiver et entretien.',
         crumbs=[('Le cool roof', None)], nav='solutions', cta=True, cta_bg='paper', cta2=('solutions.html', 'Découvrir nos solutions')),
    dict(file='solutions.html', src='solutions.html', title='Solutions cool roof : diagnostic, application, entretien | ALBEDIA',
         desc='De la visite de toiture à l’entretien : la méthode ALBEDIA pour appliquer un revêtement réfléchissant sur la toiture de votre bâtiment professionnel.',
         crumbs=[('Solutions', None)], nav='solutions', cta=True, cta_bg='paper'),
] + [
    dict(file=s['slug'] + '.html', sector=s['slug'], title=None, desc=None,
         crumbs=[('Secteurs', 'index.html#secteurs'), (s['label'], None)], nav='secteurs', cta=True, cta_bg='paper')
    for s in SECTORS
] + [
    dict(file='aides-reglementation.html', src='aides-reglementation.html', title='Prime CEE BAT-EN-112 et décret tertiaire : aides et réglementation du cool roof | ALBEDIA',
         desc='Conditions de la prime CEE BAT-EN-112 pour les revêtements réflectifs en toiture, objectifs du décret tertiaire et règles techniques à connaître.',
         crumbs=[('Aides et réglementation', None)], nav='rentabilite', cta=True, cta_bg='paper'),
    dict(file='faq.html', src='faq.html', title='Questions fréquentes sur le cool roof | ALBEDIA',
         desc='Gains, hiver, toitures compatibles, durée de vie, entretien, aides : les réponses aux questions les plus fréquentes sur le cool roof.',
         crumbs=[('Questions fréquentes', None)], nav='ressources', cta=True, cta_bg='paper'),
    dict(file='qui-sommes-nous.html', src='qui-sommes-nous.html', title='Qui sommes-nous | ALBEDIA',
         desc='ALBEDIA, spécialiste des toitures réfléchissantes pour les bâtiments professionnels : notre nom, notre mission et notre façon de travailler.',
         crumbs=[('Qui sommes-nous', None)], nav='albedia', cta=True, cta_bg='paper'),
    dict(file='devis.html', src='devis.html', title='Demande de devis cool roof | ALBEDIA',
         desc='Décrivez votre bâtiment et votre toiture : ALBEDIA vous recontacte pour organiser la visite et établir un devis de revêtement réfléchissant.',
         crumbs=[('Demander un devis', None)], nav='devis', cta=False),
    dict(file='mentions-legales.html', src='mentions-legales.html', title='Mentions légales | ALBEDIA',
         desc='Mentions légales du site albedia.eu : éditeur, hébergeur, propriété intellectuelle.',
         crumbs=[('Mentions légales', None)], nav=None, cta=False),
    dict(file='confidentialite.html', src='confidentialite.html', title='Politique de confidentialité | ALBEDIA',
         desc='Comment ALBEDIA traite les données transmises par le formulaire de demande de devis, et comment exercer vos droits.',
         crumbs=[('Confidentialité', None)], nav=None, cta=False),
    dict(file='404.html', src='404.html', title='Page introuvable | ALBEDIA', desc='Cette page n’existe pas ou a été déplacée.',
         crumbs=None, nav=None, cta=False, noindex=True, absolute=True),
    dict(file='rentabilite-cool-roof.html', src='rentabilite-cool-roof.html',
         title='Rentabilité et ROI d’un cool roof : calcul du temps de retour | ALBEDIA',
         desc='Calculez la rentabilité d’une toiture réfléchissante : économies de climatisation, prime CEE, temps de retour et gain sur 20 ans, avec notre calculateur.',
         crumbs=[('Rentabilité et ROI', None)], nav='rentabilite', cta=True, cta_bg='paper',
         cta2=('aides-reglementation.html', 'Voir la prime CEE'), faq='faq-rentabilite.json', prio='0.9'),
    dict(file='cool-roof-bac-acier.html', src='cool-roof-bac-acier.html', faq='faq-bac-acier.json',
         title='Cool roof sur toiture en bac acier | ALBEDIA',
         desc='Revêtement réfléchissant sur bac acier : corrosion, fixations, plaques éclairantes, primaire et application. Ce qu’il faut savoir avant les travaux.',
         crumbs=[('Solutions', 'solutions.html'), ('Toiture en bac acier', None)], nav='solutions', cta=True, cta_bg='paper'),
    dict(file='cool-roof-membrane.html', src='cool-roof-membrane.html', faq='faq-membrane.json',
         title='Cool roof sur membrane PVC, TPO ou EPDM | ALBEDIA',
         desc='Revêtement réfléchissant sur membrane synthétique : compatibilité, essai d’adhérence, garanties et assurance. Nos repères avant d’intervenir.',
         crumbs=[('Solutions', 'solutions.html'), ('Membranes PVC, TPO, EPDM', None)], nav='solutions', cta=True, cta_bg='paper'),
    dict(file='cool-roof-bitume.html', src='cool-roof-bitume.html', faq='faq-bitume.json',
         title='Cool roof sur étanchéité bitumineuse | ALBEDIA',
         desc='Toiture-terrasse en bitume : autoprotection, remontées du bitume, primaire adapté, eaux stagnantes. Comment appliquer un revêtement réfléchissant.',
         crumbs=[('Solutions', 'solutions.html'), ('Étanchéité bitumineuse', None)], nav='solutions', cta=True, cta_bg='paper'),
    dict(file='cool-roof-toit-terrasse-beton.html', src='cool-roof-toit-terrasse-beton.html', faq='faq-beton.json',
         title='Cool roof sur toit-terrasse en béton | ALBEDIA',
         desc='Toit-terrasse en béton : étanchéité existante, gravillons, fissures, humidité, évacuation des eaux. Les étapes pour une toiture plate réfléchissante.',
         crumbs=[('Solutions', 'solutions.html'), ('Toit-terrasse en béton', None)], nav='solutions', cta=True, cta_bg='paper'),
    dict(file='cool-roof-fibres-ciment.html', src='cool-roof-fibres-ciment.html', faq='faq-fibres-ciment.json',
         title='Cool roof sur plaques en fibres-ciment : amiante et sécurité | ALBEDIA',
         desc='Toiture en fibres-ciment : repérage de l’amiante, travaux en sous-section 4, toiture fragile et protection contre les chutes, étapes d’application.',
         crumbs=[('Solutions', 'solutions.html'), ('Fibres-ciment', None)], nav='solutions', cta=True, cta_bg='paper'),
    dict(file='decret-tertiaire.html', src='decret-tertiaire.html', faq='faq-decret-tertiaire.json',
         title='Décret tertiaire : objectifs, OPERAT et rôle du cool roof | ALBEDIA',
         desc='Éco Énergie Tertiaire : bâtiments concernés, objectif de −40 % en 2030, déclaration OPERAT, sanctions, et place d’une toiture réfléchissante.',
         crumbs=[('Décret tertiaire', None)], nav='ressources', cta=True, cta_bg='paper',
         cta2=('rentabilite-cool-roof.html', 'Calculer la rentabilité')),
    dict(file='chaleur-au-travail.html', src='chaleur-au-travail.html', faq='faq-chaleur.json',
         title='Chaleur au travail : obligations de l’employeur | ALBEDIA',
         desc='Décret du 27 mai 2025 : épisodes de chaleur intense, évaluation des risques, mesures de prévention et aménagement des lieux de travail.',
         crumbs=[('Chaleur au travail', None)], nav='ressources', cta=True, cta_bg='paper'),
    dict(file='indice-sri.html', src='indice-sri.html',
         title='Indice SRI, réflectance et émissivité d’une toiture | ALBEDIA',
         desc='L’indice SRI expliqué : norme ASTM E1980, réflectance, émissivité, valeurs à neuf et vieillies, seuils de la prime CEE, lecture d’une fiche technique.',
         crumbs=[('Solutions', 'solutions.html'), ('Indice SRI', None)], nav='solutions', cta=True, cta_bg='paper'),
    dict(file='cool-roof-photovoltaique.html', src='cool-roof-photovoltaique.html', faq='faq-photovoltaique.json',
         title='Cool roof et toiture photovoltaïque : panneaux et revêtement réfléchissant | ALBEDIA',
         desc='Toiture équipée de panneaux solaires : revêtement réfléchissant entre les rangées, gain des modules bifaciaux, obligation de solarisation et précautions de chantier.',
         crumbs=[('Solutions', 'solutions.html'), ('Toitures photovoltaïques', None)], nav='solutions', cta=True, cta_bg='paper'),
    dict(file='particuliers.html', src='particuliers.html',
         title='Particuliers : à qui vous adresser pour votre toiture ? | ALBEDIA',
         desc='ALBEDIA intervient sur les bâtiments professionnels. Pour votre maison, France Rénov’, le service public de la rénovation, vous conseille gratuitement.',
         crumbs=[('Vous êtes un particulier ?', None)], nav='albedia', cta=False),
    dict(file='zones-intervention.html', src='zones-intervention.html',
         title='Zones d’intervention : France, Suisse, Italie, Espagne | ALBEDIA',
         desc='ALBEDIA intervient sur les toitures professionnelles en France, en Suisse, en Italie et en Espagne : zones climatiques, aides et règles de chaque pays.',
         crumbs=[('Zones d’intervention', None)], nav='albedia', cta=True, cta_bg='paper'),
]
PAGES += [
    dict(file='cool-roof-%s.html' % v['slug'], city=v['slug'],
         title='Cool roof à %s : toitures réfléchissantes | ALBEDIA' % v['nom'],
         desc=('Revêtement réfléchissant pour les toitures des entrepôts, usines, commerces et bureaux de %s (%s) : zone climatique %s, prime CEE, simulation des économies.'
               % (v['nom'], v['dept'][0], v['zone'])) if v['pays'] == 'FR' else
              ('Revêtement réfléchissant pour les toitures des bâtiments professionnels de %s (canton de %s) : climat, règles cantonales et étude de votre toiture.'
               % (v['nom'], v['canton'])),
         crumbs=[('Zones d’intervention', 'zones-intervention.html'), (v['nom'], None)], nav='albedia', cta=True, cta_bg='paper')
    for v in VILLES]
for i, p in enumerate(PAGES):
    p['slogan'] = SLOGANS[i % 2]

SECTOR_DATA = json.load(open(os.path.join(SRC, 'pages', 'secteurs.json'), encoding='utf-8'))
# Photos (Unsplash, licence Unsplash) : texte alternatif, cadrage, largeurs disponibles, auteur.
# Fichiers WebP dans assets/img/photos/<slug>-<largeur>.webp
PHOTOS = json.load(open(os.path.join(SRC, 'pages', 'photos.json'), encoding='utf-8'))

# ------------------------------------------------------------------ versions anglaise, italienne et espagnole
# Pour chaque langue, _src/i18n/<langue>/ contient : ui.json (textes communs, menus, pied de page, titres et
# descriptions des pages traduites, libellés des secteurs, textes alternatifs des photos), secteurs.json (pages
# secteur), faq-*.json, js.json (textes du simulateur et des formulaires, lus par main.js), simulateur.html et
# pages/*.html (contenu des pages). Les pages traduites sont publiées dans /en/, /it/ et /es/.
I18N_DIR = os.path.join(SRC, 'i18n')
I18N_LANGS = tuple(l for l in ('en', 'it', 'es') if os.path.isfile(os.path.join(I18N_DIR, l, 'ui.json')))
UI = {l: json.load(open(os.path.join(I18N_DIR, l, 'ui.json'), encoding='utf-8')) for l in I18N_LANGS}
I18N_SECTORS = {l: json.load(open(os.path.join(I18N_DIR, l, 'secteurs.json'), encoding='utf-8')) for l in I18N_LANGS}
TRANSLATED = tuple(UI[I18N_LANGS[0]]['pages'].keys()) if I18N_LANGS else ()   # pages qui ont une version traduite


def _lang_pages():
    out = []
    slugs = {x['slug'] for x in SECTORS}
    for l in I18N_LANGS:
        for i, (f, meta) in enumerate(UI[l]['pages'].items()):
            fr = next(x for x in PAGES if x['file'] == f)
            pg = dict(file=f, lang=l, src=f, nav=fr.get('nav'), cta=fr.get('cta'), cta_bg=fr.get('cta_bg', 'paper'),
                      crumbs=[tuple(c) for c in meta['crumbs']] if meta.get('crumbs') else None,
                      title=meta.get('title'), desc=meta.get('desc'), og=meta.get('og'), faq=meta.get('faq'),
                      prio=fr.get('prio'), slogan=UI[l]['slogans'][i % 2])
            if meta.get('cta2'):
                pg['cta2'] = tuple(meta['cta2'])
            if f[:-5] in slugs:
                pg['sector'] = f[:-5]
            out.append(pg)
    return out


LANG_PAGES = _lang_pages()


def T(ctx, key):
    """Texte commun dans la langue de la page (les pages françaises gardent leurs textes d'origine)."""
    return UI[ctx.lang][key]

# ------------------------------------------------------------------ helpers
PART = os.path.join(SRC, 'partials')


def part(name):
    return open(os.path.join(PART, name), encoding='utf-8').read()


def icon(name):
    return part(os.path.join('icons', name + '.svg'))


def esc(t):
    return html.escape(t, quote=True)


def typo(markup, lang='fr'):
    """Typographie française sur les nœuds texte (hors script, style et balises), pages françaises seulement."""
    if lang != 'fr':
        return markup
    out, skip = [], False
    for chunk in re.split(r'(<[^>]+>)', markup):
        if chunk.startswith('<'):
            tag = chunk[1:].split()[0].lower().rstrip('>') if len(chunk) > 1 else ''
            if tag in ('script', 'style'):
                skip = True
            elif tag in ('/script', '/style'):
                skip = False
            out.append(chunk)
            continue
        if not skip and chunk:
            c = re.sub(r' ([:;!?»])', '\u00a0\\1', chunk)
            c = re.sub(r'« ', '«\u00a0', c)
            c = re.sub(r'(\d) (?=\d{3}\b)', '\\1\u00a0', c)
            c = re.sub(r'(\d) (%|°C|°|€|m²|kWh|ans\b|heures\b|°F)', '\\1\u00a0\\2', c)
            c = re.sub(r'\b(n°|N°) ', '\\1\u00a0', c)
            chunk = c
        out.append(chunk)
    return ''.join(out)


def todo(text):
    return '<span class="a-completer">[%s]</span>' % text


SIZES_HALF = '(max-width: 880px) 100vw, 580px'


def photo(slug, ctx, sizes=SIZES_HALF, cls='', eager=False, alt=None):
    """Balise <img> responsive (WebP en plusieurs largeurs) pour une photo du registre."""
    p = PHOTOS[slug]
    base = '%sassets/img/photos/%s' % (ctx.prefix, slug)
    widths = p['widths']
    srcset = ', '.join('%s-%d.webp %dw' % (base, w, w) for w in widths)
    default = min(widths, key=lambda w: abs(w - 1280))
    w, h = p['ratio']
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return '<img%s src="%s-%d.webp" srcset="%s" sizes="%s" width="%d" height="%d" alt="%s" data-photo="%s" %s decoding="async">' % (
        ' class="%s"' % cls if cls else '', base, default, srcset, sizes, w, h,
        esc((p['alt'] if ctx.lang == 'fr' else UI[ctx.lang]['alts'].get(slug, p['alt'])) if alt is None else alt), slug, load)


def photo_css():
    """Cadrage de chaque photo (object-position), ajouté à la feuille de style au build."""
    rules = ['[data-photo="%s"] { object-position: %s; }' % (s, p['pos']) for s, p in PHOTOS.items()
             if p.get('pos') and p['pos'] != '50% 50%']
    return '\n/* ---------------------------------------------------------------- cadrage des photos (généré) */\n' + '\n'.join(rules) + '\n'


def photo_credits():
    items = []
    for slug, p in PHOTOS.items():
        items.append('<li>%s : photo de <a href="%s" rel="noopener" target="_blank">%s</a> sur <a href="%s" rel="noopener" target="_blank">Unsplash</a></li>' % (
            esc(p['alt']), p['author_url'], esc(p['author']), p['url']))
    return '<ul class="credits">%s</ul>' % ''.join(items)


def lang_url(ctx, lang, f):
    """Lien relatif vers la version <lang> de la page f (« fr » : la page d'origine)."""
    target = ('../' if ctx.lang != 'fr' else '') + ('' if lang == 'fr' else lang + '/') + ('' if f == 'index.html' else f)
    if ctx.variant == 'preview' and (target == '' or target.endswith('/')):
        target += 'index.html'
    return target or './'


LANG_NAMES = {'fr': 'Français', 'en': 'English', 'it': 'Italiano', 'es': 'Español'}


def lang_switch(ctx):
    f = ctx.page['file']
    if f in TRANSLATED:
        # page traduite : liens vers les vraies versions de la page dans chaque langue
        items = []
        for code in ('fr',) + I18N_LANGS:
            if code == ctx.lang:
                items.append('<span class="lang-cur" lang="%s" aria-current="true" title="%s">%s</span>' % (code, LANG_NAMES[code], code.upper()))
            else:
                items.append('<a class="lang-link" href="%s" lang="%s" hreflang="%s" title="%s"><span aria-hidden="true">%s</span>'
                             '<span class="visually-hidden">%s</span></a>' % (lang_url(ctx, code, f), code, code, LANG_NAMES[code], code.upper(), LANG_NAMES[code]))
        aria = 'Langue du site' if ctx.lang == 'fr' else T(ctx, 'lang_aria')
        return '<div class="lang notranslate" translate="no" role="group" aria-label="%s">%s</div>' % (esc(aria), ''.join(items))
    page_url = SITE_URL + '/' + ('' if ctx.page['file'] in ('index.html', '404.html') else ctx.page['file'])
    links = ''.join(
        '<a class="lang-link" href="https://translate.google.com/translate?sl=fr&amp;tl=%s&amp;hl=%s&amp;u=%s" lang="%s" hreflang="%s" rel="nofollow" title="%s"><span aria-hidden="true">%s</span><span class="visually-hidden">%s</span></a>' % (
            code, code, quote(page_url, safe=''), code, code, esc(title), short, esc(label))
        for code, short, label, title in LANGS)
    # translate="no" : Google Traduction ne doit pas traduire les codes de langue (« EN » deviendrait « IN »)
    return '<div class="lang notranslate" translate="no" role="group" aria-label="Langue du site"><span class="lang-cur" lang="fr" aria-current="true" title="Français">FR</span>%s</div>' % links


class Ctx:
    def __init__(self, variant, page):
        self.variant, self.page = variant, page
        self.lang = page.get('lang', 'fr')
        if self.lang != 'fr':
            self.prefix = '../'   # pages traduites : un dossier par langue
        else:
            self.prefix = '/' if page.get('absolute') and variant == 'site' else ''

    def href(self, target):
        if self.lang != 'fr':
            # page traduite : même dossier si la page existe dans la langue, sinon la page française
            if target in ('', 'index.html'):
                return 'index.html' if self.variant == 'preview' else './'
            return target if target in TRANSLATED else '../' + target
        if target in ('', 'index.html'):
            if self.variant == 'preview':
                return 'index.html'
            return self.prefix if self.prefix else './'
        return self.prefix + target


def expand(text, ctx):
    page = ctx.page

    def repl(m):
        key = m.group(1)
        if key == 'SLOGAN':
            return page['slogan']
        if key == 'SUN':
            return part('sun.svg')
        if key == 'EYEBROW':
            return '<p class="slogan">%s%s</p>' % (part('sun.svg'), page['slogan'])
        if key == 'EMAIL':
            return EMAIL
        if key == 'EMAIL_LINK':
            return '<a href="mailto:%s">%s</a>' % (EMAIL, EMAIL)
        if key == 'PHONE':
            return PHONE if PHONE else todo('Téléphone')
        if key == 'PHONE_LINK':
            return '<a href="tel:%s">%s</a>' % (PHONE_TEL, PHONE) if PHONE else todo('Téléphone')
        if key == 'PREVIEW_ATTR':
            return ' data-preview="1"' if ctx.variant == 'preview' else ''
        if key == 'BREADCRUMB':
            return breadcrumb(ctx)
        if key == 'SECTOR_TILES':
            return sector_tiles(ctx)
        if key == 'SECTOR_OPTIONS':
            return sector_options(ctx)
        if key == 'PHOTO_CREDITS':
            return photo_credits()
        if key == 'AREA':
            return AREA if ctx.lang == 'fr' else T(ctx, 'area')
        if key == 'REGIONS':
            return regions_html()
        if key == 'VILLES':
            return villes_html()
        if key == 'CARTE_ZONES':
            return carte_zones(ctx)
        if key == 'PLAQUETTE_HREF':
            return plaquette_href()
        if key == 'PLAQUETTE_ATTR':
            return PLAQUETTE_ATTR
        if key == 'PLAQUETTE_TAILLE':
            return plaquette_taille(ctx.lang)
        if key.startswith('img:'):
            slug, _, sizes = key[4:].partition('|')
            return photo(slug, ctx, sizes or SIZES_HALF)
        if key.startswith('bg:'):
            return photo(key[3:], ctx, '100vw', cls='bg', eager=True, alt='')
        if key.startswith('bg-lazy:'):
            return photo(key[8:], ctx, '100vw', cls='bg', alt='')
        if key.startswith('icon:'):
            return icon(key[5:])
        if key.startswith('include:'):
            return part(key[8:])
        if key.startswith('TODO:'):
            return todo(key[5:])
        if key.startswith('href:'):
            return ctx.href(key[5:])
        raise KeyError(key)
    text = re.sub(r'\{\{([^{}]+)\}\}', repl, text)
    # liens internes relatifs → préfixe (page 404) / accueil
    text = re.sub(r'href="([a-z0-9-]+\.html)(#[^"]*)?"', lambda m: 'href="%s%s"' % (ctx.href(m.group(1)), m.group(2) or ''), text)
    text = re.sub(r'action="(devis\.html|contact\.php|simulation\.php)"', lambda m: 'action="%s"' % (
        ctx.href(m.group(1)) if m.group(1) == 'devis.html' else ctx.prefix + m.group(1)), text)
    text = re.sub(r'(href|src)="(assets/(?:docs|img)/[^"]+)"', lambda m: '%s="%s%s"' % (m.group(1), ctx.prefix, m.group(2)), text)
    return text


SECTOR_CHOICES = ['Industrie', 'Logistique et entreposage', 'Commerce et distribution', 'Bureaux et tertiaire',
                  'Collectivité ou équipement public', 'Agricole', 'Autre']


def sector_options(ctx=None):
    if ctx is not None and ctx.lang != 'fr':
        # valeurs en français (attendues par contact.php), libellés traduits
        return '<option value="">%s</option>' % esc(T(ctx, 'choose')) + ''.join(
            '<option value="%s">%s</option>' % (esc(v), esc(l)) for v, l in zip(SECTOR_CHOICES, T(ctx, 'sector_choices')))
    return '<option value="">Choisir…</option>' + ''.join('<option>%s</option>' % esc(c) for c in SECTOR_CHOICES)


def sector_tiles(ctx):
    sizes = '(max-width: 580px) 100vw, (max-width: 960px) 50vw, 380px'
    return ''.join(
        '<a class="tile" href="%s.html"><span class="tile-media">%s</span>'
        '<span class="tile-body"><span class="tile-ico">%s</span><span class="tile-text"><strong>%s</strong><span>%s</span></span>%s</span></a>' % (
            s['slug'], photo(s['photo'], ctx, sizes, alt=''), icon(s['icon']),
            esc(s['label'] if ctx.lang == 'fr' else T(ctx, 'sectors')[s['slug']][0]),
            esc(s['short'] if ctx.lang == 'fr' else T(ctx, 'sectors')[s['slug']][1]), icon('fleche'))
        for s in SECTORS)


def breadcrumb(ctx):
    crumbs = ctx.page.get('crumbs') or []
    items = ['<li><a href="index.html">%s</a></li>' % ('Accueil' if ctx.lang == 'fr' else esc(T(ctx, 'home')))]
    for i, (label, link) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        if last:
            items.append('<li><span aria-current="page">%s</span></li>' % esc(label))
        elif link:
            items.append('<li><a href="%s">%s</a></li>' % (link, esc(label)))
        else:
            items.append('<li><span>%s</span></li>' % esc(label))
    aria = 'Fil d’Ariane' if ctx.lang == 'fr' else T(ctx, 'breadcrumb_aria')
    return '<nav class="breadcrumb" aria-label="%s"><ol>%s</ol></nav>' % (esc(aria), ''.join(items))


# ------------------------------------------------------------------ gabarits communs
# Signature sous le logo, justifiée sur la largeur du mot « albedia » : même repère horizontal que le
# viewBox du logo (x de 2 à 656), texte étiré de x = 6 à x = 651,8 (bords des lettres) par textLength.
def brand(ctx=None):
    fr = ctx is None or ctx.lang == 'fr'
    return ('<a class="brand" href="index.html" aria-label="%s">%s'
            '<svg class="brand-tag" viewBox="2 0 654 49.5" aria-hidden="true" focusable="false">'
            '<text x="6" y="38.6" textLength="645.8" lengthAdjust="spacing">%s</text></svg></a>') % (
        'ALBEDIA, accueil' if fr else esc(T(ctx, 'brand_aria')), part('logo.svg'), BASELINE if fr else T(ctx, 'baseline'))


def menus(ctx):
    page = ctx.page
    out = []
    for key, label, items in (MENUS if ctx.lang == 'fr' else T(ctx, 'menus')):
        lis = []
        for item in items:
            if item[0] == '-':
                lis.append('<li class="sub-head">%s</li>' % esc(item[1]))
                continue
            href, ic, lab = item
            cur = ' aria-current="page"' if href == page['file'] else ''
            if href == PLAQUETTE:
                href, cur = plaquette_href(), PLAQUETTE_ATTR
            lis.append('<li><a href="%s"%s>%s<span>%s</span></a></li>' % (href, cur, icon(ic), esc(lab)))
        is_cur = ' is-current' if page.get('nav') == key else ''
        out.append('<li class="has-sub"><button class="nav-toggle-sub%s" type="button" aria-expanded="false" aria-controls="sub-%s">%s%s</button>\n'
                   '<ul class="sub" id="sub-%s">%s</ul></li>' % (is_cur, key, esc(label), icon('chevron'), key, ''.join(lis)))
    return '\n'.join(out)


def header(ctx):
    devis_cur = ' aria-current="page"' if ctx.page.get('nav') == 'devis' else ''
    fr = ctx.lang == 'fr'
    skip, nav_aria = ('Aller au contenu', 'Navigation principale') if fr else (T(ctx, 'skip'), T(ctx, 'nav_aria'))
    quote, menu = ('Demander un devis', 'Menu') if fr else (T(ctx, 'quote'), T(ctx, 'menu'))
    return f'''<a class="skip" href="#contenu">{skip}</a>
<header class="site-header">
<div class="wrap">
{brand(ctx)}
<nav class="nav" id="nav-principale" aria-label="{nav_aria}">
<ul class="nav-list">
{menus(ctx)}
</ul>
<a class="btn btn--sun btn--sm nav-cta" href="devis.html"{devis_cur}>{quote}</a>
</nav>
{lang_switch(ctx)}
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav-principale">{icon('menu')}<span>{menu}</span></button>
</div>
</header>'''


def cta_band(ctx):
    page = ctx.page
    if ctx.lang != 'fr':
        return cta_band_i18n(ctx)
    href2, label2 = page.get('cta2', ('guide-cool-roof.html', 'Lire le guide du cool roof'))
    return f'''<div class="cta-outer cta-outer--{page.get('cta_bg', 'paper')}">
<section class="cta-band" aria-labelledby="cta-titre">
<div class="wrap">
{part('sun.svg').replace('class="sun"', 'class="sun sun--xl"')}
<h2 class="cta-slogan" id="cta-titre">{page['slogan']}</h2>
<p>Parlez-nous de votre bâtiment : surface, type de toiture, usage. Nous revenons vers vous pour organiser la visite de la toiture.</p>
<div class="cta-actions"><a class="btn btn--sun" href="devis.html">Demander un devis{icon('fleche')}</a><a class="btn btn--line" href="{href2}">{label2}</a></div>
<p class="cta-contact">Ou contactez-nous : <a href="mailto:{EMAIL}">{EMAIL}</a>{(' · <a href="tel:%s">%s</a>' % (PHONE_TEL, PHONE)) if PHONE else ''}</p>
<p class="cta-contact cta-doc"><a href="{plaquette_href()}"{PLAQUETTE_ATTR}>{icon('document')}Télécharger notre plaquette ({plaquette_taille()})</a></p>
</div>
</section>
</div>'''


def footer(ctx):
    if ctx.lang != 'fr':
        return footer_i18n(ctx)
    phone = ('<p class="footer-contact">%s<a href="tel:%s">%s</a></p>' % (icon('tel'), PHONE_TEL, PHONE)) if PHONE else ''
    cols = '\n'.join('<nav class="footer-col" aria-label="%s"><h2>%s</h2><ul>%s</ul></nav>' % (
        esc(title), esc(title), ''.join('<li><a href="%s">%s</a></li>' % (href, esc(label)) for href, label in links))
        for title, links in FOOTER_COLS)
    return f'''<footer class="site-footer">
<div class="wrap">
<div class="footer-top">
<div class="footer-brand">
{brand()}
<p>Revêtements réfléchissants (cool roof) pour les toitures des bâtiments professionnels, {AREA}.</p>
<p class="footer-contact">{icon('mail')}<a href="mailto:{EMAIL}">{EMAIL}</a></p>
{phone}
<p class="footer-contact">{icon('lieu')}<a href="zones-intervention.html">France · Suisse · Italie · Espagne</a></p>
<p class="footer-contact">{icon('document')}<a href="{plaquette_href()}"{PLAQUETTE_ATTR}>Plaquette de présentation (PDF)</a></p>
</div>
{cols}
</div>
<nav class="footer-cities" aria-labelledby="pied-villes"><h2 id="pied-villes">Le cool roof par ville</h2>
<ul>{''.join('<li><a href="cool-roof-%s.html">%s</a></li>' % (v['slug'], esc(v['nom'])) for v in VILLES)}<li><a href="zones-intervention.html#regions">Toutes les régions</a></li></ul></nav>
<div class="footer-bottom"><p>© 2026 ALBEDIA, marque déposée exploitée par CGBI, filiale de GROUPE NOVELIA.</p>
<ul class="footer-legal"><li><a href="mentions-legales.html">Mentions légales</a></li><li><a href="confidentialite.html">Confidentialité</a></li><li>Ce site ne dépose aucun cookie.</li></ul></div>
</div>
</footer>'''


def cta_band_i18n(ctx):
    page = ctx.page
    href2, label2 = page.get('cta2') or tuple(T(ctx, 'cta2'))
    tel = (' · <a href="tel:%s">%s</a>' % (PHONE_TEL, PHONE)) if PHONE else ''
    return f'''<div class="cta-outer cta-outer--{page.get('cta_bg', 'paper')}">
<section class="cta-band" aria-labelledby="cta-titre">
<div class="wrap">
{part('sun.svg').replace('class="sun"', 'class="sun sun--xl"')}
<h2 class="cta-slogan" id="cta-titre">{page['slogan']}</h2>
<p>{T(ctx, 'cta_text')}</p>
<div class="cta-actions"><a class="btn btn--sun" href="devis.html">{T(ctx, 'quote')}{icon('fleche')}</a><a class="btn btn--line" href="{href2}">{label2}</a></div>
<p class="cta-contact">{T(ctx, 'cta_contact')} <a href="mailto:{EMAIL}">{EMAIL}</a>{tel}</p>
<p class="cta-contact cta-doc"><a href="{plaquette_href()}"{PLAQUETTE_ATTR} hreflang="fr">{icon('document')}{T(ctx, 'brochure').replace('{size}', plaquette_taille(ctx.lang))}</a></p>
</div>
</section>
</div>'''


def footer_i18n(ctx):
    phone = ('<p class="footer-contact">%s<a href="tel:%s">%s</a></p>' % (icon('tel'), PHONE_TEL, PHONE)) if PHONE else ''

    def col_links(links):
        if links == 'LANGS':   # colonne « Langues » : accueil du site dans les autres langues
            return ''.join('<li><a href="%s" lang="%s" hreflang="%s">%s</a></li>' % (lang_url(ctx, code, 'index.html'), code, code, LANG_NAMES[code])
                           for code in ('fr',) + I18N_LANGS if code != ctx.lang)
        return ''.join('<li><a href="%s">%s</a></li>' % (href, esc(label)) for href, label in links)
    cols = '\n'.join('<nav class="footer-col" aria-label="%s"><h2>%s</h2><ul>%s</ul></nav>' % (
        esc(title), esc(title), col_links(links)) for title, links in T(ctx, 'footer_cols'))
    legal = ''.join('<li><a href="%s" hreflang="fr">%s</a></li>' % (h, esc(l)) for h, l in T(ctx, 'legal_links'))
    return f'''<footer class="site-footer">
<div class="wrap">
<div class="footer-top">
<div class="footer-brand">
{brand(ctx)}
<p>{T(ctx, 'footer_desc').replace('{area}', T(ctx, 'area'))}</p>
<p class="footer-contact">{icon('mail')}<a href="mailto:{EMAIL}">{EMAIL}</a></p>
{phone}
<p class="footer-contact">{icon('lieu')}<a href="zones-intervention.html">{T(ctx, 'countries')}</a></p>
<p class="footer-contact">{icon('document')}<a href="{plaquette_href()}"{PLAQUETTE_ATTR} hreflang="fr">{T(ctx, 'brochure_short')}</a></p>
</div>
{cols}
</div>
<div class="footer-bottom"><p>{T(ctx, 'footer_copy')}</p>
<ul class="footer-legal">{legal}<li>{T(ctx, 'nocookie')}</li></ul></div>
</div>
</footer>'''


# ------------------------------------------------------------------ pages secteur
SECTOR_TPL_FR = dict(
    quote='Demander un devis', understand='Comprendre le cool roof', enjeux='Les enjeux', batiments='Bâtiments concernés',
    gain_kicker='Ce que vous y gagnez', gain_title='Ce que le cool roof vous apporte', points_kicker='Avant les travaux',
    points_title='Les points que nous étudions',
    points_text='Chaque bâtiment a ses contraintes. La visite de la toiture sert à les relever avant de vous proposer un procédé et un devis.',
    method='Voir notre méthode', aides_kicker='Aides et obligations', aides_title='Ce qui peut s’appliquer à votre bâtiment',
    link1=['aides-reglementation.html', 'Aides CEE et réglementation'], link2=['rentabilite-cool-roof.html', 'Rentabilité et temps de retour'],
    others='Autres secteurs')


def sector_page(slug, ctx=None):
    fr = ctx is None or ctx.lang == 'fr'
    d = SECTOR_DATA[slug] if fr else I18N_SECTORS[ctx.lang][slug]
    t = SECTOR_TPL_FR if fr else T(ctx, 'sector_tpl')
    label = (lambda o: o['label']) if fr else (lambda o: T(ctx, 'sectors')[o['slug']][0])
    s = next(x for x in SECTORS if x['slug'] == slug)
    bats = ''.join('<li>%s<span>%s</span></li>' % ('{{icon:check}}', esc(b)) for b in d['batiments'])
    bens = ''.join('<div class="feature"><span class="ico-badge">{{icon:%s}}</span><h3>%s</h3><p>%s</p></div>' % (
        ic, esc(t), esc(p)) for ic, t, p in d['benefices'])
    pts = ''.join('<li>{{icon:loupe}}<span>%s</span></li>' % esc(p) for p in d['points'])
    others = ''.join('<li><a class="chip" href="%s.html">{{icon:%s}}%s</a></li>' % (o['slug'], o['icon'], esc(label(o)))
                     for o in SECTORS if o['slug'] != slug)
    enjeux = ''.join('<p>%s</p>' % esc(p) for p in d['enjeux'])
    return f'''<section class="page-head page-head--photo page-head--sector">
{{{{bg:{s['photo']}}}}}
<div class="wrap">
{{{{BREADCRUMB}}}}
<span class="badge-ico">{{{{icon:{s['icon']}}}}}</span>
{{{{EYEBROW}}}}
<h1>{esc(d['h1'])}</h1>
<p class="lead">{esc(d['lead'])}</p>
<div class="hero-actions"><a class="btn btn--sun" href="devis.html">{t['quote']}{{{{icon:fleche}}}}</a><a class="btn btn--light" href="guide-cool-roof.html">{t['understand']}</a></div>
</div>
</section>
<section class="band" aria-labelledby="enjeux-titre">
<div class="wrap split split--top split--media">
<div class="prose">
<p class="kicker">{t['enjeux']}</p>
<h2 id="enjeux-titre">{esc(d['enjeux_titre'])}</h2>
{enjeux}
<h3 id="batiments-titre">{t['batiments']}</h3>
<ul class="checklist checklist--cols">{bats}</ul>
</div>
<figure class="photo photo--tall">{{{{img:{s['photo2']}}}}}</figure>
</div>
</section>
<section class="band band--tint" aria-labelledby="apports-titre">
<div class="wrap">
<div class="section-head">
<p class="kicker">{t['gain_kicker']}</p>
<h2 id="apports-titre">{t['gain_title']}</h2>
</div>
<div class="grid-3">{bens}</div>
</div>
</section>
<section class="band" aria-labelledby="points-titre">
<div class="wrap split split--top">
<div class="prose">
<p class="kicker">{t['points_kicker']}</p>
<h2 id="points-titre">{t['points_title']}</h2>
<p>{t['points_text']}</p>
<a class="link-arrow" href="solutions.html#methode">{t['method']}{{{{icon:fleche}}}}</a>
</div>
<ul class="checklist checklist--points">{pts}</ul>
</div>
</section>
<section class="band band--tint" aria-labelledby="aides-titre">
<div class="wrap split split--top">
<div class="prose">
<p class="kicker">{t['aides_kicker']}</p>
<h2 id="aides-titre">{t['aides_title']}</h2>
<p>{esc(d['aides'])}</p>
<a class="link-arrow" href="{t['link1'][0]}">{t['link1'][1]}{{{{icon:fleche}}}}</a>
<a class="link-arrow" href="{t['link2'][0]}">{t['link2'][1]}{{{{icon:fleche}}}}</a>
</div>
<nav class="others" aria-labelledby="autres-titre">
<h3 id="autres-titre">{t['others']}</h3>
<ul class="chips">{others}</ul>
</nav>
</div>
</section>
'''


# ------------------------------------------------------------------ pages ville et zones
def fmt_int(n):
    return '{:,}'.format(int(round(n))).replace(',', '\u00a0')


def arrondi(x):
    """Arrondis identiques à ceux du simulateur."""
    if x >= 100000:
        return round(x / 1000) * 1000
    if x >= 10000:
        return round(x / 100) * 100
    if x >= 1000:
        return round(x / 10) * 10
    return round(x)


def cee_1000(zone):
    """Prime BAT-EN-112 estimée pour 1 000 m² de toiture, au prix de référence."""
    return arrondi(1000 * CEE_KWHC[zone] / 1000 * CEE_PRIX)


def city_chip(v):
    # icône insérée directement : cette liste est aussi produite par la balise {{VILLES}}, après l'expansion
    return '<li><a class="chip" href="cool-roof-%s.html">%s%s</a></li>' % (v['slug'], icon('lieu'), esc(v['nom']))


def villes_html():
    fr = ''.join(city_chip(v) for v in VILLES if v['pays'] == 'FR')
    ch = ''.join(city_chip(v) for v in VILLES if v['pays'] == 'CH')
    return ('<h3 class="villes-titre">France</h3><ul class="chips">%s</ul>'
            '<h3 class="villes-titre">Suisse romande</h3><ul class="chips">%s</ul>') % (fr, ch)


def regions_html():
    out = []
    for nom, ancre, deps, villes in REGIONS:
        deps = deps.split()
        zones = sorted({zone_of(d) for d in deps})
        dl = ' · '.join('%s <span class="dep-n">%s</span>' % (esc(DEPTS[d]), d) for d in deps)
        vl = ', '.join('<a href="cool-roof-%s.html">%s</a>' % (VILLE_PAR_NOM[x]['slug'], esc(x)) if x in VILLE_PAR_NOM else esc(x)
                       for x in villes)
        if len(zones) > 1:
            detail = ' ; '.join('%s : %s' % (z, ', '.join(d for d in deps if zone_of(d) == z)) for z in zones)
            zl = 'Zones climatiques %s et %s (%s)' % (', '.join(zones[:-1]), zones[-1], detail)
        else:
            zl = 'Zone climatique %s' % zones[0]
        out.append('<article class="region" id="%s"><h3>%s</h3><p class="region-zones">%s</p>'
                   '<p class="region-deps">%s</p><p class="region-villes"><strong>Grandes villes :</strong> %s</p></article>' % (
                       ancre, esc(nom), zl, dl, vl))
    return '<div class="regions">%s</div>' % ''.join(out)


def carte_zones(ctx=None):
    """Carte des zones climatiques CEE par département (balise {{CARTE_ZONES}}, page Zones d'intervention).
    Tracés : partials/carte-departements.json, produit par _src/carte.py. Noms et zones : DEPTS et zone_of().
    Pages traduites : textes de la clé « carte » de ui.json."""
    carte = json.loads(part('carte-departements.json'))
    enc = carte['encart']
    c = UI[ctx.lang]['carte'] if ctx is not None and ctx.lang != 'fr' else dict(
        aria='Carte des départements de France métropolitaine, colorés selon leur zone climatique CEE (H1, H2 ou H3). '
             'La zone de chaque département figure aussi dans la liste des régions, plus bas.',
        zone='Zone {z}', deps='{n} départements', prime='Prime BAT-EN-112 : {k} kWh cumac par\u00a0m²',
        hover='Passez le curseur sur un département pour afficher sa zone.',
        touch='Touchez un département pour afficher sa zone.',
        inset='Paris et la petite couronne sont agrandis dans l’encadré, en haut à gauche.')

    def dep(code, d):
        return '<path data-d="%s" data-z="%s" data-n="%s" d="%s"/>' % (code, zone_of(code), esc(DEPTS[code]), d)

    def rect(cls, r, rx):
        return '<rect class="%s" x="%d" y="%d" width="%d" height="%d" rx="%d"/>' % (cls, r[0], r[1], r[2], r[3], rx)

    svg = ('<svg viewBox="%s" fill-rule="evenodd" role="img" aria-label="%s">'
           '<g class="carte-deps">%s</g>%s<g class="carte-encart">%s%s</g></svg>') % (
        carte['viewBox'], esc(c['aria']), ''.join(dep(k, d) for k, d in carte['paths'].items()),
        rect('carte-repere', enc['repere'], 3), rect('carte-cadre', enc['cadre'], 8),
        ''.join(dep(k, d) for k, d in enc['paths'].items()))
    zones = ('H1', 'H2', 'H3')
    nb = {z: sum(1 for d in DEPTS if zone_of(d) == z) for z in zones}
    legende = ''.join(
        '<li data-zone="%s"><span class="carte-pastille" aria-hidden="true"></span><span class="carte-l"><strong>%s</strong>'
        '<em>%s</em><small>%s</small></span></li>' % (
            z, c['zone'].replace('{z}', z), c['deps'].replace('{n}', str(nb[z])), c['prime'].replace('{k}', str(CEE_KWHC[z])))
        for z in zones)
    return ('<div class="zones-carte" data-carte-zones>'
            '<div class="carte">%s<div class="carte-tip" hidden><strong></strong><span></span></div></div>'
            '<div class="carte-infos"><ul class="carte-legende">%s</ul>'
            '<p class="carte-aide"><span class="si-souris">%s</span><span class="si-tactile">%s</span> %s</p></div></div>') % (
        svg, legende, c['hover'], c['touch'], c['inset'])


def city_page(slug):
    v = VILLE_PAR_SLUG[slug]
    nom = esc(v['nom'])
    fr = v['pays'] == 'FR'
    sectors = ''.join('<li><a class="chip" href="%s.html">{{icon:%s}}%s</a></li>' % (x['slug'], x['icon'], esc(x['label'])) for x in SECTORS)
    supports = ''.join('<li><a class="chip" href="%s">{{icon:couches}}%s</a></li>' % (f, esc(label)) for f, label in SUPPORTS)
    proches = ''.join(city_chip(VILLE_PAR_SLUG[x]) for x in v['proches'])
    if fr:
        zone = v['zone']
        region = next(r for r in REGIONS if r[0] == v['region'])
        sim = 'rentabilite-cool-roof.html?cp=%s#simulateur' % v['cp']
        facts = [('Département', '%s (%s)' % (esc(v['dept'][1]), v['dept'][0])),
                 ('Région', '<a href="zones-intervention.html#%s">%s</a>' % (region[1], esc(v['region']))),
                 ('Zone climatique CEE', zone),
                 ('Prime BAT-EN-112', '%d kWh cumac par m², soit ≈ %s € pour 1 000 m² de toiture' % (CEE_KWHC[zone], fmt_int(cee_1000(zone))))]
        facts_note = '<p class="src">Prime estimée à 8,70 € le MWh cumac (indice de prix des CEE classiques, juin 2026), sous réserve d’éligibilité. <a href="aides-reglementation.html#bat-en-112">Les conditions</a></p>'
        aides = ('<ul class="checklist">'
                 '<li>{{icon:check}}<span><strong>Prime CEE BAT-EN-112</strong> : en zone %s, %d kWh cumac par m² de toiture traitée, pour un bâtiment tertiaire à usage commercial, climatisé par pompe à chaleur. <a href="aides-reglementation.html#bat-en-112">Les conditions</a></span></li>'
                 '<li>{{icon:check}}<span><strong>Décret tertiaire</strong> : les bâtiments tertiaires de 1 000 m² et plus doivent réduire leur consommation d’énergie de 40 %% d’ici 2030. <a href="decret-tertiaire.html">En savoir plus</a></span></li>'
                 '<li>{{icon:check}}<span><strong>Chaleur au travail</strong> : depuis le 1er juillet 2025, l’employeur doit prévenir les risques liés à la chaleur pendant les épisodes de chaleur intense. <a href="chaleur-au-travail.html">Les obligations</a></span></li>'
                 '</ul>') % (zone, CEE_KWHC[zone])
        region_link = '<a class="link-arrow" href="zones-intervention.html#%s">Toute la région %s{{icon:fleche}}</a>' % (region[1], esc(v['region']))
    else:
        sim = 'rentabilite-cool-roof.html?pays=CH#simulateur'
        facts = [('Pays', 'Suisse'), ('Canton', esc(v['canton'])), ('Prime CEE', 'dispositif français, non applicable en Suisse')]
        facts_note = '<p class="src">Source : <a href="https://www.fedlex.admin.ch/eli/cc/1999/404/fr#art_89" rel="noopener" target="_blank">Constitution fédérale, article 89</a>.</p>'
        aides = ('<ul class="checklist">'
                 '<li>{{icon:check}}<span><strong>Règles cantonales</strong> : les mesures concernant la consommation d’énergie dans les bâtiments relèvent au premier chef des cantons, ici le canton de %s.</span></li>'
                 '<li>{{icon:check}}<span><strong>Pas de CEE</strong> : les certificats d’économies d’énergie sont un dispositif français.</span></li>'
                 '<li>{{icon:check}}<span><strong>La même étude</strong> : diagnostic du support, intérêt été comme hiver, choix du système adapté à votre toiture.</span></li>'
                 '</ul>') % esc(v['canton'])
        region_link = '<a class="link-arrow" href="zones-intervention.html#suisse">La Suisse dans nos zones d’intervention{{icon:fleche}}</a>'
    facts_html = ''.join('<div><dt>%s</dt><dd>%s</dd></div>' % (k, val) for k, val in facts)
    return f'''<section class="page-head page-head--compact">
<div class="wrap">
{{{{BREADCRUMB}}}}
{{{{EYEBROW}}}}
<h1>Cool roof à {nom}</h1>
<p class="lead">ALBEDIA applique des revêtements réfléchissants sur les toitures des entrepôts, usines, commerces, bureaux et équipements publics de {nom} {esc(v['agglo'])}.</p>
<div class="hero-actions"><a class="btn btn--sun" href="devis.html">Demander un devis{{{{icon:fleche}}}}</a><a class="btn btn--line" href="{sim}">Simuler mes économies à {nom}</a></div>
</div>
</section>
<section class="band" aria-labelledby="climat-titre">
<div class="wrap split split--top">
<div class="prose">
<p class="kicker">Climat</p>
<h2 id="climat-titre">Le climat de {nom} et vos toitures</h2>
<p>{esc(v['climat'])}</p>
<p>{esc(v['contexte'])}</p>
<p>Une toiture traditionnelle sombre absorbe 85 à 95 % du rayonnement solaire. Une toiture réfléchissante en renvoie l’essentiel : au plus chaud de la journée, elle reste environ 28 à 33 °C plus fraîche en surface (US EPA).</p>
</div>
<div class="aside-box">
<h3>{nom} en bref</h3>
<dl class="city-facts">{facts_html}</dl>
{facts_note}
</div>
</div>
</section>
<section class="band band--tint" aria-labelledby="batiments-titre">
<div class="wrap">
<div class="section-head">
<p class="kicker">Bâtiments</p>
<h2 id="batiments-titre">Les toitures que nous traitons à {nom}</h2>
<p class="lead">Nous intervenons sur les bâtiments professionnels de {nom} et de ses environs, quels que soient leur usage et leur couverture. Chaque projet commence par la visite de la toiture.</p>
</div>
<div class="grid-2 city-links">
<nav aria-labelledby="par-secteur-titre"><h3 id="par-secteur-titre">Par secteur</h3><ul class="chips">{sectors}</ul></nav>
<nav aria-labelledby="par-toiture-titre"><h3 id="par-toiture-titre">Par type de toiture</h3><ul class="chips">{supports}</ul></nav>
</div>
</div>
</section>
<section class="band" aria-labelledby="regles-titre">
<div class="wrap split split--top">
<div class="prose">
<p class="kicker">Aides et obligations</p>
<h2 id="regles-titre">Ce qui s’applique à votre bâtiment à {nom}</h2>
{aides}
<div class="hero-actions"><a class="btn btn--sun" href="{sim}">Estimer mes économies et ma prime{{{{icon:fleche}}}}</a></div>
</div>
<nav class="others" aria-labelledby="proches-titre">
<h3 id="proches-titre">Villes proches</h3>
<ul class="chips">{proches}</ul>
{region_link}
<a class="link-arrow" href="zones-intervention.html#villes">Toutes nos villes{{{{icon:fleche}}}}</a>
</nav>
</div>
</section>
'''


# ------------------------------------------------------------------ JSON-LD
def jsonld(page):
    blocks = []
    lang = page.get('lang', 'fr')
    if lang != 'fr':
        base = SITE_URL + '/' + lang + '/'
        if page['file'] == 'index.html':
            blocks.append({'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'ALBEDIA', 'url': base,
                           'inLanguage': UI[lang]['html_lang']})
        elif page.get('crumbs'):
            items = [{'@type': 'ListItem', 'position': 1, 'name': UI[lang]['home'], 'item': base}]
            for i, (label, link) in enumerate(page['crumbs']):
                it = {'@type': 'ListItem', 'position': i + 2, 'name': label}
                if i == len(page['crumbs']) - 1:
                    it['item'] = base + page['file']
                elif link:
                    it['item'] = base + link.replace('index.html', '')
                items.append(it)
            blocks.append({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': items})
        if page.get('faq'):
            faq = json.load(open(os.path.join(I18N_DIR, lang, page['faq']), encoding='utf-8'))
            blocks.append({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
                {'@type': 'Question', 'name': q['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': ' '.join(q['a'])}} for q in faq]})
        return ''.join('<script type="application/ld+json">%s</script>\n' % json.dumps(b, ensure_ascii=False) for b in blocks)
    if page['file'] == 'index.html':
        blocks.append({
            '@context': 'https://schema.org', '@type': 'Organization', 'name': 'ALBEDIA', 'url': SITE_URL + '/',
            'logo': SITE_URL + '/assets/img/logo-albedia.png', 'email': EMAIL,
            'slogan': SLOGANS[0].replace('\u00a0', ' '),
            'description': 'Application de revêtements réfléchissants (cool roof) sur les toitures des bâtiments professionnels.',
            'areaServed': [{'@type': 'Country', 'name': n} for n in COUNTRIES],
            'legalName': 'CONTRACTANT GENERAL EN BATIMENTS INDUSTRIELS (CGBI)',
            'telephone': PHONE_TEL,
            'address': {'@type': 'PostalAddress', 'streetAddress': '163 cours de la Libération et du Général de Gaulle',
                        'postalCode': '38000', 'addressLocality': 'Grenoble', 'addressCountry': 'FR'}})
        blocks.append({'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'ALBEDIA', 'url': SITE_URL + '/',
                       'inLanguage': 'fr-FR'})
    elif page.get('crumbs'):
        items = [{'@type': 'ListItem', 'position': 1, 'name': 'Accueil', 'item': SITE_URL + '/'}]
        crumbs = page['crumbs']
        for i, (label, link) in enumerate(crumbs):
            it = {'@type': 'ListItem', 'position': i + 2, 'name': label}
            if i == len(crumbs) - 1:
                it['item'] = SITE_URL + '/' + page['file']
            elif link:
                it['item'] = SITE_URL + '/' + link.replace('index.html', '')
            items.append(it)
        blocks.append({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': items})
    if page.get('city'):
        v = VILLE_PAR_SLUG[page['city']]
        blocks.append({'@context': 'https://schema.org', '@type': 'Service', 'name': 'Cool roof à ' + v['nom'],
                       'serviceType': 'Revêtement réfléchissant de toiture (cool roof)',
                       'provider': {'@type': 'Organization', 'name': 'ALBEDIA', 'url': SITE_URL + '/'},
                       'areaServed': {'@type': 'City', 'name': v['nom']}, 'url': SITE_URL + '/' + page['file']})
    faq_file = 'faq.json' if page['file'] == 'faq.html' else page.get('faq')
    if faq_file:
        faq = json.load(open(os.path.join(SRC, 'pages', faq_file), encoding='utf-8'))
        blocks.append({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': q['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': ' '.join(q['a'])}} for q in faq]})
    return ''.join('<script type="application/ld+json">%s</script>\n' % json.dumps(b, ensure_ascii=False) for b in blocks)


def faq_html(items):
    out = []
    for q in items:
        out.append('<details><summary>%s</summary><div class="answer">%s</div></details>' % (
            esc(q['q']), ''.join('<p>%s</p>' % esc(p) for p in q['a'])))
    return '<div class="faq">%s</div>' % ''.join(out)


# ------------------------------------------------------------------ assemblage
def page_body(page, ctx):
    lang = ctx.lang
    if page.get('city'):
        main = city_page(page['city'])
    elif page.get('sector'):
        main = sector_page(page['sector'], ctx)
        d = (SECTOR_DATA if lang == 'fr' else I18N_SECTORS[lang])[page['sector']]
        page['title'] = d['title']
        page['desc'] = d['desc']
    elif lang != 'fr':
        main = open(os.path.join(I18N_DIR, lang, 'pages', page['src']), encoding='utf-8').read()
    else:
        main = open(os.path.join(SRC, 'pages', page['src']), encoding='utf-8').read()
    m = re.search(r'\{\{bg:([a-z0-9-]+)\}\}', main)
    page['lcp'] = m.group(1) if m else None   # photo d'en-tête, préchargée dans le <head>
    if '{{SIMULATEUR}}' in main:
        main = main.replace('{{SIMULATEUR}}', part('simulateur.html') if lang == 'fr'
                            else open(os.path.join(I18N_DIR, lang, 'simulateur.html'), encoding='utf-8').read())
    if '{{FAQ_PAGE}}' in main:
        base = os.path.join(SRC, 'pages') if lang == 'fr' else os.path.join(I18N_DIR, lang)
        main = main.replace('{{FAQ_PAGE}}', faq_html(json.load(open(os.path.join(base, page['faq']), encoding='utf-8'))))
    if lang != 'fr' and '{{FAQ_HOME}}' in main:
        main = main.replace('{{FAQ_HOME}}', faq_html(json.load(open(os.path.join(I18N_DIR, lang, 'faq-home.json'), encoding='utf-8'))))
    if '{{FAQ_FULL}}' in main or '{{FAQ_HOME}}' in main:
        faq = json.load(open(os.path.join(SRC, 'pages', 'faq.json'), encoding='utf-8'))
        main = main.replace('{{FAQ_FULL}}', faq_html(faq))
        main = main.replace('{{FAQ_HOME}}', faq_html([q for q in faq if q.get('home')]))
    parts = [header(ctx), '<main id="contenu">', main, '</main>']
    if page.get('cta'):
        parts.append(cta_band(ctx))
    parts.append(footer(ctx))
    return typo(expand('\n'.join(parts), ctx), lang)


def preload_photo(page, ctx):
    slug = page.get('lcp')
    if not slug:
        return ''
    p = PHOTOS[slug]
    base = '%sassets/img/photos/%s' % (ctx.prefix, slug)
    srcset = ', '.join('%s-%d.webp %dw' % (base, w, w) for w in p['widths'])
    return '<link rel="preload" as="image" type="image/webp" imagesrcset="%s" imagesizes="100vw" fetchpriority="high">\n' % srcset


def alternates(page):
    """Balises hreflang des pages qui existent en français, en anglais, en italien et en espagnol."""
    if page['file'] not in TRANSLATED:
        return ''
    path = '' if page['file'] == 'index.html' else page['file']
    out = ['<link rel="alternate" hreflang="fr" href="%s/%s">' % (SITE_URL, path)]
    out += ['<link rel="alternate" hreflang="%s" href="%s/%s/%s">' % (l, SITE_URL, l, path) for l in I18N_LANGS]
    out.append('<link rel="alternate" hreflang="x-default" href="%s/%s">' % (SITE_URL, path))
    return '\n'.join(out) + '\n'


def head_site(page, ctx):
    p = ctx.prefix
    lang = ctx.lang
    url = SITE_URL + '/' + ('' if lang == 'fr' else lang + '/') + ('' if page['file'] == 'index.html' else page['file'])
    robots = 'noindex, follow' if page.get('noindex') else 'index, follow'
    canonical = '' if page.get('noindex') else '<link rel="canonical" href="%s">\n' % url
    og_title = page.get('og') or page['title'].replace(' | ALBEDIA', '')
    gsc = ('<meta name="google-site-verification" content="%s">\n' % GSC_VERIFICATION
           if GSC_VERIFICATION and page['file'] == 'index.html' and lang == 'fr' else '')
    html_lang = 'fr' if lang == 'fr' else UI[lang]['html_lang']
    og_locale = 'fr_FR' if lang == 'fr' else UI[lang]['og_locale']
    og_alt = 'ALBEDIA, cool roof pour toitures professionnelles' if lang == 'fr' else UI[lang]['og_alt']
    return f'''<!doctype html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title>
<meta name="description" content="{esc(page['desc'])}">
<meta name="robots" content="{robots}">
{gsc}{canonical}{alternates(page)}<meta name="theme-color" content="#0F2B46">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ALBEDIA">
<meta property="og:locale" content="{og_locale}">
<meta property="og:title" content="{esc(og_title)}">
<meta property="og:description" content="{esc(page['desc'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}/assets/img/og-albedia.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{p}favicon.ico" sizes="32x32">
<link rel="icon" href="{p}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{p}apple-touch-icon.png">
<link rel="preload" href="{p}assets/fonts/plus-jakarta-sans-var.woff2" as="font" type="font/woff2" crossorigin>
{preload_photo(page, ctx)}<link rel="stylesheet" href="{p}assets/css/style.css?v=9">
{jsonld(page)}</head>
<body>
'''


GFONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400..800&amp;display=swap">')


def head_preview(page, is_main, ctx):
    if is_main:
        return ('<title>Site albedia.eu</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
                + GFONTS + '\n<link rel="stylesheet" href="assets/css/style.css?v=9">\n')
    html_lang = 'fr' if ctx.lang == 'fr' else UI[ctx.lang]['html_lang']
    return f'''<!doctype html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title>
{GFONTS}
<link rel="stylesheet" href="{ctx.prefix}assets/css/style.css?v=9">
</head>
<body>
'''


def build(variant, out):
    out = os.path.abspath(out)
    if variant == 'preview':
        # l'aperçu va toujours dans un dossier jetable, jamais dans le dépôt
        if out == REPO or out.startswith(REPO + os.sep):
            sys.exit('Le dossier d’aperçu doit être en dehors du dépôt.')
        if os.path.isdir(out):
            shutil.rmtree(out)
    for d in ('css', 'js', 'img'):
        os.makedirs(os.path.join(out, 'assets', d), exist_ok=True)
    css = open(os.path.join(SRC, 'assets', 'css', 'style.css'), encoding='utf-8').read()
    if variant == 'preview':
        css = re.sub(r'/\* @font-face:start \*/.*?/\* @font-face:end \*/', '', css, flags=re.S)
    css += photo_css()
    open(os.path.join(out, 'assets', 'css', 'style.css'), 'w', encoding='utf-8').write(css)
    shutil.copy(os.path.join(SRC, 'assets', 'js', 'main.js'), os.path.join(out, 'assets', 'js', 'main.js'))
    img_src = os.path.join(SRC, 'assets', 'img')
    for f in os.listdir(img_src):
        if os.path.isfile(os.path.join(img_src, f)):
            shutil.copy(os.path.join(img_src, f), os.path.join(out, 'assets', 'img', f))
    # photos : le dossier généré est recréé à chaque build (une photo retirée des sources disparaît du site)
    photos_out = os.path.join(out, 'assets', 'img', 'photos')
    if os.path.isdir(photos_out):
        shutil.rmtree(photos_out)
    shutil.copytree(os.path.join(img_src, 'photos'), photos_out)
    # documents à télécharger (plaquette PDF) : recopiés à chaque build
    docs_out = os.path.join(out, 'assets', 'docs')
    if os.path.isdir(docs_out):
        shutil.rmtree(docs_out)
    shutil.copytree(os.path.join(SRC, 'assets', 'docs'), docs_out)
    if variant == 'site':
        shutil.copytree(os.path.join(SRC, 'assets', 'fonts'), os.path.join(out, 'assets', 'fonts'), dirs_exist_ok=True)
        for f in ('favicon.ico', 'favicon.svg', 'apple-touch-icon.png'):
            shutil.copy(os.path.join(SRC, 'assets', f), os.path.join(out, f))
        shutil.copy(os.path.join(SRC, 'php', 'contact.php'), os.path.join(out, 'contact.php'))
        shutil.copy(os.path.join(SRC, 'php', 'simulation.php'), os.path.join(out, 'simulation.php'))
        shutil.copy(os.path.join(SRC, 'php', '.htaccess'), os.path.join(out, '.htaccess'))
    written = []
    for l in I18N_LANGS:
        os.makedirs(os.path.join(out, l), exist_ok=True)
    for page in PAGES + LANG_PAGES:
        if variant == 'preview' and page['file'] == '404.html':
            continue
        ctx = Ctx(variant, page)
        body = page_body(page, ctx)
        p = ctx.prefix
        script = '<script src="%sassets/js/main.js?v=9" defer></script>\n' % p
        if ctx.lang != 'fr':
            # textes du simulateur et des formulaires pour main.js
            js = json.load(open(os.path.join(I18N_DIR, ctx.lang, 'js.json'), encoding='utf-8'))
            script = ('<script type="application/json" id="i18n-js">%s</script>\n' % json.dumps(js, ensure_ascii=False).replace('</', '<\\/')) + script
        rel = page['file'] if ctx.lang == 'fr' else ctx.lang + '/' + page['file']
        if variant == 'site':
            doc = head_site(page, ctx) + body + '\n' + script + '</body>\n</html>\n'
        else:
            is_main = page['file'] == 'index.html' and ctx.lang == 'fr'
            doc = head_preview(page, is_main, ctx) + body + '\n' + script + ('' if is_main else '</body>\n</html>\n')
        open(os.path.join(out, rel), 'w', encoding='utf-8').write(doc)
        written.append(rel)
    if variant == 'site':
        urls = [pg['file'] for pg in PAGES if not pg.get('noindex') and pg['file'] not in ('mentions-legales.html', 'confidentialite.html')]
        sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for f in urls:
            loc = SITE_URL + '/' + ('' if f == 'index.html' else f)
            pg = next(x for x in PAGES if x['file'] == f)
            prio = pg.get('prio') or ('1.0' if f == 'index.html' else ('0.9' if f in ('guide-cool-roof.html', 'solutions.html', 'devis.html') else '0.7'))
            sm.append('  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>' % (loc, LASTMOD, prio))
        for pg in LANG_PAGES:
            f = pg['file']
            loc = '%s/%s/%s' % (SITE_URL, pg['lang'], '' if f == 'index.html' else f)
            prio = pg.get('prio') or ('0.8' if f == 'index.html' else '0.6')
            sm.append('  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>' % (loc, LASTMOD, prio))
        sm.append('</urlset>')
        open(os.path.join(out, 'sitemap.xml'), 'w').write('\n'.join(sm) + '\n')
        open(os.path.join(out, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE_URL)
    print(variant, len(written), 'pages')
    return written


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] == 'site':
        build('site', REPO)
    elif args[0] == 'preview':
        build('preview', args[1] if len(args) > 1 else os.path.join(tempfile.gettempdir(), 'albedia-preview'))
    else:
        sys.exit('Usage : python3 _src/build.py [site | preview <dossier>]')
