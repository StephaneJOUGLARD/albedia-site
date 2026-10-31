#!/usr/bin/env python3
"""Assemble le site ALBEDIA à partir des sources de _src/.

Utilisation (depuis la racine du dépôt) :
  python3 _src/build.py                     régénère le site à la racine du dépôt (ce que publie OVH)
  python3 _src/build.py preview <dossier>   produit un aperçu (polices Google Fonts, formulaire inactif)
                                            dans un dossier HORS du dépôt, pour le publier comme artifact
"""
import html, json, os, re, shutil, sys, tempfile

SRC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SRC)

SITE_URL = 'https://albedia.eu'
EMAIL = 'contact@albedia.eu'
PHONE = None          # ex. '04 00 00 00 00' : s'affiche dans l'en-tête de contact et le pied de page
LASTMOD = '2026-10-31'
SLOGANS = ['Vos toitures réfléchissent\u00a0!', 'Augmentez votre albédo\u00a0!']

SECTORS = [
    dict(slug='industrie', label='Industrie', short='Ateliers et sites de production', icon='industrie'),
    dict(slug='logistique', label='Logistique', short='Entrepôts et plateformes', icon='logistique'),
    dict(slug='distribution', label='Commerce et distribution', short='Magasins et surfaces de vente', icon='distribution'),
    dict(slug='tertiaire', label='Bureaux et tertiaire', short='Bureaux et bâtiments d’activité', icon='tertiaire'),
    dict(slug='collectivites', label='Collectivités', short='Écoles, gymnases, équipements', icon='collectivites'),
    dict(slug='agricole', label='Agricole', short='Élevage, stockage, transformation', icon='agricole'),
]

# Ordre = ordre d'alternance des slogans (0, 1, 0, 1…)
PAGES = [
    dict(file='index.html', src='index.html', title='Cool roof pour toitures professionnelles | ALBEDIA',
         og='ALBEDIA, le cool roof pour les toitures professionnelles',
         desc='ALBEDIA applique des revêtements réfléchissants (cool roof) sur les toitures des entrepôts, usines, commerces et bureaux pour garder les bâtiments plus frais l’été.',
         crumbs=None, nav=None, cta=True, cta_bg='paper'),
    dict(file='guide-cool-roof.html', src='guide-cool-roof.html', title='Le cool roof : principe, albédo, bénéfices et limites | ALBEDIA',
         desc='Comprendre le cool roof : albédo, émissivité, indice SRI, chiffres de référence sourcés, intérêt selon le bâtiment, effet en hiver et entretien.',
         crumbs=[('Le cool roof', None)], nav='guide', cta=True, cta_bg='paper', cta2=('solutions.html', 'Découvrir nos solutions')),
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
         crumbs=[('Aides et réglementation', None)], nav='aides', cta=True, cta_bg='paper'),
    dict(file='faq.html', src='faq.html', title='Questions fréquentes sur le cool roof | ALBEDIA',
         desc='Gains, hiver, toitures compatibles, durée de vie, entretien, aides : les réponses aux questions les plus fréquentes sur le cool roof.',
         crumbs=[('Questions fréquentes', None)], nav='albedia', cta=True, cta_bg='paper'),
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
]
for i, p in enumerate(PAGES):
    p['slogan'] = SLOGANS[i % 2]

SECTOR_DATA = json.load(open(os.path.join(SRC, 'pages', 'secteurs.json'), encoding='utf-8'))

# ------------------------------------------------------------------ helpers
PART = os.path.join(SRC, 'partials')


def part(name):
    return open(os.path.join(PART, name), encoding='utf-8').read()


def icon(name):
    return part(os.path.join('icons', name + '.svg'))


def esc(t):
    return html.escape(t, quote=True)


def typo(markup):
    """Typographie française sur les nœuds texte (hors script, style et balises)."""
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


