# ML_OpenAI_WHISPER

Application locale de dictée et de transcription française basée sur OpenAI Whisper. Le navigateur enregistre ou envoie un fichier audio ; le serveur Flask le transcrit, applique un léger post-traitement puis conserve l'audio et le résultat localement.

## Distribution Windows recommandée

L'application est distribuée sous forme d'un `Setup.exe` Velopack. Python, Whisper, Torch, l'interface web et FFmpeg sont inclus dans l'installation. Le modèle Whisper est téléchargé une seule fois au premier lancement.

Les fichiers applicatifs remplaçables sont installés sous `%LOCALAPPDATA%\haleczander.DicteeCourriels\current`. Les données qui doivent survivre aux mises à jour et à une réinstallation restent dans une racine séparée :

```text
%LOCALAPPDATA%\DicteeCourriels\
  data\        # dictées, audios, transcriptions et logs
  certs\       # certificat HTTPS propre à ce PC
  models\      # modèle Whisper
  config.json  # host, port et HTTPS
```

Une nouvelle version est détectée au démarrage. L'interface permet de télécharger le delta, puis d'installer la mise à jour et de redémarrer. Le dossier `current` est remplacé par Velopack ; les données ci-dessus ne sont pas touchées.

### Construire l'installeur

Prérequis de build : Python 3.14, .NET SDK 10, `vpk` 1.2.0 et FFmpeg dans `vendor/ffmpeg/bin`.

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
dotnet tool install --global vpk --version 1.2.0
powershell -ExecutionPolicy Bypass -File .\deploy\release.ps1 -Version 0.1.0
```

Les artefacts sont écrits dans `Releases/`. Un tag `vX.Y.Z` déclenche également le workflow GitHub Actions de publication.

### Configurer le HTTPS du PC hôte

Le certificat et sa clé privée ne sont jamais intégrés à la release. Sur le PC qui héberge l'application :

```powershell
winget install --id FiloSottile.mkcert -e
powershell -ExecutionPolicy Bypass -File .\deploy\setup-https.ps1 -StateRoot "$env:LOCALAPPDATA\DicteeCourriels"
```

Importer ensuite le fichier `rootCA.pem` indiqué par le script sur les téléphones ou ordinateurs clients. Régénérer le certificat si l'adresse IP LAN du serveur change.

## Reprendre le développement après un `git pull`

Depuis la racine du dépôt, sous PowerShell :

```powershell
# Une seule fois sur une nouvelle machine (Python 3.10+ requis)
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Le projet requiert aussi **une distribution FFmpeg locale**. Le code cherche obligatoirement les exécutables sous `vendor/ffmpeg/bin/` :

```text
vendor/ffmpeg/bin/ffmpeg.exe
vendor/ffmpeg/bin/ffprobe.exe
```

`vendor/` est volontairement ignoré par Git : un `git pull` ne le récupère donc pas. Installer FFmpeg sous Windows avec :

```powershell
winget install --id Gyan.FFmpeg -e --source winget --accept-package-agreements --accept-source-agreements
```

