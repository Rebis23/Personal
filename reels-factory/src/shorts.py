"""I Reel finiscono anche su YouTube Shorts.

Lorenzo, 25/09: "puoi postare tutti i vecchi video anche su yt shorts?"

Le clip sono gia pronte: 1080x1920 verticali, fra i 20 e i 75 secondi. Il
limite degli Shorts e tre minuti, quindi YouTube le riconosce come Shorts
da sole — non c'e niente da segnalare, basta caricarle.

QUELLO CHE SERVE, E PERCHE E' PIU' NOIOSO DI UNA CHIAVE API. Caricare un
video non si puo fare con una chiave: serve l'autorizzazione OAuth del
proprietario del canale. Tre segreti, tutti e tre da fare una volta sola:

    YT_CLIENT_ID · YT_CLIENT_SECRET · YT_REFRESH_TOKEN

E c'e una trappola che va detta prima e non dopo: se il progetto su Google
Cloud resta in stato "Testing", il refresh token SCADE DOPO SETTE GIORNI.
La fabbrica funzionerebbe una settimana e poi smetterebbe senza un errore
evidente. Il consent screen va messo "In production".

La quota invece non e un problema: cento caricamenti al giorno di partenza,
e le clip da recuperare sono trentotto.
"""

import json
import mimetypes
import os
import time
from pathlib import Path

import requests

TOKEN = "https://oauth2.googleapis.com/token"
CARICA = ("https://www.googleapis.com/upload/youtube/v3/videos"
          "?uploadType=multipart&part=snippet,status")

# 22 = "People & Blogs". E la categoria giusta per contenuto parlato di un
# canale personale; YouTube la pretende obbligatoria.
CATEGORIA = "22"


def configurato() -> bool:
    return all(os.environ.get(k, "").strip()
               for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def _accesso() -> str | None:
    """Scambia il refresh token con un token d'accesso, che dura un'ora."""
    r = requests.post(TOKEN, data={
        "client_id": os.environ["YT_CLIENT_ID"].strip(),
        "client_secret": os.environ["YT_CLIENT_SECRET"].strip(),
        "refresh_token": os.environ["YT_REFRESH_TOKEN"].strip(),
        "grant_type": "refresh_token",
    }, timeout=60)
    if r.status_code != 200:
        # IL CASO DA RICONOSCERE A COLPO D'OCCHIO. "invalid_grant" qui vuol
        # dire quasi sempre una cosa sola: il progetto e rimasto in
        # "Testing" e il refresh token e scaduto dopo sette giorni.
        print(f"  ⚠️ Token di YouTube rifiutato ({r.status_code}): {r.text[:300]}")
        if "invalid_grant" in r.text:
            print("  ⚠️ Probabile causa: il consent screen su Google Cloud e "
                  "ancora in 'Testing' e il refresh token e scaduto dopo 7 "
                  "giorni. Va messo 'In production' e rifatta l'autorizzazione.")
        return None
    return r.json().get("access_token")


def descrizione(hook: str, titolo_video: str) -> str:
    """Due righe: di cosa parla, e da dove viene."""
    return (f"{hook}\n\n"
            f"Estratto da «{titolo_video}» — il video intero e sul canale.\n\n"
            f"#shorts")


def carica(clip: Path, *, hook: str, titolo_video: str,
           privacy: str = "public") -> str | None:
    """Carica una clip come Short. Torna l'id del video, o None."""
    if not configurato():
        print("  ⚠️ YouTube non configurato: servono YT_CLIENT_ID, "
              "YT_CLIENT_SECRET e YT_REFRESH_TOKEN")
        return None
    token = _accesso()
    if token is None:
        return None

    # Il titolo dello Short e l'aggancio: e gia scritto per fermare lo
    # scroll, e sta sotto i 100 caratteri che YouTube accetta.
    meta = {
        "snippet": {"title": hook[:100],
                    "description": descrizione(hook, titolo_video),
                    "categoryId": CATEGORIA},
        "status": {"privacyStatus": privacy,
                   "selfDeclaredMadeForKids": False},
    }
    tipo = mimetypes.guess_type(clip.name)[0] or "video/mp4"

    for tentativo in (1, 2, 3):
        try:
            with clip.open("rb") as f:
                r = requests.post(
                    CARICA,
                    headers={"Authorization": f"Bearer {token}"},
                    files={
                        "metadata": ("metadata.json", json.dumps(meta),
                                     "application/json"),
                        "media": (clip.name, f, tipo),
                    },
                    timeout=900,
                )
        except requests.RequestException as e:
            print(f"  ⚠️ Caricamento su YouTube, tentativo {tentativo}/3: {e}")
            if tentativo < 3:
                time.sleep(tentativo * 10)
            continue

        if r.status_code in (200, 201):
            vid = r.json().get("id")
            print(f"  ▶️ Short caricato: https://youtube.com/shorts/{vid}")
            return vid

        print(f"  ⚠️ YouTube ha risposto {r.status_code}: {r.text[:300]}")
        if r.status_code == 403 and "quota" in r.text.lower():
            print("  ⚠️ Quota giornaliera finita: si riprende domani.")
            return None
        if r.status_code < 500:
            return None                      # colpa nostra: riprovare e inutile
        if tentativo < 3:
            time.sleep(tentativo * 10)
    return None
