import base64
import hmac
import os


class AuthMixin:
    def __init__(self, *args, user=None, password=None, **kwargs):
        if user is None and password is None:
            env_auth = (os.environ.get('FILER_AUTH')
                        or os.environ.get('DL_AUTH'))
            if env_auth:
                user, _, password = env_auth.partition(':')
        if not user or not password:
            raise ValueError(
                "Basic Auth credentials required: use --user 'name:pass' "
                "or set FILER_AUTH='name:pass' (DL_AUTH is also accepted)")
        self.auth_user = user
        self.auth_pass = password
        super().__init__(*args, **kwargs)

    def _authenticated(self):
        header = self.headers.get('Authorization', '')
        if not header.startswith('Basic '):
            return False
        try:
            decoded = base64.b64decode(header[6:]).decode('utf-8')
            user, _, password = decoded.partition(':')
        except Exception:
            return False
        return (hmac.compare_digest(user, self.auth_user)
                and hmac.compare_digest(password, self.auth_pass))
    def require_auth(self):
        if not self._authenticated():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="downloads"')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return False
        return True

