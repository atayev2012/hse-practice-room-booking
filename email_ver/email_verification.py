import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import config
import logging
import random

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - [%(levelname)s] - %(message)s')

# Email class
class Email:
    def __init__(self, recipient_email: str, recipient_name: str = "Пользователь"):
        self.recipient_email = recipient_email
        self.recipient_name = recipient_name
        self.subject = "Бронирование Аудиторий - подтверждение адреса электронной почты"

        self.__generate_code()
        self.__construct_body()

    def __construct_body(self):
        with open("email_ver/email_template.html") as f:
            self.body = f.read().replace("{code}", self.code).replace("{User's Name}", self.recipient_name)

    def __generate_code(self):
        """
        Generates a random 6-digit number as a string, including leading zeros.
        """
        self.code = f"{random.randint(0, 999999):06d}"

    async def send_email(self):
        try:
            # Create MIME message
            logging.info(f"Preparing email to be sent - details: {self.recipient_email} - {self.subject}")
            msg = MIMEMultipart()
            msg['From'] = config.EMAIL
            msg['To'] = self.recipient_email
            msg['Subject'] = self.subject
            msg.attach(MIMEText(self.body, 'html'))

            # Connect to SMTP server
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.starttls()  # Secure connection
                server.login(config.EMAIL, config.EMAIL_PASSWORD)
                server.sendmail(config.EMAIL, self.recipient_email, msg.as_string())
                logging.info("Email was sent successfully!")
        except Exception as e:
            logging.error(f"An error occurred in email sending: {e}")



if __name__ == "__main__":
    # Example usage
    new_email = Email("atayev2012@gmail.com", "New test", "This is a 2nd test email!")
