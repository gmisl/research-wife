"""Send the generated weekly HTML report through an SMTP provider."""

from __future__ import annotations

import argparse
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/exports/weekly-email.html')
    args = parser.parse_args()

    host = os.environ['SMTP_HOST']
    port = int(os.environ.get('SMTP_PORT', '587'))
    username = os.environ['SMTP_USERNAME']
    password = os.environ['SMTP_PASSWORD']
    recipient = os.environ['EMAIL_RECIPIENT']
    subject = os.environ.get('EMAIL_SUBJECT', 'Organic EU meat research — weekly update')

    message = EmailMessage()
    message['From'] = username
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content('Open the attached HTML report in a browser.')
    message.add_alternative(Path(args.input).read_text(encoding='utf-8'), subtype='html')

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)
    print(f'Sent weekly report to {recipient}')


if __name__ == '__main__':
    main()
