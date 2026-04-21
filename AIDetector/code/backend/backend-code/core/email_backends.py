import smtplib
import ssl
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.utils.functional import cached_property


class MyEmailBackend(EmailBackend):
    def open(self):
        """
        Override the `open` method to disable SSL verification.
        """
        if self.connection:
            return False

        connection_params = {"local_hostname": "localhost"}  # 你可以设置本地主机名
        if self.timeout is not None:
            connection_params["timeout"] = self.timeout
        if self.use_ssl:
            # Create an SSL context with disabled verification
            context = ssl.create_default_context()
            context.check_hostname = False  # 禁用证书验证
            context.verify_mode = ssl.CERT_NONE  # 禁用证书验证
            connection_params["context"] = context

        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)
            if not self.use_ssl and self.use_tls:
                self.connection.starttls(context=self.ssl_context)
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
