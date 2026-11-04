<?php
/**
 * ALBEDIA · envoi par e-mail d'une simulation faite avec le simulateur de la page d'accueil (#simulateur).
 *
 * Le calcul est fait dans le navigateur (assets/js/main.js). Ce script reçoit les paramètres choisis et les
 * résultats affichés, les contrôle (listes de valeurs autorisées, nombres bornés) puis envoie :
 *  - au visiteur, le récapitulatif de sa simulation (texte fixe : aucune saisie libre n'est reprise) ;
 *  - à ALBEDIA, une copie avec l'adresse du visiteur en « Répondre à ».
 * Fonctionne sur les hébergements web OVHcloud avec PHP (fonction mail()).
 * L'adresse d'expédition doit appartenir à un domaine rattaché à l'hébergement (albedia.eu).
 */
declare(strict_types=1);

const DESTINATAIRE  = 'contact@albedia.eu';
const EXPEDITEUR    = 'contact@albedia.eu';
const TELEPHONE     = '06 83 48 06 15';
const SITE          = 'https://albedia.eu';
const MAX_PAR_HEURE = 5;

date_default_timezone_set('Europe/Paris');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

$wantsJson = isset($_SERVER['HTTP_ACCEPT']) && strpos((string) $_SERVER['HTTP_ACCEPT'], 'application/json') !== false;

function repondre(bool $ok, string $erreur = ''): void
{
    global $wantsJson;
    if ($wantsJson) {
        http_response_code($ok ? 200 : 400);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['ok' => $ok, 'error' => $erreur], JSON_UNESCAPED_UNICODE);
    } else {
        header('Location: /#simulateur', true, 303);
    }
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    http_response_code(405);
    exit;
}

/* Champ piège : rempli uniquement par les robots. On fait comme si tout allait bien. */
if (!empty($_POST['website'])) {
    repondre(true);
}

/* Demande envoyée trop vite après l'ouverture de la page pour venir d'une personne. */
$delai = isset($_POST['elapsed']) && $_POST['elapsed'] !== '' ? (int) $_POST['elapsed'] : -1;
if ($delai >= 0 && $delai < 3000) {
    repondre(false, 'Merci de prendre quelques secondes pour vérifier votre simulation avant de la recevoir.');
}

/* Limite d'envois par adresse IP. */
$ip = (string) ($_SERVER['REMOTE_ADDR'] ?? 'inconnue');
$fichierLimite = rtrim(sys_get_temp_dir(), '/\\') . '/albedia_simu_' . hash('sha256', $ip);
$maintenant = time();
$envois = [];
if (is_file($fichierLimite)) {
    $contenu = (string) @file_get_contents($fichierLimite);
    foreach (explode(',', $contenu) as $t) {
        if ((int) $t > $maintenant - 3600) {
            $envois[] = (int) $t;
        }
    }
}
if (count($envois) >= MAX_PAR_HEURE) {
    repondre(false, 'Plusieurs simulations ont déjà été envoyées depuis cette connexion. Réessayez dans une heure ou écrivez-nous à ' . DESTINATAIRE . '.');
}

function champ(string $cle, int $max): string
{
    $v = isset($_POST[$cle]) && is_string($_POST[$cle]) ? $_POST[$cle] : '';
    $v = strip_tags($v);
    $v = (string) preg_replace('/[\x00-\x1F\x7F]/u', '', $v);
    return trim(mb_substr($v, 0, $max));
}

function entier(string $cle, int $min, int $max): ?int
{
    $v = champ($cle, 12);
    if (!preg_match('/^[0-9]{1,9}$/', $v)) {
        return null;
    }
    $n = (int) $v;
    return ($n >= $min && $n <= $max) ? $n : null;
}

function decimal(string $cle, float $min, float $max): ?float
{
    $v = str_replace(',', '.', champ($cle, 20));
    if (!preg_match('/^[0-9]{1,7}(\.[0-9]{1,12})?$/', $v)) {
        return null;
    }
    $n = (float) $v;
    return ($n >= $min && $n <= $max) ? $n : null;
}