class Ctx:
    def __init__(self, variant, page):
        self.variant, self.page = variant, page
        self.prefix = '/' if page.get('absolute') and variant == 'site' else ''

    def href(self, target):
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
        if key == 'PREVIEW_ATTR':
            return ' data-preview="1"' if ctx.variant == 'preview' else ''
        if key == 'BREADCRUMB':
            return breadcrumb(ctx)
        if key == 'SECTOR_TILES':
            return sector_tiles(ctx)
        if key == 'SECTOR_OPTIONS':
            return sector_options()
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
    text = re.sub(r'action="(devis\.html|contact\.php)"', lambda m: 'action="%s%s"' % (ctx.prefix, m.group(1)), text)
    return text


SECTOR_CHOICES = ['Industrie', 'Logistique et entreposage', 'Commerce et distribution', 'Bureaux et tertiaire',
                  'Collectivité ou équipement public', 'Agricole', 'Autre']


def sector_options():
    return '<option value="">Choisir…</option>' + ''.join('<option>%s</option>' % esc(c) for c in SECTOR_CHOICES)


def sector_tiles(ctx):
    return ''.join(
        '<a class="tile" href="%s.html">%s<span class="tile-text"><strong>%s</strong><span>%s</span></span>%s</a>' % (
            s['slug'], icon(s['icon']), esc(s['label']), esc(s['short']), icon('fleche'))
        for s in SECTORS)


def breadcrumb(ctx):
    crumbs = ctx.page.get('crumbs') or []
    items = ['<li><a href="index.html">Accueil</a></li>']
    for i, (label, link) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        if last:
            items.append('<li><span aria-current="page">%s</span></li>' % esc(label))
        elif link:
            items.append('<li><a href="%s">%s</a></li>' % (link, esc(label)))
        else:
            items.append('<li><span>%s</span></li>' % esc(label))
    return '<nav class="breadcrumb" aria-label="Fil d’Ariane"><ol>%s</ol></nav>' % ''.join(items)


# ------------------------------------------------------------------ gabarits communs
def header(ctx):
    nav = ctx.page.get('nav')
    cur = lambda key: ' aria-current="page"' if nav == key else ''
    sub_cur = lambda key: ' is-current' if nav == key else ''
    sectors = ''.join('<li><a href="%s.html"%s>%s<span>%s</span></a></li>' % (
        s['slug'], ' aria-current="page"' if ctx.page.get('sector') == s['slug'] else '', icon(s['icon']), esc(s['label']))
        for s in SECTORS)
    albedia = ''.join('<li><a href="%s"%s>%s<span>%s</span></a></li>' % (
        f, ' aria-current="page"' if ctx.page['file'] == f else '', icon(ic), lab)
        for f, ic, lab in (('qui-sommes-nous.html', 'interlocuteur', 'Qui sommes-nous'),
                           ('faq.html', 'question', 'Questions fréquentes'),
                           ('devis.html', 'mail', 'Devis et contact')))
    return f'''<a class="skip" href="#contenu">Aller au contenu</a>
<header class="site-header">
<div class="wrap">
<a class="brand" href="index.html" aria-label="ALBEDIA, accueil">{part('logo.svg')}</a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav-principale">{icon('menu')}<span>Menu</span></button>
<nav class="nav" id="nav-principale" aria-label="Navigation principale">
<ul class="nav-list">
<li><a class="nav-link" href="solutions.html"{cur('solutions')}>Solutions</a></li>
<li class="has-sub"><button class="nav-toggle-sub{sub_cur('secteurs')}" type="button" aria-expanded="false" aria-controls="sub-secteurs">Secteurs{icon('chevron')}</button>
<ul class="sub" id="sub-secteurs">{sectors}</ul></li>
<li><a class="nav-link" href="guide-cool-roof.html"{cur('guide')}>Le cool roof</a></li>
<li><a class="nav-link" href="aides-reglementation.html"{cur('aides')}>Aides CEE</a></li>
<li class="has-sub"><button class="nav-toggle-sub{sub_cur('albedia')}" type="button" aria-expanded="false" aria-controls="sub-albedia">ALBEDIA{icon('chevron')}</button>
<ul class="sub" id="sub-albedia">{albedia}</ul></li>
</ul>
<a class="btn btn--sun btn--sm nav-cta" href="devis.html"{cur('devis')}>Demander un devis</a>
</nav>
</div>
</header>'''


