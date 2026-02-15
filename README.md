# STT_OpenAI_WHISPER

POC de transcription vocale avec OpenAI Whisper.

Ce depot utilise Codex pour aider au developpement et aux iterations rapides.

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

## Docker (test local rapide)

Prerequis:
- Docker Desktop
- Certificats presents dans `certs/local.pem` et `certs/local-key.pem`

Lancer:

```bash
docker compose up --build
```

Arreter:

```bash
docker compose down
```
