import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import date

def get_los_toestel_prijs(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    elem = soup.find(string=lambda t: t and 'Los toestel' in t)
    if elem:
        span = next((s for s in elem.parent.next_elements if getattr(s, 'name', None) == 'span'), None)
        if span:
            prijs = span.text.strip()
            try:
                return float(re.sub(r'[^\d,\.]', '', prijs).replace('.', '').replace(',', '.'))
            except Exception:
                pass
    return None

def get_provider_prices_and_fees(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    pat = re.compile(r"Samsung Galaxy S25 Ultra \+ ([A-Za-z0-9]+)")
    providers = sorted(set(m.group(1) for m in pat.finditer(soup.text)))
    prijzen, fees = {}, {}
    for p in providers:
        label = f"Samsung Galaxy S25 Ultra + {p}"
        # Zoek de juiste <tr> voor deze provider
        tr = None
        for row in soup.find_all("tr"):
            first_td = row.find("td")
            if first_td and label in first_td.get_text():
                tr = row
                break
        toestelprijs = aanbetaling = None
        if tr:
            tds = tr.find_all("td")
            if len(tds) >= 3:
                def parse_price(td):
                    span = td.find("span", class_="Price__Amount-sc-ecffd5cc-2")
                    if span:
                        txt = span.text.strip()
                        try:
                            return float(re.sub(r'[^\d,\.]', '', txt).replace('.', '').replace(',', '.'))
                        except Exception:
                            return None
                    return None
                toestelprijs = parse_price(tds[1])  # Dit is nu de totale toestelkosten
                aanbetaling = parse_price(tds[2])
                if toestelprijs is not None:
                    prijzen[p] = toestelprijs  # GEEN aanbetaling meer optellen
                if toestelprijs is not None:
                    prijzen[f'{p}_toestelprijs'] = toestelprijs
                if aanbetaling is not None:
                    prijzen[f'{p}_aanbetaling'] = aanbetaling
        # Zoek maandelijkse fee
        img = soup.find('img', alt=p)
        if img:
            n = img
            while n:
                n = n.find_next()
                if n and n.has_attr('class') and any('Bottom__MonthlyFee' in c for c in n['class']):
                    spans = n.find_all('span')
                    if len(spans) >= 3:
                        euro, delim, cent = spans[0].text.strip(), spans[1].text.strip(), spans[2].text.strip()
                        if cent == '-' or not cent:
                            cent = '00'
                        if euro and cent and delim == ',':
                            try:
                                fees[p] = float(f"{euro}.{cent}")
                            except Exception:
                                pass
                    break
    return providers, prijzen, fees

def build_abonnement_urls():
    base_url = "https://www.mobiel.nl/smartphone/samsung/galaxy-s25-ultra/met-abonnement"
    kleuren = [
        "titanium-black",
        "titanium-silver-blue",
        "titanium-gray",
        "titanium-white-silver"
    ]
    opslag_varianten = ["512gb", "256gb"]
    urls = []
    for kleur in kleuren:
        for opslag in opslag_varianten:
            url = (
                f"{base_url}?kleur={kleur}&opslagcapaciteit={opslag}"
                f"&data=2147483647-&minuten=2147483647-&bijbetaling=-700&sorteren=meest-voordelig"
            )
            urls.append({"url": url, "kleur": kleur, "opslag": opslag})
    return urls

# --- Abonnement URLS ---
abonnement_urls = build_abonnement_urls()

# Los toestel prijzen ophalen voor 512GB en 256GB
los_url_512 = "https://www.mobiel.nl/smartphone/samsung/galaxy-s25-ultra/512gb-titanium-black"
los_url_256 = "https://www.mobiel.nl/smartphone/samsung/galaxy-s25-ultra/256gb-titanium-black"
los_prijs_512 = get_los_toestel_prijs(los_url_512)
los_prijs_256 = get_los_toestel_prijs(los_url_256)

all_rows = []

for abbo_info in abonnement_urls:
    url = abbo_info["url"]
    kleur = abbo_info["kleur"]
    opslag = abbo_info["opslag"]
    providers, prijzen, fees = get_provider_prices_and_fees(url)
    # Vodafone klantkorting toepassen
    if 'Vodafone' in fees:
        fees['Vodafone'] = round(fees['Vodafone'] - 7.5, 2)
    # Kies juiste los toestel prijs per opslag
    if opslag == "512gb":
        los_prijs = los_prijs_512
    elif opslag == "256gb":
        los_prijs = los_prijs_256
    else:
        los_prijs = None
    for p in providers:
        toestelprijs = prijzen.get(f'{p}_toestelprijs')
        aanbetaling = prijzen.get(f'{p}_aanbetaling')
        abbo = fees.get(p)
        abbo_zonder_toestel = None
        kredietbedrag = None
        if toestelprijs is not None and aanbetaling is not None:
            kredietbedrag = toestelprijs - aanbetaling
        if abbo is not None and toestelprijs is not None and aanbetaling is not None:
            abbo_zonder_toestel = round(abbo - ((toestelprijs - aanbetaling) / 24), 2)
        row = {
            'date': date.today(),
            'kleur': kleur,
            'opslag': opslag,
            'provider': p,
            'los_toestel': los_prijs,
            'kredietbedrag': kredietbedrag,
            'abonnement': abbo,
            'abonnement_zonder_toestel': abbo_zonder_toestel,
            'toestelprijs': toestelprijs,
            'aanbetaling': aanbetaling
        }
        all_rows.append(row)

# DataFrame van alle rows
if all_rows:
    df_new = pd.DataFrame(all_rows)
    csv_path = "prijzen_s25_ultra.csv"
    # Houd alleen unieke rijen per dag, provider, kleur, opslag
    df_new.sort_values(['date', 'provider', 'kleur', 'opslag', 'abonnement'], inplace=True)
    df_new = df_new.drop_duplicates(subset=['date', 'provider', 'kleur', 'opslag'], keep='first')
    try:
        df_old = pd.read_csv(csv_path, on_bad_lines='skip')
        # Voeg ontbrekende kolommen toe aan df_old
        for col in df_new.columns:
            if col not in df_old.columns:
                df_old[col] = None
        for col in df_old.columns:
            if col not in df_new.columns:
                df_new[col] = None
        df_old = df_old[df_new.columns]
        df_new = df_new[df_new.columns]
        df = pd.concat([df_old, df_new], ignore_index=True)
        # Forceer consistente types voor alle kolommen
        df['date'] = df['date'].astype(str)
        df['kleur'] = df['kleur'].astype(str)
        df['opslag'] = df['opslag'].astype(str)
        df['provider'] = df['provider'].astype(str)
        for col in ['los_toestel', 'kredietbedrag', 'abonnement', 'abonnement_zonder_toestel', 'toestelprijs', 'aanbetaling']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        # Verwijder dubbele rijen op date, provider, kleur, opslag
        df = df.drop_duplicates(subset=['date', 'provider', 'kleur', 'opslag'], keep='first')
        # Verwijder exacte dubbele rijen (alle kolommen gelijk)
        df = df.drop_duplicates(keep='first')
        df.to_csv(csv_path, index=False)
    except FileNotFoundError:
        df_new.to_csv(csv_path, index=False)

