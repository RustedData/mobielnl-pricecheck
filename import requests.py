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
        le = soup.find(string=lambda t: t and label in t)
        if le:
            # Zoek prijs in de buurt van het label
            prijs = None
            for e in le.parent.next_elements:
                if not isinstance(e, str):
                    txt = e.get_text(strip=True) if hasattr(e, 'get_text') else ''
                    m = re.search(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?", txt)
                    if m:
                        try:
                            prijs = float(m.group().replace('.', '').replace(',', '.'))
                            break
                        except Exception:
                            pass
            if prijs is not None:
                prijzen[p] = prijs
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

# Prijzen ophalen
los_url = "https://www.mobiel.nl/smartphone/samsung/galaxy-s25-ultra/512gb-titanium-black"
abonnement_url = "https://www.mobiel.nl/smartphone/samsung/galaxy-s25-ultra/met-abonnement?kleur=titanium-black&opslagcapaciteit=512gb&data=2147483647-&minuten=100-&bijbetaling=-700&sorteren=meest-voordelig"

los_prijs = get_los_toestel_prijs(los_url)
providers, prijzen, fees = get_provider_prices_and_fees(abonnement_url)

# Vodafone klantkorting toepassen
if 'Vodafone' in fees:
    fees['Vodafone'] = round(fees['Vodafone'] - 7.5, 2)

# Data verzamelen per provider
data = {'date': [date.today()], 'los_toestel': [los_prijs]}
for p in providers:
    toestel = prijzen.get(p)
    abbo = fees.get(p)
    data[f'{p}_toestel'] = [toestel]
    data[f'{p}_abonnement'] = [abbo]
    data[f'{p}_abonnement_zonder_toestel'] = [round(abbo - toestel/24, 2) if toestel is not None and abbo is not None else None]

# Kolommen sorteren: eerst los_toestel, dan per provider alle waardes
cols = ['date', 'los_toestel'] + [f'{p}_{s}' for p in providers for s in ['toestel','abonnement','abonnement_zonder_toestel']]
df_new = pd.DataFrame(data)[cols]

# CSV bijwerken: overschrijf regel als datum bestaat, anders voeg toe
csv_path = "prijzen_s25_ultra.csv"
try:
    df_old = pd.read_csv(csv_path, on_bad_lines='skip')
    df_old = df_old[df_old['date'] != str(date.today())]
    df = pd.concat([df_old, df_new], ignore_index=True)
    df.to_csv(csv_path, index=False)
except FileNotFoundError:
    df = df_new
    df.to_csv(csv_path, index=False)

