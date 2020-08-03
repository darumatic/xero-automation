import smtplib
import os
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr


class XeroEmailSender:
    @staticmethod
    def send_via_smpt(result, errors=None):
        from_addr = os.environ["SENDER"]
        to_addr = os.environ["RECEIVER"]
        print("Sending validation report to: " + to_addr)
        password = os.environ["SENDGRID_API_KEY"]
        smtp_server = "smtp.sendgrid.net"
        username = "apikey"
        subject = "Monthly validation report"

        if errors:
            errors = XeroEmailSender.format_errors(errors)

        msg = MIMEText(result + "\n" + errors, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = formataddr((str(Header('Xero validation report', 'utf-8')), 'qq2841864141@gmail.com'))

        server = smtplib.SMTP(smtp_server, 587)
        server.set_debuglevel(1)
        server.login(username, password)
        try:
            server.sendmail(from_addr, [to_addr], msg.as_string())
            print("Validation email send succeed!")
        except Exception as e:
            print("Sending validation report failed! :")
            print(e)
        server.quit()
        print("*" * 80)

    @staticmethod
    def format_errors(errors):
        counter = 1
        error_str = ""
        for error in errors:
            if len(errors[error]) > 0:
                error_str += str(error) + ":\n"
            for item in errors[error]:
                if isinstance(item, str):
                    error_str += str(counter) + ". " + item + "\n"
                else:
                    error_str += str(counter) + ". " + str(item)[2:-1] + "\n"
                counter += 1
        return error_str
