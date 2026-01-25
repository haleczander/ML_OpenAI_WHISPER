# STT_OpenAI_WHISPER

POC de transcription vocale avec OpenAI Whisper.

Ce depot utilise Codex pour aider au developpement et aux iterations rapides.

## Scripts

- `main.py`: transcription batch d'un fichier audio.
- `live_transcribe.py`: transcription en flux tendu depuis le micro.
- `server.py`: serveur local + front pour dictee.

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python main.py
python live_transcribe.py
```

## App locale (serveur + front)

```
python server.py
```

Puis ouvrir `http://localhost:8000`.

## HTTPS (obligatoire sur iPhone pour le micro)

Tu dois servir en HTTPS avec un certificat de confiance.

Option A (mkcert recommande) :
- Installer mkcert sur la machine qui heberge le serveur.
- Generer les certs :

```
mkcert -install
mkdir certs
mkcert -key-file certs/local-key.pem -cert-file certs/local.pem localhost 127.0.0.1 <IP-LAN>
```

- Copier le certificat racine mkcert sur l'iPhone et l'ajouter comme cert de confiance.

Puis lancer :

```
python server.py
```

Et ouvrir `https://<IP-LAN>:8000` sur l'iPhone.
