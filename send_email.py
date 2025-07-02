import os
import smtplib
from email.message import EmailMessage
import pandas as pd

csv_path = "prijzen_s25_ultra.csv"

# Lees de csv en maak de tekst voor in de mail
try:
    df = pd.read_csv(csv_path)
    df_text = df.to_string(index=False)
except Exception as e:
    df_text = f"Kon CSV niet lezen: {e}"

msg = EmailMessage()
msg['Subject'] = 'Dagelijkse Prijzen S25 Ultra'
msg['From'] = os.environ.get('FROM_EMAIL')
msg['To'] = os.environ.get('TO_EMAIL')
msg.set_content(f"Hieronder de actuele prijzen:\n\n{df_text}")

with open(csv_path, 'rb') as f:
    msg.add_attachment(f.read(), maintype='text', subtype='csv', filename=os.path.basename(csv_path))

# Outlook/Office365 SMTP settings
smtp_server = 'smtp.office365.com'
smtp_port = 587

with smtplib.SMTP(smtp_server, smtp_port) as smtp:
    smtp.starttls()
    try:
        smtp.login(os.environ.get('SMTP_USER'), os.environ.get('SMTP_PASS'))
    except smtplib.SMTPAuthenticationError as e:
        print('SMTP login failed:', e)
        raise
    smtp.send_message(msg)