def cta_band(ctx):
    page = ctx.page
    href2, label2 = page.get('cta2', ('guide-cool-roof.html', 'Lire le guide du cool roof'))
    return f'''<div class="cta-outer cta-outer--{page.get('cta_bg', 'paper')}">
<section class="cta-band" aria-labelledby="cta-titre">
<div class="wrap">
{part('sun.svg').replace('class="sun"', 'class="sun sun--xl"')}
<h2 class="cta-slogan" id="cta-titre">{page['slogan']}</h2>
<p>Parlez-nous de votre bâtiment : surface, type de toiture, usage. Nous revenons vers vous pour organiser la visite de la toiture.</p>
<div class="cta-actions"><a class="btn btn--sun" href="devis.html">Demander un devis{icon('fleche')}</a><a class="btn btn--line" href="{href2}">{label2}</a></div>
<p class="cta-contact">Ou écrivez-nous à <a href="mailto:{EMAIL}">{EMAIL}</a></p>
</div>
</section>
</div>'''


def footer(ctx):
    phone = ('<p class="footer-contact">%s<span>%s</span></p>' % (icon('tel'), PHONE)) if PHONE else ''
    sectors = ''.join('<li><a href="%s.html">%s</a></li>' % (s['slug'], esc(s['label'])) for s in SECTORS)
    return f'''<footer class="site-footer">
<div class="wrap">
<div class="footer-top">
<div class="footer-brand">
<a class="brand" href="index.html" aria-label="ALBEDIA, accueil">{part('logo.svg')}</a>
<p>Revêtements réfléchissants (cool roof) pour les toitures des bâtiments professionnels, en France.</p>
<p class="footer-contact">{icon('mail')}<a href="mailto:{EMAIL}">{EMAIL}</a></p>
{phone}
</div>
<div class="footer-col"><h2>Solutions</h2><ul>
<li><a href="solutions.html">Nos solutions</a></li>
<li><a href="solutions.html#methode">Notre méthode</a></li>
<li><a href="solutions.html#toitures">Toitures compatibles</a></li>
<li><a href="devis.html">Demander un devis</a></li>
</ul></div>
<div class="footer-col"><h2>Secteurs</h2><ul>{sectors}</ul></div>
<div class="footer-col"><h2>Ressources</h2><ul>
<li><a href="guide-cool-roof.html">Guide du cool roof</a></li>
<li><a href="aides-reglementation.html#bat-en-112">Prime CEE BAT-EN-112</a></li>
<li><a href="aides-reglementation.html#decret-tertiaire">Décret tertiaire</a></li>
<li><a href="faq.html">Questions fréquentes</a></li>
</ul></div>
<div class="footer-col"><h2>ALBEDIA</h2><ul>
<li><a href="qui-sommes-nous.html">Qui sommes-nous</a></li>
<li><a href="devis.html">Contact</a></li>
<li><a href="mentions-legales.html">Mentions légales</a></li>
<li><a href="confidentialite.html">Confidentialité</a></li>
</ul></div>
</div>
<div class="footer-bottom"><p>© 2026 ALBEDIA. Tous droits réservés.</p><p>Ce site ne dépose aucun cookie.</p></div>
</div>
</footer>'''


