#!/usr/bin/env python3
"""Ajoute ou met à jour une photo du site (nécessite Pillow : pip install pillow).

Utilisation (depuis la racine du dépôt) :
  python3 _src/photos.py <image.jpg> <nom-court> --alt "Texte alternatif" --auteur "Nom du photographe" \
      --compte <identifiant-unsplash-du-photographe> --source https://unsplash.com/photos/<identifiant> \
      [--cadrage "50% 50%"]

Crée _src/assets/img/photos/<nom-court>-640.webp, -1280.webp et -1920.webp (selon la taille de l'image
d'origine) et enregistre la photo dans _src/pages/photos.json : texte alternatif, cadrage (object-position,
utilisé quand la photo est recadrée à l'affichage), largeurs, auteur et liens.
Dans les pages : {{img:nom-court}} dans une <figure class="photo">, ou {{bg:nom-court}} en fond d'en-tête.
La liste des crédits des mentions légales se met à jour seule au build.
Ne jamais utiliser une photo Unsplash+ ni la présenter comme une réalisation d'ALBEDIA.
"""
import argparse, json, os, sys

from PIL import Image, ImageOps

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(SRC, 'assets', 'img', 'photos')
REGISTRE = os.path.join(SRC, 'pages', 'photos.json')
LARGEURS = (640, 1280, 1920)
QUALITE = 70


def main():
    ap = argparse.ArgumentParser(description='Ajoute une photo au site ALBEDIA.')
    ap.add_argument('image')
    ap.add_argument('nom')
    ap.add_argument('--alt', required=True)
    ap.add_argument('--auteur', required=True)
    ap.add_argument('--compte', required=True, help='identifiant Unsplash du photographe, sans @')
    ap.add_argument('--source', required=True, help='lien de la photo sur Unsplash')
    ap.add_argument('--cadrage', default='50% 50%')
    a = ap.parse_args()

    im = ImageOps.exif_transpose(Image.open(a.image)).convert('RGB')
    os.makedirs(DEST, exist_ok=True)
    faites = []
    for w in LARGEURS:
        if w > im.width:
            break
        h = round(im.height * w / im.width)
        out = im if w == im.width else im.resize((w, h), Image.LANCZOS)
        out.save(os.path.join(DEST, '%s-%d.webp' % (a.nom, w)), 'WEBP', quality=QUALITE, method=6)
        faites.append(w)
    if not faites:
        sys.exit('Image trop petite : 640 px de large au minimum.')

    registre = json.load(open(REGISTRE, encoding='utf-8')) if os.path.isfile(REGISTRE) else {}
    registre[a.nom] = {
        'alt': a.alt, 'pos': a.cadrage, 'widths': faites, 'ratio': [im.width, im.height],
        'author': a.auteur, 'author_url': 'https://unsplash.com/@' + a.compte, 'url': a.source,
    }
    with open(REGISTRE, 'w', encoding='utf-8') as f:
        json.dump(registre, f, ensure_ascii=False, indent=1)
    print(a.nom, im.size, faites)


if __name__ == '__main__':
    main()
