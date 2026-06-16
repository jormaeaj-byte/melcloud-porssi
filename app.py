
 
import requests
import os
import time
from datetime import datetime, timezone

# --- Asetukset (muutetaan Render.com:ssa ympäristömuuttujina) ---
MELCLOUD_EMAIL = os.environ.get("MELCLOUD_EMAIL")
MELCLOUD_PASSWORD = os.environ.get("MELCLOUD_PASSWORD")
DEVICE_ID = os.environ.get("DEVICE_ID")          # Laitteen ID, katso alla
BUILDING_ID = os.environ.get("BUILDING_ID")      # Rakennuksen ID, katso alla

KALLIS_HINTA = float(os.environ.get("KALLIS_HINTA", "10"))   # snt/kWh
HALPA_HINTA = float(os.environ.get("HALPA_HINTA", "5"))      # snt/kWh
NORMAALI_LAMPO = float(os.environ.get("NORMAALI_LAMPO", "21"))
SAASTO_LAMPO = float(os.environ.get("SAASTO_LAMPO", "17"))
TARKISTUS_VALI = int(os.environ.get("TARKISTUS_VALI", "3600"))  # sekuntia


def melcloud_kirjaudu():
    """Kirjautuu MELCloudiin ja palauttaa context key -tunnuksen."""
    url = "https://app.melcloud.com/Mitsubishi.Wifi.Client.Resources/Login/ClientLogin"
    data = {
        "Email": MELCLOUD_EMAIL,
        "Password": MELCLOUD_PASSWORD,
        "Language": 17,
        "AppVersion": "1.26.2.0",
        "Persist": True,
    }
    r = requests.post(url, json=data)
    r.raise_for_status()
    token = r.json()["LoginData"]["ContextKey"]
    print(f"MELCloud kirjautuminen onnistui")
    return token


def hae_nordpool_hinta():
    """Hakee kuluvan tunnin spot-hinnan Suomesta (snt/kWh sis. ALV)."""
    r = requests.get("https://api.spot-hinta.fi/TodayAndDayForward", timeout=10)
    r.raise_for_status()
    data = r.json()
    tunti = datetime.now().hour
    for item in data:
        item_tunti = datetime.fromisoformat(item["DateTime"]).hour
        if item_tunti == tunti:
            hinta = item["PriceWithTax"] * 100  # €/MWh → snt/kWh
            return round(hinta, 2)
    return None


def hae_laite_tiedot(token):
    """Hakee laitteen nykyiset asetukset MELCloudista."""
    url = f"https://app.melcloud.com/Mitsubishi.Wifi.Client.Resources/Device/Get"
    headers = {"X-MitsContextKey": token}
    params = {"id": DEVICE_ID, "buildingID": BUILDING_ID}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def aseta_lampotila(token, laite_data, lampotila):
    """Asettaa lämpöpumpulle uuden lämpötilan."""
    url = "https://app.melcloud.com/Mitsubishi.Wifi.Client.Resources/Device/SetAta"
    headers = {"X-MitsContextKey": token, "Content-Type": "application/json"}

    # Päivitä vain lämpötila, muut asetukset säilyvät
    laite_data["SetTemperature"] = lampotila
    laite_data["HasPendingCommand"] = True

    r = requests.post(url, headers=headers, json=laite_data)
    r.raise_for_status()
    print(f"Lämpötila asetettu: {lampotila}°C")


def tarkista_ja_ohjaa():
    """Päälogiikka: hae hinta ja ohjaa pumppu sen mukaan."""
    print(f"\n--- Tarkistus {datetime.now().strftime('%H:%M')} ---")

    hinta = hae_nordpool_hinta()
    if hinta is None:
        print("Hintaa ei saatu – ei muutoksia")
        return

    print(f"Sähkön hinta nyt: {hinta} snt/kWh")

    token = melcloud_kirjaudu()
    laite = hae_laite_tiedot(token)
    nykyinen = laite.get("SetTemperature")
    print(f"Nykyinen asetus: {nykyinen}°C")

    if hinta > KALLIS_HINTA:
        if nykyinen != SAASTO_LAMPO:
            print(f"Hinta korkea ({hinta} > {KALLIS_HINTA}) → säästölämpötila {SAASTO_LAMPO}°C")
            aseta_lampotila(token, laite, SAASTO_LAMPO)
        else:
            print("Säästölämpötila jo päällä, ei muutosta")
    else:
        if nykyinen != NORMAALI_LAMPO:
            print(f"Hinta ok ({hinta} ≤ {KALLIS_HINTA}) → normaali {NORMAALI_LAMPO}°C")
            aseta_lampotila(token, laite, NORMAALI_LAMPO)
        else:
            print("Normaalilämpötila jo päällä, ei muutosta")


def main():
    print("Pörssisähköohjaus käynnistyy...")
    print(f"  Kallis hinta: >{KALLIS_HINTA} snt/kWh → {SAASTO_LAMPO}°C")
    print(f"  Normaali hinta: ≤{KALLIS_HINTA} snt/kWh → {NORMAALI_LAMPO}°C")
    print(f"  Tarkistusväli: {TARKISTUS_VALI}s\n")

    while True:
        try:
            tarkista_ja_ohjaa()
        except Exception as e:
            print(f"Virhe: {e}")
        time.sleep(TARKISTUS_VALI)


if __name__ == "__main__":
    main()
```

Klikkaa **Commit new file**.

---
 

