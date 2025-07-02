import os
import smtplib
from email.message import EmailMessage
import pandas as pd
from email.utils import formataddr

csv_path = "prijzen_s25_ultra.csv"

# Lees de csv en maak de tekst voor in de mail
try:
    df = pd.read_csv(csv_path)
    df_text = df.to_string(index=False)
except Exception as e:
    df_text = f"Kon CSV niet lezen: {e}"

from_name = os.environ.get('FROM_NAME', 'PriceCheckApp')
from_email = os.environ.get('FROM_EMAIL')
to_name = os.environ.get('TO_NAME', '')
to_email = os.environ.get('TO_EMAIL')

msg = EmailMessage()
msg['Subject'] = 'Dagelijkse Prijzen S25 Ultra'
msg['From'] = formataddr((from_name, from_email))
msg['To'] = formataddr((to_name, to_email))
msg.set_content(f"Hieronder de actuele prijzen:\n\n{df_text}")

with open(csv_path, 'rb') as f:
    msg.add_attachment(f.read(), maintype='text', subtype='csv', filename=os.path.basename(csv_path))

# Gmail SMTP settings
smtp_server = 'smtp.gmail.com'
smtp_port = 465

with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
    smtp.login(os.environ.get('SMTP_USER'), os.environ.get('SMTP_PASS'))
    smtp.send_message(msg)
