#!/usr/bin/env python3
"""Prende il refresh token di YouTube. Si lancia UNA volta, sul Mac.

    python3 autorizza-youtube.py

Chiede le due cose che Google ti ha dato (client ID e client secret), apre
il browser, tu approvi, e stampa il refresh token da mettere nei segreti
di GitHub.

DUE COSE CHE VEDRAI E CHE NON SONO GUASTI:

· «Google hasn't verified this app». E' normale per un'app tua, non
  verificata. Fai "Advanced" (o "Avanzate") e poi "Go to ... (unsafe)".
  Verifica e pubblicazione sono due cose diverse: un'app si pubblica anche
  senza verifica, e funziona.

· Il browser dira che la pagina non e sicura o simili: sta parlando con
  questo script sul tuo computer, non con internet.

Usa solo la libreria standard di Python: niente da installare.
"""
import http.server
import json
import secrets
import socketserver
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

PORTA = 8765
RINVIO = f"http://localhost:{PORTA}"
AUTORIZZA = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
# Solo il permesso di caricare. Niente lettura, niente gestione del canale:
# se questa chiave finisse in mano sbagliata potrebbe solo caricare video.
AMBITO = "https://www.googleapis.com/auth/youtube.upload"

codice = {}


class Orecchio(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        codice.update({k: v[0] for k, v in q.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        fatto = "code" in codice
        self.wfile.write(
            ("<h2>Fatto, puoi chiudere questa pagina.</h2>" if fatto else
             f"<h2>Qualcosa non ha funzionato: {codice}</h2>").encode())
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *a):
        pass


def main() -> int:
    print("\n=== Autorizzazione YouTube per la Reels Factory ===\n")
    print("Le trovi su console.cloud.google.com, in Google Auth Platform ->")
    print("Clients, dentro il client OAuth di tipo 'Desktop app'.\n")
    cid = input("Client ID:     ").strip()
    csec = input("Client secret: ").strip()
    if not cid or not csec:
        print("\n⛔ Servono tutti e due.")
        return 1

    stato = secrets.token_urlsafe(16)
    url = AUTORIZZA + "?" + urllib.parse.urlencode({
        "client_id": cid,
        "redirect_uri": RINVIO,
        "response_type": "code",
        "scope": AMBITO,
        "access_type": "offline",
        # SENZA QUESTO NON ARRIVA IL REFRESH TOKEN. Google lo manda solo la
        # prima volta che autorizzi; se hai gia autorizzato una volta e non
        # forzi il consenso, torna solo il token d'accesso che dura un'ora
        # e la fabbrica non puo rinnovarsi da sola.
        "prompt": "consent",
        "state": stato,
    })

    print("\nApro il browser. Accedi con l'account CHE GESTISCE IL CANALE.")
    print("Se compare «Google hasn't verified this app»: Advanced -> Go to "
          "(unsafe). E' normale, non e un errore.\n")
    print(f"Se il browser non si apre da solo, incolla questo:\n{url}\n")
    webbrowser.open(url)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORTA), Orecchio) as s:
        s.serve_forever()

    if codice.get("state") != stato:
        print("\n⛔ Risposta non coerente con la richiesta: rifiuto.")
        return 1
    if "code" not in codice:
        print(f"\n⛔ Google non ha dato il codice: {codice}")
        return 1

    dati = urllib.parse.urlencode({
        "code": codice["code"], "client_id": cid, "client_secret": csec,
        "redirect_uri": RINVIO, "grant_type": "authorization_code",
    }).encode()
    try:
        with urllib.request.urlopen(
                urllib.request.Request(TOKEN, data=dati), timeout=60) as r:
            fuori = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        corpo = getattr(e, "read", lambda: b"")().decode(errors="replace")
        print(f"\n⛔ Scambio del codice fallito: {e}\n{corpo[:400]}")
        return 1

    rt = fuori.get("refresh_token")
    if not rt:
        print("\n⛔ Nessun refresh token. Succede se avevi gia autorizzato "
              "questo client: revoca l'accesso su "
              "myaccount.google.com/permissions e rilancia.")
        return 1

    print("\n" + "=" * 62)
    print("FATTO. Metti questi tre in GitHub, nel repo Personal:")
    print("Settings -> Secrets and variables -> Actions -> New repository secret")
    print("=" * 62)
    print(f"\nYT_CLIENT_ID\n{cid}\n")
    print(f"YT_CLIENT_SECRET\n{csec}\n")
    print(f"YT_REFRESH_TOKEN\n{rt}\n")
    print("=" * 62)
    print("Poi scrivimi 'fatto' e faccio partire il recupero dei 38 Reel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
