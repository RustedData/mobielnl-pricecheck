import os
import smtplib
from email.message import EmailMessage
import pandas as pd
from email.utils import formataddr

def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def get_cheapest_options(today_df):
    today_df = today_df.copy()
    today_df['total'] = 24 * today_df['abonnement'] + today_df['aanbetaling']
    cheapest_256 = today_df[today_df['opslag'].str.contains('256')]
    cheapest_512 = today_df[today_df['opslag'].str.contains('512')]
    cheapest_256_row = cheapest_256.loc[cheapest_256['total'].idxmin()] if not cheapest_256.empty else None
    cheapest_512_row = cheapest_512.loc[cheapest_512['total'].idxmin()] if not cheapest_512.empty else None
    return cheapest_256_row, cheapest_512_row

def build_summary(los_prijs, cheapest_256_row, cheapest_512_row, today):
    summary = f"Datum: {today}\n"
    if los_prijs is not None:
        summary += f"Los toestel prijs (laagste): €{los_prijs:.2f}\n"
    if cheapest_256_row is not None:
        summary += (
            f"Goedkoopste 256GB: €{cheapest_256_row['total']:.2f} bij {cheapest_256_row['provider']} ({cheapest_256_row['kleur']})\n"
            f"Maandprijs: €{cheapest_256_row['abonnement']:.2f}, Aanbetaling: €{cheapest_256_row['aanbetaling']:.2f}, Toestelprijs: €{cheapest_256_row['toestelprijs']:.2f}\n"
        )
    if cheapest_512_row is not None:
        summary += (
            f"Goedkoopste 512GB: €{cheapest_512_row['total']:.2f} bij {cheapest_512_row['provider']} ({cheapest_512_row['kleur']})\n"
            f"Maandprijs: €{cheapest_512_row['abonnement']:.2f}, Aanbetaling: €{cheapest_512_row['aanbetaling']:.2f}, Toestelprijs: €{cheapest_512_row['toestelprijs']:.2f}\n"
        )
    if cheapest_256_row is None and cheapest_512_row is None:
        summary += "Geen abonnementen gevonden."
    return summary

def send_email(summary, csv_path):
    from_name = os.environ.get('FROM_NAME', 'PriceCheckApp').strip().replace('\n', '').replace('\r', '')
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
    smtp_server = 'smtp.gmail.com'
    smtp_port = 465
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
        smtp.login(os.environ.get('SMTP_USER'), os.environ.get('SMTP_PASS'))
        smtp.send_message(msg)

def main():
    load_env()
    csv_path = "prijzen_s25_ultra.csv"
    try:
        df = pd.read_csv(csv_path)
        today = str(pd.Timestamp.today().date())
        today_df = df[df['date'] == today]
        los_prijs = today_df['los_toestel'].min() if not today_df.empty else None
        cheapest_256_row, cheapest_512_row = get_cheapest_options(today_df)
        summary = build_summary(los_prijs, cheapest_256_row, cheapest_512_row, today)
    except Exception as e:
        summary = f"Kon samenvatting niet maken: {e}"
    # send_email(summary, csv_path)  # Email is gedeactiveerd
    print(summary)

if __name__ == '__main__':
    main()
