import django.core.mail.backends.smtp
import settings
import smtplib

# The SDA mail server (which is the primary one used by this code) has a weird authentication method
class SDASSLEmailBackend(django.core.mail.backends.smtp.EmailBackend):
  def __init__(self, **kwargs):
    super(SDASSLEmailBackend, self).__init__(**kwargs)

  def open(self):
    if self.connection:
      return False
    try:
      self.connection = smtplib.SMTP_SSL(self.host, self.port)
      self.connection.set_debuglevel(1)
      self.connection.connect(self.host, self.port)
      self.connection.ehlo()
      self.connection.esmtp_features["auth"] = "LOGIN PLAIN"
      if self.username and self.password:
          self.connection.login(self.username, self.password)
      return True
    except:
      if not self.fail_silently:
        raise