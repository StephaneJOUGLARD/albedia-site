<?php
/**
 * ALBEDIA · traitement du formulaire de demande de devis (devis.html).
 *
 * Fonctionne sur les hébergements web OVHcloud avec PHP (fonction mail()).
 * L'adresse d'expédition doit appartenir à un domaine rattaché à l'hébergement (albedia.eu).
 * Pour recevoir les demandes ailleurs, modifiez DESTINATAIRE ci-dessous.
 */
declare(strict_types=1);

const DESTINATAIRE = 'contact@albedia.eu';
const EXPEDITEUR   = 'contact@albedia.eu';
const NOM_SITE     = 'Site ALBEDIA';
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
        header('Location: devis.html#' . ($ok ? 'merci' : 'erreur'), true, 303);
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

/* Formulaire envoyé trop vite pour avoir été rempli par une personne. */
$delai = isset($_POST['elapsed']) && $_POST['elapsed'] !== '' ? (int) $_POST['elapsed'] : -1;
if ($delai >= 0 && $delai < 3000) {
    repondre(false, 'Merci de prendre quelques secondes pour remplir le formulaire avant de l’envoyer.');
}

/* Limite d'envois par adresse IP. */
$ip = (string) ($_SERVER['REMOTE_ADDR'] ?? 'inconnue');
$fichierLimite = rtrim(sys_get_temp_dir(), '/\\') . '/albedia_devis_' . hash('sha256', $ip);
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
    repondre(false, 'Plusieurs demandes ont déjà été envoyées depuis cette connexion. Réessayez dans une heure ou écrivez-nous à ' . DESTINATAIRE . '.');
}

function champ(string $cle, int $max): string
{
    $v = isset($_POST[$cle]) && is_string($_POST[$cle]) ? $_POST[$cle] : '';
    $v = strip_tags($v);
    $v = (string) preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $v);
    return trim(mb_substr($v, 0, $max));
}

function ligne(string $v): string
{
    return trim((string) preg_replace('/[\r\n]+/', ' ', $v));
}

function parmi(string $v, array $autorises): string
{
    return in_array($v, $autorises, true) ? $v : '';
}

$nom        = ligne(champ('nom', 100));
$entreprise = ligne(champ('entreprise', 120));
$email      = ligne(champ('email', 160));
$telephone  = ligne(champ('telephone', 30));
$secteur    = parmi(ligne(champ('secteur', 60)), [
    'Industrie', 'Logistique et entreposage', 'Commerce et distribution', 'Bureaux et tertiaire',
    'Collectivité ou équipement public', 'Agricole', 'Autre',
]);
$surface    = ligne(champ('surface', 10));
$toiture    = parmi(ligne(champ('toiture', 60)), [
    'Bac acier', 'Étanchéité bitumineuse', 'Membrane synthétique (PVC, TPO, EPDM)', 'Béton',
    'Fibres-ciment', 'Plusieurs types', 'Je ne sais pas',
]);
$codePostal = ligne(champ('code_postal', 10));
$clim       = parmi(ligne(champ('climatisation', 20)), ['Oui', 'En partie', 'Non', 'Je ne sais pas']);
$message    = champ('message', 5000);

if ($nom === '' || $entreprise === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    repondre(false, 'Merci d’indiquer votre nom, votre entreprise et une adresse e-mail valide.');
}
if ($telephone !== '' && !preg_match('/^[0-9 +().\-]{6,30}$/', $telephone)) {
    repondre(false, 'Le numéro de téléphone indiqué n’est pas valide.');
}
if ($surface !== '' && !preg_match('/^[0-9]{1,7}$/', $surface)) {
    $surface = '';
}

$corps = "Nouvelle demande de devis envoyée depuis albedia.eu\n"
    . str_repeat('-', 48) . "\n"
    . "Nom : $nom\n"
    . "Entreprise : $entreprise\n"
    . "E-mail : $email\n"
    . 'Téléphone : ' . ($telephone !== '' ? $telephone : 'non indiqué') . "\n\n"
    . 'Secteur : ' . ($secteur !== '' ? $secteur : 'non indiqué') . "\n"
    . 'Surface de toiture : ' . ($surface !== '' ? $surface . ' m²' : 'non indiquée') . "\n"
    . 'Type de toiture : ' . ($toiture !== '' ? $toiture : 'non indiqué') . "\n"
    . 'Code postal du bâtiment : ' . ($codePostal !== '' ? $codePostal : 'non indiqué') . "\n"
    . 'Bâtiment climatisé : ' . ($clim !== '' ? $clim : 'non indiqué') . "\n\n"
    . "Projet :\n" . ($message !== '' ? $message : '(aucun message)') . "\n\n"
    . str_repeat('-', 48) . "\n"
    . 'Envoyé le ' . date('d/m/Y à H:i') . "\n"
    . "Répondez directement à ce message pour écrire à $nom.\n";

$sujet = '[Devis] ' . $entreprise . ($secteur !== '' ? ' – ' . $secteur : '');

$entetes = [
    'From: ' . mb_encode_mimeheader(NOM_SITE, 'UTF-8', 'Q') . ' <' . EXPEDITEUR . '>',
    'Reply-To: ' . $email,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
];

$envoye = mail(DESTINATAIRE, mb_encode_mimeheader($sujet, 'UTF-8', 'Q'), $corps, implode("\r\n", $entetes));

if ($envoye) {
    $envois[] = $maintenant;
    @file_put_contents($fichierLimite, implode(',', $envois), LOCK_EX);
    repondre(true);
}
repondre(false, 'L’envoi n’a pas abouti. Réessayez ou écrivez-nous directement à ' . DESTINATAIRE . '.');