/* Arrondis identiques à ceux de la page. */
function arrondi(float $x): float
{
    if ($x >= 100000) {
        return round($x / 1000) * 1000;
    }
    if ($x >= 10000) {
        return round($x / 100) * 100;
    }
    if ($x >= 1000) {
        return round($x / 10) * 10;
    }
    return round($x);
}

function nb(float $n): string
{
    return number_format($n, 0, ',', ' ');
}

function dec(float $n): string
{
    return rtrim(rtrim(number_format($n, 2, ',', ' '), '0'), ',');
}

$LIBELLES = [
    'pays' => ['FR' => 'France', 'CH' => 'Suisse', 'IT' => 'Italie', 'ES' => 'Espagne'],
    'secteur' => [
        'industrie' => 'Industrie', 'logistique' => 'Logistique et entreposage', 'distribution' => 'Commerce',
        'tertiaire' => 'Bureaux et tertiaire', 'collectivites' => 'Collectivité ou équipement public', 'agricole' => 'Agricole',
    ],
    'couverture' => [
        'bac-acier' => 'bac acier', 'bitume' => 'étanchéité bitumineuse', 'membrane' => 'membrane synthétique',
        'beton' => 'béton', 'fibres-ciment' => 'fibres-ciment',
    ],
    'aspect' => ['sombre' => 'sombre', 'clair' => 'grise ou claire', 'reflechissant' => 'déjà blanche et réfléchissante'],
    'etat' => ['bon' => 'en bon état', 'reprises' => 'à reprendre par endroits', 'degradee' => 'dégradée'],
    'clim' => ['totale' => 'tout le bâtiment', 'partielle' => 'une partie du bâtiment', 'aucune' => 'aucune'],
    'chauffage' => ['pac' => 'pompe à chaleur', 'gaz' => 'gaz ou fioul', 'electrique' => 'électrique', 'aucun' => 'aucun'],
    'conso_source' => ['estimation' => 'estimée par le simulateur', 'declaree' => 'indiquée par vous'],
    'cee_statut' => [
        'ok' => '',
        'etranger' => 'non applicable : les CEE sont un dispositif français. D’autres aides peuvent exister en Suisse, en Italie et en Espagne.',
        'secteur' => 'non éligible à la fiche BAT-EN-112, qui concerne les bâtiments tertiaires à usage commercial. Nous vérifions lors de l’étude si un autre dispositif s’applique à votre site.',
        'reflechissant' => 'non éligible : la fiche BAT-EN-112 exige une toiture sans revêtement réflectif avant les travaux.',
        'sans-clim' => 'non éligible : la toiture doit couvrir un volume fermé et climatisé.',
        'chauffage' => 'non éligible : la fiche BAT-EN-112 exige un chauffage et une climatisation assurés par une pompe à chaleur.',
    ],
];

const ILLISIBLE = 'La simulation n’a pas pu être lue. Rechargez la page, refaites votre simulation et réessayez.';

$email = trim((string) preg_replace('/[\r\n]+/', ' ', champ('email', 160)));
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    repondre(false, 'Indiquez une adresse e-mail valide.');
}

$s = [];
foreach (array_keys($LIBELLES) as $cle) {
    $v = champ($cle, 20);
    if (!array_key_exists($v, $LIBELLES[$cle])) {
        repondre(false, ILLISIBLE);
    }
    $s[$cle] = $v;
}

$codePostal = $s['pays'] === 'FR' ? champ('code_postal', 5) : '';
if (!preg_match('/^[0-9]{5}$/', $codePostal)) {
    $codePostal = '';
}
$zone = $s['pays'] === 'FR' ? champ('zone', 2) : '';
if (!in_array($zone, ['H1', 'H2', 'H3'], true)) {
    $zone = '';
}

