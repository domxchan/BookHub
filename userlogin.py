import re
import hashlib
import random
from string import letters

SECRET = "!!!thisisourlittlesecret###"
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")


def valid_username(username):
    return username and USER_RE.match(username)


def valid_password(password):
    return password and PASSWORD_RE.match(password)


def valid_verify(verify, password):
    return verify == password


def valid_email(email):
    return not email or EMAIL_RE.match(email)


def valid_details(username, password, verify, email):
    error_username = "invalid username!" if not valid_username(username) else ""
    error_password = "invalid password!" if not valid_password(password) else ""
    error_verify = "passwords don't match" if not valid_verify(verify, password) else ""
    error_email = "invalid email!" if not valid_email(email) else ""
    found_error = error_username or error_password or error_verify or error_email
    return error_username, error_password, error_verify, error_email, found_error


def make_salt(length=5):
    return ''.join(random.choice(letters) for x in xrange(length))


def create_pw_hash(name, password, salt=None):
    if not salt:
        salt = make_salt()
    pw_hash = hashlib.sha256("%s%s%s" % (name, password, salt)).hexdigest()
    return "%s|%s" % (salt, pw_hash)


def validate_login(name, password, pw_hash):
    salt = pw_hash.split("|")[0]
    return pw_hash == create_pw_hash(name, password, salt)


def make_user_cookie(name):
    return "%s|%s" % (name, hashlib.sha256("%s%s" % (name, SECRET)).hexdigest())


def validate_cookie(ck):
    name = ck.split("|")[0]
    if ck == make_user_cookie(name):
        return name
