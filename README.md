# Velox API

Version API (sans interface graphique) de l'app yt-dlp. Toute la logique PyQt5
a été retirée ; les mêmes fonctionnalités sont maintenant des endpoints HTTP.

## Installation locale

```bash
pip install -r requirements.txt
```

⚠️ `ffmpeg` n'est **pas** installable via pip — c'est un binaire système
(nécessaire pour merger vidéo+audio, extraire l'audio, embarquer les
miniatures/métadonnées). Installe-le via ton gestionnaire de paquets :
`apt install ffmpeg` (Debian/Ubuntu), `brew install ffmpeg` (macOS), etc.

## Lancement local

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Documentation interactive (Swagger) : http://localhost:8000/docs

## Déploiement sur Render

Le `Dockerfile` fourni installe `ffmpeg` via `apt-get` puis les dépendances
Python — c'est la façon fiable d'avoir ffmpeg disponible sur Render (le
runtime Python natif ne permet pas d'installer de paquets système).

1. Pousse ce dossier (`app.py`, `requirements.txt`, `Dockerfile`, `render.yaml`) sur un repo Git.
2. Sur Render : **New → Blueprint**, connecte le repo. `render.yaml` configure
   automatiquement un service Docker avec un disque persistant monté sur `/data`.
   - Sans blueprint, crée un **Web Service** classique, choisis **Docker** comme
     runtime, et ajoute manuellement un disque persistant (`/data`) + la variable
     d'env `VELOX_DATA_DIR=/data`.
3. Render détecte automatiquement le `Dockerfile` et build l'image.

Le disque persistant est important : sans lui, tout ce qui est écrit sur le
disque du conteneur (fichiers téléchargés, historique, `.velox_settings.json`)
**disparaît à chaque redéploiement/restart**. Avec `VELOX_DATA_DIR=/data`
pointé sur le disque monté, ces données survivent.

Une fois déployé, récupère les fichiers téléchargés via `GET /files` (liste)
puis `GET /files/{nom}` (téléchargement).

## Fonctionnement général

Les téléchargements sont asynchrones : chaque appel de démarrage
(`/download`, `/batch`, `/audio`, `/playlist`) renvoie immédiatement un
`job_id`. On suit ensuite la progression avec `GET /jobs/{job_id}`
(statut, %, vitesse, ETA, dernières lignes de log) jusqu'à ce que
`status` passe à `done`, `error` ou `cancelled`.

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| GET | `/status` | Vérifie que yt-dlp est disponible + sa version |
| POST | `/download` | Démarre un téléchargement vidéo simple |
| POST | `/batch` | Démarre un téléchargement en lot (plusieurs URLs) |
| POST | `/audio` | Extrait l'audio d'une vidéo |
| GET | `/playlist/info?url=...` | Titre + nombre de vidéos d'une playlist |
| POST | `/playlist` | Démarre le téléchargement d'une playlist (vidéo ou audio) |
| GET | `/jobs/{job_id}` | Statut / progression / logs d'un job |
| GET | `/jobs` | Liste tous les jobs connus |
| POST | `/jobs/{job_id}/cancel` | Annule un job en cours |
| GET | `/history` | Historique des téléchargements + compteurs |
| DELETE | `/history` | Vide l'historique |
| GET | `/settings` | Chemin actuel vers l'exécutable yt-dlp |
| POST | `/settings/path` | Change le chemin vers yt-dlp |
| POST | `/settings/update` | `yt-dlp -U` |
| POST | `/settings/pip-install` | `pip install -U yt-dlp` |
| GET | `/files` | Liste les fichiers téléchargés sur le serveur |
| GET | `/files/{nom}` | Télécharge un fichier précis |

## Exemple

```bash
# démarrer un téléchargement
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=XXXX", "quality": "1080p"}'
# → {"job_id": "..."}

# suivre la progression
curl http://localhost:8000/jobs/<job_id>
```

## Ce qui a changé par rapport à la version desktop

- Toute la couche PyQt5 (fenêtres, sidebar, cartes, thème sombre...) a été supprimée.
- Les `QThread` sont remplacés par des `threading.Thread` classiques.
- La persistance (historique, chemin yt-dlp) reste dans le même fichier
  `~/.velox_settings.json`.
- Les mêmes options yt-dlp sont exposées (qualité, format, cookies,
  sous-titres, miniature, métadonnées, limite de vitesse, etc.).