$longueur = decimal('longueur', 5, 1000);
$largeur  = decimal('largeur', 5, 1000);
$hauteur  = decimal('hauteur', 2, 60);
$surface  = entier('surface', 25, 1000000);
$niveaux  = entier('niveaux', 1, 20);
$conso    = entier('conso', 0, 50000000);
$consoEte = entier('conso_ete', 0, 50000000);
$prix     = decimal('prix', 0.1, 0.4);
$gainKwh  = entier('gain_kwh', 0, 50000000);
$gainEur  = entier('gain_eur', 0, 20000000);
$ceeEur   = $s['cee_statut'] === 'ok' ? entier('cee_eur', 0, 5000000) : 0;

if ($longueur === null || $largeur === null || $hauteur === null || $surface === null || $niveaux === null
    || $conso === null || $consoEte === null || $consoEte > $conso || $prix === null || $gainKwh === null
    || $gainEur === null || $ceeEur === null) {
    repondre(false, ILLISIBLE);
}

/* ---------------------------------------------------------------- récapitulatif */
$lib = function (string $cle) use ($s, $LIBELLES): string {
    return $LIBELLES[$cle][$s[$cle]];
};

$localisation = $lib('pays');
if ($s['pays'] === 'FR') {
    if ($codePostal !== '' && $zone !== '') {
        $localisation .= ', code postal ' . $codePostal . ', zone climatique ' . $zone;
    } else {
        $localisation .= ', zone climatique H2 retenue par défaut';
    }
}

$batiment = "VOTRE BÂTIMENT\n"
    . '- Localisation : ' . $localisation . "\n"
    . '- Type de bâtiment : ' . $lib('secteur') . "\n"
    . '- Dimensions : ' . dec($longueur) . ' m × ' . dec($largeur) . ' m, hauteur ' . dec($hauteur) . ' m'
    . ($niveaux > 1 ? ' (' . $niveaux . ' niveaux)' : ' (plain-pied)') . "\n"
    . '- Surface de toiture : ' . nb($surface) . " m², sans ombrage\n"
    . '- Toiture : ' . $lib('couverture') . ', ' . $lib('aspect') . ', ' . $lib('etat') . "\n"
    . '- Climatisation : ' . $lib('clim') . "\n"
    . '- Chauffage : ' . $lib('chauffage') . "\n"
    . '- Consommation annuelle : ' . nb($conso) . ' kWh (' . $lib('conso_source') . ')'
    . ($consoEte > 0 ? ', dont environ ' . nb(arrondi($consoEte)) . ' kWh de climatisation l’été' : '') . "\n"
    . '- Prix du kWh : ' . number_format($prix, 2, ',', ' ') . " € hors TVA\n";

if ($s['aspect'] === 'reflechissant') {
    $economies = 'gain faible : votre toiture est déjà réfléchissante. Un nettoyage peut lui rendre une partie de sa réflectance.';
} elseif ($s['clim'] === 'aucune') {
    $economies = 'pas de facture de climatisation à réduire, mais moins de surchauffe sous la toiture en été.';
} else {
    $economies = 'environ ' . nb(arrondi($gainEur)) . ' € par an, soit environ ' . nb(arrondi($gainKwh))
        . ' kWh de climatisation en moins chaque année.';
}
if ($s['cee_statut'] === 'ok') {
    $prime = 'environ ' . nb(arrondi($ceeEur)) . ' €, sous réserve d’éligibilité (fiche BAT-EN-112, sur la base de '
        . '8,70 € le MWh cumac, indice de prix des CEE classiques de juin 2026). Le montant versé dépend du financeur.';
} else {
    $prime = $LIBELLES['cee_statut'][$s['cee_statut']];
}

$attention = [];
if ($s['etat'] === 'degradee') {
    $attention[] = 'Toiture dégradée : une réfection d’étanchéité s’impose avant tout revêtement.';
} elseif ($s['etat'] === 'reprises') {
    $attention[] = 'Quelques reprises à prévoir avant l’application, chiffrées lors de la visite.';
}
if ($s['couverture'] === 'fibres-ciment') {
    $attention[] = 'Fibres-ciment : repérage de l’amiante obligatoire avant travaux sur les bâtiments construits avant le 1er juillet 1997.';
}

