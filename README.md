# STT_OpenAI_WHISPER

POC de transcription vocale avec OpenAI Whisper.

Ce depot utilise Codex pour aider au developpement et aux iterations rapides.

## Telechargement direct

- ZIP portable (latest): https://github.com/haleczander/ML_OpenAI_WHISPER/releases/latest/download/dictee_courriels.zip

## Architecture (Clean)

- `src/domain`: entites metier (`Item`).
- `src/application`: ports + use cases (orchestration metier) + container d'injection.
- `src/adapters/persistence`: persistence JSON des items.
- `src/adapters/storage`: persistence fichiers sur le filesystem.
- `src/adapters/transcription`: implementation Whisper du port de transcription (normalisation audio mono/16k avant inference).
- `src/adapters/text`: post-processing texte ultra-leger par regex (instructions de dictee -> ponctuation/mise en page).
- `server.py`: API Flask/WebSocket qui expose les use cases (`upload/transcribe`, `get`, `list`, `delete`).

## Scripts

- `server.py`: serveur local + front pour dictee.

## Installation

```bash
pip install -r requirements.txt
```

## Mode portable Windows

Prerequis:
- Python 3.10+ installe et accessible via `py` ou `python`
- ffmpeg: soit installe dans le `PATH`, soit embarque dans `vendor/ffmpeg/bin/ffmpeg.exe`
- Certificats HTTPS: soit deja presents dans `certs/`, soit embarques dans `deploy/certs/local.pem` et `deploy/certs/local-key.pem`

Installation:

```powershell
.\deploy\install.ps1
```

Ou en double-clic Windows:

```bat
install.bat
```

Packaging "portable" (sans installation systeme ffmpeg/certs):
- Deposer `ffmpeg.exe` dans `vendor/ffmpeg/bin/ffmpeg.exe`
- Deposer les certs dans `deploy/certs/local.pem` et `deploy/certs/local-key.pem`
- Lancer `.\deploy\install.ps1` (copie auto des certs vers `certs/`)

Lancement:

```powershell
# HTTP (desktop simple)
.\deploy\run.ps1

# HTTPS (mobile/micro navigateur)
.\deploy\run.ps1 -Https
```

Ou en double-clic Windows:

```bat
run.bat
run.bat http
```

## App locale (serveur + front)

```bash
python server.py
```

Puis ouvrir `http://localhost:8000`.

## HTTPS (obligatoire sur iPhone pour le micro)

Tu dois servir en HTTPS avec un certificat de confiance.

Option A (mkcert recommande) :
- Installer mkcert sur la machine qui heberge le serveur.
- Generer les certs :

```bash
mkcert -install
mkdir certs
mkcert -key-file certs/local-key.pem -cert-file certs/local.pem localhost 127.0.0.1 <IP-LAN>
```

- Copier le certificat racine mkcert sur l'iPhone et l'ajouter comme cert de confiance.

Puis lancer :

```bash
python server.py
```

Et ouvrir `https://<IP-LAN>:8000` sur l'iPhone.
