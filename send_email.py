import os
import smtplib
from email.message import EmailMessage
import pandas as pd
from email.utils import formataddr

# Laad .env variabelen als ze bestaan (voor lokaal gebruik)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

csv_path = "prijzen_s25_ultra.csv"

# Lees de csv en maak een samenvatting voor vandaag
try:
    df = pd.read_csv(csv_path)
    today = str(pd.Timestamp.today().date())
    row = df[df['date'] == today].iloc[0]
    los_prijs = row['los_toestel']
    # Zoek alle kolommen die eindigen op '_toestel' en '_abonnement'
    abbo_cols = [c for c in df.columns if c.endswith('_toestel') or c.endswith('_abonnement')]
    # Vind goedkoopste totaalprijs abonnement (toestel + 24*abonnement)
    min_total = None
    min_provider = None
    min_abbo = None
    min_toestel = None
    for p in set(c.split('_')[0] for c in abbo_cols if '_toestel' in c):
        toestel = row.get(f'{p}_toestel')
        abbo = row.get(f'{p}_abonnement')
        if pd.notnull(toestel) and pd.notnull(abbo):
            total = toestel + 24 * abbo
            if min_total is None or total < min_total:
                min_total = total
                min_provider = p
                min_abbo = abbo
                min_toestel = toestel
    if min_total is not None:
        summary = (
            f"Datum: {today}\n"
            f"Los toestel prijs: €{los_prijs:.2f}\n"
            f"Goedkoopste abonnement totaal (toestel + 24x abbo): €{min_total:.2f} bij {min_provider}\n"
            f"Toestelprijs bij goedkoopste provider: €{min_toestel:.2f}\n"
            f"Maandprijs goedkoopste abonnement: €{min_abbo:.2f}"
        )
    else:
        summary = f"Datum: {today}\nLos toestel prijs: €{los_prijs:.2f}\nGeen abonnementen gevonden."
except Exception as e:
    summary = f"Kon samenvatting niet maken: {e}"

from_name = os.environ.get('FROM_NAME', 'Riks Mama').strip().replace('\n', '').replace('\r', '')
from_email = os.environ.get('FROM_EMAIL', '').strip().replace('\n', '').replace('\r', '')
to_name = os.environ.get('TO_NAME', '').strip().replace('\n', '').replace('\r', '')
to_email = os.environ.get('TO_EMAIL', '').strip().replace('\n', '').replace('\r', '')

msg = EmailMessage()
msg['Subject'] = 'Dagelijkse Prijzen S25 Ultra'
msg['From'] = formataddr((from_name, from_email))
msg['To'] = formataddr((to_name, to_email))
msg.set_content(f"{summary}\n\nDe volledige tabel staat in de bijlage.")

with open(csv_path, 'rb') as f:
    msg.add_attachment(f.read(), maintype='text', subtype='csv', filename=os.path.basename(csv_path))

# Gmail SMTP settings
smtp_server = 'smtp.gmail.com'
smtp_port = 465

with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
    smtp.login(os.environ.get('SMTP_USER'), os.environ.get('SMTP_PASS'))
    smtp.send_message(msg)