$estimation = "VOTRE ESTIMATION\n"
    . '- Économies estimées : ' . $economies . "\n"
    . '- Prime CEE estimée : ' . $prime . "\n"
    . ($attention ? "\nÀ NOTER\n- " . implode("\n- ", $attention) . "\n" : '');

$avertissement = "Estimation indicative et non contractuelle, pour une toiture sans ombrage, établie à partir de valeurs "
    . "moyennes publiées (US EPA, fiche CEE BAT-EN-112, Observatoire de l’immobilier durable) et des hypothèses "
    . "détaillées sous le simulateur : " . SITE . "/#simulateur\n"
    . "Le gain réel dépend de votre bâtiment : c’est ce qu’évalue notre étude préalable.\n";

$signature = "ALBEDIA, revêtements réfléchissants pour toitures professionnelles\n"
    . DESTINATAIRE . ' · ' . TELEPHONE . ' · ' . SITE . "\n";

$corpsVisiteur = "Bonjour,\n\n"
    . "Merci d’avoir utilisé le simulateur d’ALBEDIA. Voici le récapitulatif de votre simulation.\n\n"
    . $batiment . "\n"
    . $estimation . "\n"
    . $avertissement . "\n"
    . "Pour faire étudier votre toiture, répondez simplement à ce message ou faites votre demande sur "
    . SITE . "/devis.html\n\n"
    . "Bien cordialement,\n\n"
    . $signature . "\n"
    . "Vous recevez ce message parce que votre adresse a été saisie dans le simulateur du site albedia.eu. "
    . "Si vous n’êtes pas à l’origine de cette demande, ignorez-le : aucun autre message ne vous sera envoyé à ce sujet.\n";

$corpsAlbedia = "Nouvelle simulation envoyée depuis albedia.eu\n"
    . str_repeat('-', 48) . "\n"
    . "E-mail du visiteur : $email\n\n"
    . $batiment . "\n"
    . $estimation . "\n"
    . str_repeat('-', 48) . "\n"
    . 'Envoyé le ' . date('d/m/Y à H:i') . "\n"
    . "Le visiteur a reçu le même récapitulatif. Répondez directement à ce message pour lui écrire.\n";

$entetes = function (string $nom, string $repondreA): string {
    return implode("\r\n", [
        'From: ' . mb_encode_mimeheader($nom, 'UTF-8', 'Q') . ' <' . EXPEDITEUR . '>',
        'Reply-To: ' . $repondreA,
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: 8bit',
    ]);
};

$sujetAlbedia = '[Simulation] ' . $lib('secteur') . ' · ' . nb($surface) . ' m²'
    . ($codePostal !== '' ? ' · ' . $codePostal : ($s['pays'] !== 'FR' ? ' · ' . $lib('pays') : ''));
$sujetVisiteur = 'Votre simulation ALBEDIA : économies et prime CEE';

$envoiAlbedia = mail(DESTINATAIRE, mb_encode_mimeheader($sujetAlbedia, 'UTF-8', 'Q'), $corpsAlbedia, $entetes('Site ALBEDIA', $email));
$envoiVisiteur = $envoiAlbedia && mail($email, mb_encode_mimeheader($sujetVisiteur, 'UTF-8', 'Q'), $corpsVisiteur, $entetes('ALBEDIA', DESTINATAIRE));

if ($envoiAlbedia && $envoiVisiteur) {
    $envois[] = $maintenant;
    @file_put_contents($fichierLimite, implode(',', $envois), LOCK_EX);
    repondre(true);
}
repondre(false, 'L’envoi n’a pas abouti. Réessayez ou écrivez-nous directement à ' . DESTINATAIRE . '.');