# ------------------------------------------------------------------ pages secteur
def sector_page(slug):
    d = SECTOR_DATA[slug]
    s = next(x for x in SECTORS if x['slug'] == slug)
    bats = ''.join('<li>%s<span>%s</span></li>' % ('{{icon:check}}', esc(b)) for b in d['batiments'])
    bens = ''.join('<div class="feature"><span class="ico-badge">{{icon:%s}}</span><h3>%s</h3><p>%s</p></div>' % (
        ic, esc(t), esc(p)) for ic, t, p in d['benefices'])
    pts = ''.join('<li>{{icon:loupe}}<span>%s</span></li>' % esc(p) for p in d['points'])
    others = ''.join('<li><a class="chip" href="%s.html">{{icon:%s}}%s</a></li>' % (o['slug'], o['icon'], esc(o['label']))
                     for o in SECTORS if o['slug'] != slug)
    enjeux = ''.join('<p>%s</p>' % esc(p) for p in d['enjeux'])
    return f'''<section class="page-head page-head--sector">
<div class="wrap">
{{{{BREADCRUMB}}}}
<span class="badge-ico">{{{{icon:{s['icon']}}}}}</span>
{{{{EYEBROW}}}}
<h1>{esc(d['h1'])}</h1>
<p class="lead">{esc(d['lead'])}</p>
<div class="hero-actions"><a class="btn btn--sun" href="devis.html">Demander un devis{{{{icon:fleche}}}}</a><a class="btn btn--line" href="guide-cool-roof.html">Comprendre le cool roof</a></div>
</div>
</section>
<section class="band" aria-labelledby="enjeux-titre">
<div class="wrap split split--top">
<div class="prose">
<p class="kicker">Les enjeux</p>
<h2 id="enjeux-titre">{esc(d['enjeux_titre'])}</h2>
{enjeux}
</div>
<aside class="aside-box" aria-labelledby="batiments-titre">
<h3 id="batiments-titre">Bâtiments concernés</h3>
<ul class="checklist">{bats}</ul>
</aside>
</div>
</section>
<section class="band band--tint" aria-labelledby="apports-titre">
<div class="wrap">
<div class="section-head">
<p class="kicker">Ce que vous y gagnez</p>
<h2 id="apports-titre">Ce que le cool roof vous apporte</h2>
</div>
<div class="grid-3">{bens}</div>
</div>
</section>
<section class="band" aria-labelledby="points-titre">
<div class="wrap split split--top">
<div class="prose">
<p class="kicker">Avant les travaux</p>
<h2 id="points-titre">Les points que nous étudions</h2>
<p>Chaque bâtiment a ses contraintes. La visite de la toiture sert à les relever avant de vous proposer un procédé et un devis.</p>
<a class="link-arrow" href="solutions.html#methode">Voir notre méthode{{{{icon:fleche}}}}</a>
</div>
<ul class="checklist checklist--points">{pts}</ul>
</div>
</section>
<section class="band band--tint" aria-labelledby="aides-titre">
<div class="wrap split split--top">
<div class="prose">
<p class="kicker">Aides et obligations</p>
<h2 id="aides-titre">Ce qui peut s’appliquer à votre bâtiment</h2>
<p>{esc(d['aides'])}</p>
<a class="link-arrow" href="aides-reglementation.html">Aides CEE et réglementation{{{{icon:fleche}}}}</a>
</div>
<nav class="others" aria-labelledby="autres-titre">
<h3 id="autres-titre">Autres secteurs</h3>
<ul class="chips">{others}</ul>
</nav>
</div>
</section>
'''


# ------------------------------------------------------------------ JSON-LD
def jsonld(page):
    blocks = []
    if page['file'] == 'index.html':
        blocks.append({
            '@context': 'https://schema.org', '@type': 'Organization', 'name': 'ALBEDIA', 'url': SITE_URL + '/',
            'logo': SITE_URL + '/assets/img/logo-albedia.png', 'email': EMAIL,
            'slogan': SLOGANS[0].replace('\u00a0', ' '),
            'description': 'Application de revêtements réfléchissants (cool roof) sur les toitures des bâtiments professionnels.',
            'areaServed': {'@type': 'Country', 'name': 'France'}})
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
    if page['file'] == 'faq.html':
        faq = json.load(open(os.path.join(SRC, 'pages', 'faq.json'), encoding='utf-8'))
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
    if page.get('sector'):
        main = sector_page(page['sector'])
        d = SECTOR_DATA[page['sector']]
        page['title'] = d['title']
        page['desc'] = d['desc']
    else:
        main = open(os.path.join(SRC, 'pages', page['src']), encoding='utf-8').read()
    if '{{FAQ_FULL}}' in main or '{{FAQ_HOME}}' in main:
        faq = json.load(open(os.path.join(SRC, 'pages', 'faq.json'), encoding='utf-8'))
        main = main.replace('{{FAQ_FULL}}', faq_html(faq))
        main = main.replace('{{FAQ_HOME}}', faq_html([q for q in faq if q.get('home')]))
    parts = [header(ctx), '<main id="contenu">', main, '</main>']
    if page.get('cta'):
        parts.append(cta_band(ctx))
    parts.append(footer(ctx))
    return typo(expand('\n'.join(parts), ctx))


