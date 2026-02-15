# STT_FASTER_WHISPER

POC de transcription vocale avec `faster-whisper` (plus rapide et plus leger sur CPU).

Ce depot utilise Codex pour aider au developpement et aux iterations rapides.

## Scripts

- `main.py`: transcription batch d'un fichier audio.
- `live_transcribe.py`: transcription en flux tendu depuis le micro.
- `server.py`: serveur local + front pour dictee.

## Installation

```
pip install -r requirements.txt
```

## Reglages perf (machines peu puissantes)

Par defaut, le projet utilise un modele `large-v3` avec `int8_float32` sur CPU.

Variables utiles:

- `WHISPER_MODEL`: `tiny`, `base`, `small`, `medium`, `large-v3`
- `WHISPER_DEVICE`: `cpu` ou `cuda` (par defaut: auto)
- `WHISPER_COMPUTE_TYPE`: `int8`, `int8_float16`, `int8_float32`, `float16`, `float32` (par defaut: auto)
- `WHISPER_CPU_THREADS`: nombre de threads CPU (0 = auto)

Exemple (Windows PowerShell):

```
$env:WHISPER_MODEL="large-v3"
$env:WHISPER_DEVICE="cpu"
$env:WHISPER_COMPUTE_TYPE="int8"
python server.py
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