Fermer puis rouvrir PowerShell. Pour le développement, créer ensuite une **jonction de dossier** (un lien vers l'installation locale, sans dupliquer FFmpeg) :

```powershell
$ffmpegBin = Split-Path -Parent (Get-Command ffmpeg).Source
New-Item -ItemType Directory -Force .\vendor\ffmpeg
New-Item -ItemType Junction -Path .\vendor\ffmpeg\bin -Target $ffmpegBin
```

Une jonction ne nécessite normalement pas les droits administrateur, contrairement à un lien symbolique Windows. La commande suppose que `vendor/ffmpeg/bin` n'existe pas déjà ; si ce chemin existe, vérifier son contenu avant de le remplacer. Confirmer la configuration :

```powershell
Test-Path .\vendor\ffmpeg\bin\ffmpeg.exe
Test-Path .\vendor\ffmpeg\bin\ffprobe.exe
```

Les deux commandes doivent retourner `True`. Le code utilise obligatoirement ce chemin `vendor/` ; avoir seulement `ffmpeg` dans le `PATH` ne suffit pas au démarrage.

Lancer ensuite le serveur de développement en HTTP :

```powershell
.\deploy\run.ps1
```

Ouvrir [http://localhost:8000](http://localhost:8000). Le premier lancement télécharge le modèle Whisper `turbo`, ce qui peut prendre un peu de temps. Le serveur n'est pas en rechargement automatique : arrêter avec `Ctrl+C`, puis relancer après une modification Python.

Raccourcis Windows équivalents :

```bat
install.bat
run.bat http
```

### Dépannage : PyTorch bloqué par Smart App Control

Si le démarrage échoue sur `import torch` avec le message `DLL load failed` et « une stratégie de contrôle d'application a bloqué ce fichier », Windows Smart App Control bloque une extension native de PyTorch, souvent `torch/_C.cpXXX-win_amd64.pyd`. Ce n'est pas un problème de FFmpeg ni une dépendance Python manquante ; recréer le venv ne le résout pas.

Sur un PC personnel, si tu fais confiance aux dépendances installées depuis ce projet, ouvrir **Sécurité Windows** → **Contrôle des applications et du navigateur** → **Paramètres Smart App Control**, puis choisir **Désactivé**. Fermer et rouvrir PowerShell avant de relancer le serveur.

Smart App Control ne permet pas d'autoriser seulement une application ou une DLL : il faut soit utiliser une version reconnue/signée, soit désactiver cette protection. Microsoft Defender reste indépendant et doit rester actif. Voir la [FAQ Microsoft Smart App Control](https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions).

## Les deux modes de lancement

| Besoin | Commande | URL |
| --- | --- | --- |
| Développement sur le PC | `.\deploy\run.ps1` | `http://localhost:8000` |
| Micro depuis un téléphone | `.\deploy\run.ps1 -Https` | `https://<IP-LAN>:8000` |

Le micro du navigateur nécessite HTTPS sur iPhone (et généralement hors de `localhost`). Le mode HTTPS attend `certs/local.pem` et `certs/local-key.pem`. Ils peuvent être créés avec [mkcert](https://github.com/FiloSottile/mkcert), puis le certificat racine doit être déclaré fiable sur le téléphone.

```powershell
mkcert -install
New-Item -ItemType Directory -Force certs
mkcert -key-file certs/local-key.pem -cert-file certs/local.pem localhost 127.0.0.1 <IP-LAN>
.\deploy\run.ps1 -Https
```

Pour lancer directement sans le script, il faut explicitement choisir HTTP, car `server.py` privilégie HTTPS par défaut :

```powershell
$env:APP_SSL = "0"
.\.venv\Scripts\python.exe server.py
```

## Où intervenir

| Élément | Fichier ou dossier |
| --- | --- |
| API Flask, WebSocket et démarrage du serveur | `server.py` |
| Interface navigateur | `static/index.html`, `static/app.js`, `static/styles.css` |
| Construction des dépendances et modèle Whisper (`turbo`, français) | `src/application/container.py` |
| Appel Whisper et conversion audio mono / 16 kHz | `src/adapters/transcription/whisper_transcribe_adapter.py` |
| Post-traitement de la dictée | `src/adapters/text/instruction_text_post_processor.py` |
| Cas d'usage : transcription, régénération, consultation, suppression | `src/application/use_cases/` |
| Persistance JSON et fichiers locaux | `src/adapters/persistence/`, `src/adapters/storage/` |

L'architecture suit une séparation simple : `domain` contient les entités, `application` les cas d'usage et ports, et `adapters` les implémentations techniques.

## Données locales et diagnostic

Les fichiers générés ne sont pas versionnés :

| Contenu | Emplacement |
| --- | --- |
| Index des dictées | `data/items.json` |
| Vocabulaire métier local | `data/vocabulary.json` |
| Audios envoyés/enregistrés | `data/audio/` |
| Transcriptions | `data/transcripts/` |
| Journal serveur et adaptateurs | `data/logs/` |

L'état du serveur est vérifiable via `GET /api/health`; il indique le modèle chargé et le périphérique utilisé (`cuda` si disponible, sinon `cpu`). Les autres routes utiles sont `GET /api/items`, `GET /api/jobs`, `POST /api/upload`, `POST /api/items/<id>/regenerate` et `DELETE /api/items/<id>`.

## Créer l'archive portable

Après avoir préparé FFmpeg et, si nécessaire, les certificats, créer une archive autonome :

```powershell
.\deploy\package-portable.ps1
```

Le script récupère FFmpeg depuis le `PATH` lorsqu'il est disponible, ou permet de préciser son emplacement :

```powershell
.\deploy\package-portable.ps1 -FfmpegSource "C:\chemin\vers\ffmpeg\bin"
```

Une archive déjà publiée est disponible ici :
<https://github.com/haleczander/ML_OpenAI_WHISPER/releases/latest/download/dictee_courriels.zip>