def head_site(page, ctx):
    p = ctx.prefix
    url = SITE_URL + '/' + ('' if page['file'] == 'index.html' else page['file'])
    robots = 'noindex, follow' if page.get('noindex') else 'index, follow'
    canonical = '' if page.get('noindex') else '<link rel="canonical" href="%s">\n' % url
    og_title = page.get('og') or page['title'].replace(' | ALBEDIA', '')
    return f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title>
<meta name="description" content="{esc(page['desc'])}">
<meta name="robots" content="{robots}">
{canonical}<meta name="theme-color" content="#0F2B46">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ALBEDIA">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{esc(og_title)}">
<meta property="og:description" content="{esc(page['desc'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}/assets/img/og-albedia.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="ALBEDIA, cool roof pour toitures professionnelles">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{p}favicon.ico" sizes="32x32">
<link rel="icon" href="{p}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{p}apple-touch-icon.png">
<link rel="preload" href="{p}assets/fonts/plus-jakarta-sans-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{p}assets/css/style.css?v=1">
{jsonld(page)}</head>
<body>
'''


GFONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400..800&amp;display=swap">')


def head_preview(page, is_main):
    if is_main:
        return ('<title>Site albedia.eu</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
                + GFONTS + '\n<link rel="stylesheet" href="assets/css/style.css?v=1">\n')
    return f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title>
{GFONTS}
<link rel="stylesheet" href="assets/css/style.css?v=1">
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
    open(os.path.join(out, 'assets', 'css', 'style.css'), 'w', encoding='utf-8').write(css)
    shutil.copy(os.path.join(SRC, 'assets', 'js', 'main.js'), os.path.join(out, 'assets', 'js', 'main.js'))
    for f in os.listdir(os.path.join(SRC, 'assets', 'img')):
        shutil.copy(os.path.join(SRC, 'assets', 'img', f), os.path.join(out, 'assets', 'img', f))
    if variant == 'site':
        shutil.copytree(os.path.join(SRC, 'assets', 'fonts'), os.path.join(out, 'assets', 'fonts'), dirs_exist_ok=True)
        for f in ('favicon.ico', 'favicon.svg', 'apple-touch-icon.png'):
            shutil.copy(os.path.join(SRC, 'assets', f), os.path.join(out, f))
        shutil.copy(os.path.join(SRC, 'php', 'contact.php'), os.path.join(out, 'contact.php'))
        shutil.copy(os.path.join(SRC, 'php', '.htaccess'), os.path.join(out, '.htaccess'))
    written = []
    for page in PAGES:
        if variant == 'preview' and page['file'] == '404.html':
            continue
        ctx = Ctx(variant, page)
        body = page_body(page, ctx)
        p = ctx.prefix
        script = '<script src="%sassets/js/main.js?v=1" defer></script>\n' % p
        if variant == 'site':
            doc = head_site(page, ctx) + body + '\n' + script + '</body>\n</html>\n'
        else:
            is_main = page['file'] == 'index.html'
            doc = head_preview(page, is_main) + body + '\n' + script + ('' if is_main else '</body>\n</html>\n')
        open(os.path.join(out, page['file']), 'w', encoding='utf-8').write(doc)
        written.append(page['file'])
    if variant == 'site':
        urls = [pg['file'] for pg in PAGES if not pg.get('noindex') and pg['file'] not in ('mentions-legales.html', 'confidentialite.html')]
        sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for f in urls:
            loc = SITE_URL + '/' + ('' if f == 'index.html' else f)
            prio = '1.0' if f == 'index.html' else ('0.9' if f in ('guide-cool-roof.html', 'solutions.html', 'devis.html') else '0.7')
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
