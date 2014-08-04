import os
import jinja2
import webapp2
import csv
import logging
import userlogin
import sys
sys.path.insert(0, 'libs')
import items
import crawler
from datetime import date
from google.appengine.ext import ndb
from google.appengine.ext.ndb import metadata
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import images
import re
from google.appengine.api.urlfetch import DeadlineExceededError
from google.appengine.api.urlfetch import DownloadError
import facebook  
from google.appengine.ext import db
from webapp2_extras import sessions
import urllib2


FACEBOOK_APP_ID = "5750566261"
FACEBOOK_APP_SECRET = "b60e7bc379b7f627a701f9bbb043ea88"



DEBUG = True
DEFAULT_INTELLIGENCE_NAME = 'default_intelligence_name'
DEFAULT_USER_NAME = 'user_name'
DEFAULT_BOOKSHELF_NAME = 'bookshelf_name'
CSV_FILE = 'intelligence.csv'

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=False)


config = {}
config['webapp2_extras.sessions'] = dict(secret_key='a3320p9rupjoiwj23')


class User2(db.Model):
    id = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    name = db.StringProperty(required=True)
    profile_url = db.StringProperty(required=True)
    access_token = db.StringProperty(required=True)


class BaseHandler(webapp2.RequestHandler):
    """Provides access to the active Facebook user in self.current_user

The property is lazy-loaded on first access, using the cookie saved
by the Facebook JavaScript SDK to determine the user ID of the active
user. See http://developers.facebook.com/docs/authentication/ for
more information.
"""
    @property
    def current_user(self):
        if self.session.get("user"):
            # User is logged in
            return self.session.get("user")
        else:
            # Either used just logged in or just saw the first page
            # We'll see here
            cookie = facebook.get_user_from_cookie(self.request.cookies,
                                                   FACEBOOK_APP_ID,
                                                   FACEBOOK_APP_SECRET)
            if cookie:
                # Okay so user logged in.
                # Now, check to see if existing user
                user = User2.get_by_key_name(cookie["uid"])
                if not user:
                    # Not an existing user so get user info
                    graph = facebook.GraphAPI(cookie["access_token"])
                    profile = graph.get_object("me")
                    user = User2(
                        key_name=str(profile["id"]),
                        id=str(profile["id"]),
                        name=profile["name"],
                        profile_url=profile["link"],
                        access_token=cookie["access_token"]
                    )
                    user.put()
                elif user.access_token != cookie["access_token"]:
                    user.access_token = cookie["access_token"]
                    user.put()
                # User is now logged in
                self.session["user"] = dict(
                    name=user.name,
                    profile_url=user.profile_url,
                    id=user.id,
                    access_token=user.access_token
                )
                return self.session.get("user")
        return None

    def dispatch(self):
        """
This snippet of code is taken from the webapp2 framework documentation.
See more at
http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html

"""
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        """
This snippet of code is taken from the webapp2 framework documentation.
See more at
http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html

"""
        return self.session_store.get_session()





def user_key(user_name=DEFAULT_USER_NAME, **kw):
    return ndb.Key('User', user_name, **kw)

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    pw_hash = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def by_name(cls, name):
        user = None
        if name:
            user = memcache.get("user:%s" % name)

            if not user:
                logging.error("User DB Query")
                users = User.query(User.name==name, ancestor=user_key()).fetch(1)
                if users:
                    user = users[0]
                    memcache.set("user:%s" % name, user)
            return user

    @classmethod
    def login(cls, name, password):
        user = cls.by_name(name)
        if user and userlogin.validate_login(name, password, user.pw_hash):
            return user

    @classmethod
    def update(cls, user):
        logging.error("User DB Put")
        user.put()
        memcache.set("user:%s" % user.name, user)


def intelligence_key(intelligence_name=DEFAULT_INTELLIGENCE_NAME, **kw):
    """Constructs a Datastore key for an Intelligence entity with intelligence_name."""
    return ndb.Key('Intelligence', intelligence_name, **kw)

class StellarRaters(ndb.Model):
    linguistic = ndb.IntegerProperty()
    logical = ndb.IntegerProperty()
    right_minded = ndb.IntegerProperty()              
    intrapersonal = ndb.IntegerProperty()
    interpersonal = ndb.IntegerProperty()
    naturalistic = ndb.IntegerProperty()


class StellarRating(ndb.Model):
    linguistic = ndb.FloatProperty()
    logical = ndb.FloatProperty()
    right_minded = ndb.FloatProperty()              
    intrapersonal = ndb.FloatProperty()
    interpersonal = ndb.FloatProperty()
    naturalistic = ndb.FloatProperty()


class Intelligence(ndb.Model):
    isbn = ndb.StringProperty()
    name = ndb.StringProperty()
    language = ndb.StringProperty()
    raters = ndb.StructuredProperty(StellarRaters)
    rating = ndb.StructuredProperty(StellarRating)

    @classmethod
    def by_name(cls, isbn):
        intelligence = memcache.get("intelligence|isbn=%s" % isbn)
        if not intelligence:
            key = ndb.Key('Intelligence', isbn, parent=intelligence_key(DEFAULT_INTELLIGENCE_NAME))
            logging.error('Intelligence DB Get')
            intelligence = key.get()
            memcache.set("intelligence|isbn=%s" % isbn, intelligence)
        return intelligence

    def update(cls):
        logging.error("Intelligence DB Put")
        cls.put()
        memcache.set("intelligence|isbn=%s" % cls.isbn, cls)


def bookshelf_key(bookshelf_name=DEFAULT_BOOKSHELF_NAME, **kw):
    return ndb.Key('Bookshelf', bookshelf_name, **kw)

class Bookshelf(ndb.Model):
    username = ndb.StringProperty(required=True)
    isbn = ndb.StringProperty(required=True)
    status = ndb.IntegerProperty(required=True, default=0)
    # Favorites: 0
    # Purchased: 1
    # To Read: 2
    # Reading Now: 3
    # Have Read: 4
    # Reviewed: 5
    # Recently Viewed: 6
    # My eBooks: 7
    # Books For You: 8
    rating = ndb.StructuredProperty(StellarRating)
    added = ndb.DateTimeProperty(auto_now_add = True, default=date.today())

    @classmethod
    def by_name(cls, username, isbn):
        if username and isbn:
            usersbook = memcache.get("usersbooks|username=%s&isbn=%s" % (username, isbn))
            if not usersbook:
                logging.error("Bookshelf DB Query")
                usersbooks = Bookshelf.query(Bookshelf.isbn==isbn, ancestor=bookshelf_key(username)).fetch(1)
                if usersbooks:
                    usersbook = usersbooks[0]
                    memcache.set("usersbooks|username=%s&isbn=%s" % (username, isbn), usersbook)
            return usersbook
        return None

    @classmethod
    def by_user(cls, username):
        if username:
            usersbooks = memcache.get("usersbooks|username=%s" % username)
            if not usersbooks:
                logging.error("Bookshelf DB Query")
                usersbooks = Bookshelf.query(ancestor=bookshelf_key(username)).fetch()
                # usersbooks = Bookshelf.query(ancestor=bookshelf_key(username)).run(batch_size=1000)
                memcache.set("usersbooks|username=%s" % username, usersbooks)
            return usersbooks
        return None

    def update(cls):
        logging.error("Bookshelf Instance DB Put")
        cls.put()
        memcache.set("usersbooks|username=%s&isbn=%s" % (cls.username, cls.isbn), cls)
        memcache.delete("usersbooks|username=%s" % cls.username)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        params['redir'] = self.request.path
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_login_cookie(self, username):
        user_cookie = userlogin.make_user_cookie(username)
        self.response.headers.add_header("Set-Cookie",
                                         "user_id=%s; Path=/" % str(user_cookie))

    def retrieve_cookie(self, cookie_name):
        cookie = self.request.cookies.get(cookie_name)
        return cookie and userlogin.validate_cookie(cookie)

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        self.username = self.retrieve_cookie("user_id")
        self.user = User.by_name(self.username)

    def reset_login_cookie(self):
        self.response.headers.add_header("Set-Cookie",
                                         "user_id=; Path=/")

    def kick_guest(self, redirect="/"):
        if not self.user:
            self.response.headers['Content-Type'] = 'text/html'
            self.response.write("""
                <html><head>
                <script>setTimeout(function () {window.location.href = "/""")
            self.response.write(redirect)
            self.response.write("""";}, 2000);</script>
                </head>
                <body>
                <p>Please log in or sign up for an account.</p>
                </body>
                </html>
            """)
            return True
        return False


class Signup(Handler):
    def get(self):
        self.render("signup.html", button_id=2)

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")

        error_username, \
            error_password, \
            error_verify, \
            error_email, \
            found_error = userlogin.valid_details(username, password, verify, email)

        params = dict(username=username,
                      email=email,
                      error_username=error_username,
                      error_password=error_password,
                      error_verify=error_verify,
                      error_email=error_email)

        if found_error:
            self.render("signup.html", **params)
        else:
            user = User.by_name(username)
            if user:
                error = "user already exists!"
                self.render("signup.html", error_username=error)
            else:
                user = User(name=username,
                            pw_hash=userlogin.create_pw_hash(username, password),
                            email=email,
                            parent=user_key())
                User.update(user)
                self.set_login_cookie(username)
                self.redirect("/")


class Login(Handler):
    def get(self):
        self.render("login.html")

    def post(self):
        re_url = self.request.get("redirect")
        username = self.request.get("username")
        password = self.request.get("password")
        user = User.login(username, password)
        if user:
            self.set_login_cookie(username)
            if re_url:
                self.redirect(re_url)
            else:
                self.redirect("/")
        else:
            error = "login unsuccessful, please try again!"
            self.render("login.html", error=error)


class Logout(Handler):
    def get(self):
        re_url = self.request.get("redirect")
        self.reset_login_cookie()
        if re_url:
            self.redirect(re_url)
        else:
            self.redirect("/")


class AddBooksPage(Handler):

    def get(self):
        if self.kick_guest(redirect="mylibrary.html"):
            return
        self.render("addbooks.html")

    def post(self):
        isbn_input = self.request.get("isbn").strip()
        valid_isbn = re.compile(r'\b(\d{13}|\d{10})\b')
        isbns = re.findall(valid_isbn, isbn_input.replace("-",""))
        booksfound = []

        logging.error("ISBNs: %s" % isbns)
        
        for isbn in isbns:

            if len(isbn)==10:
                newisbn = ''.join(['978', isbn])
                check = unicode((10 - (sum(int(digit) * (3 if idx % 2 else 1) for idx, digit in enumerate(newisbn[:12])) % 10)) % 10)
                isbn = newisbn[:12] + check

            usersbook = Bookshelf.by_name(self.username, isbn)
            # usersbook = None     #delete this line
            if usersbook:
                """book already on bookshelf"""
                # self.response.write("On Shelf")
                self.render("addbooks.html", isbn=isbn, error_isbn='Book is on your bookshelf already')
                return
            else:
                intelligence_book = Intelligence.by_name(isbn)
                # intelligence_book = None           # delete this line
                if not intelligence_book:
                    """scrape off websites and add intelligence"""
                    # self.response.write("Not in Database\n\n")
                    newbookkey = items.bookitem_key(isbn, parent=items.bookitem_key())
                    newbook = items.BookItem(key=newbookkey)
                    newbook.isbn = isbn
                    bookstw_url = ''.join(["http://search.books.com.tw/exep/prod_search.php?cat=BKA&key=", isbn])
                    eslitetw_url = ''.join(["http://www.eslite.com/Search_BW.aspx?query=", isbn])
                    crawler.crawl(newbook, bookstw_url, crawler.create_bookstw_searchresult_callback,
                                           eslitetw_url, crawler.create_eslitetw_searchresult_callback,
                                           googlebooksjs = True)
                    # self.response.write(newbook)

                    if newbook.name:

                        for (i, url) in enumerate(newbook.image_urls):
                            try:
                                result = urlfetch.fetch(url, deadline=10)
                            except DeadlineExceededError:
                                logging.error("Deadline Exceeded While Fetching Book Image\n\n\n")
                                return
                            except DownloadError:
                                logging.error("Download Error While Fetching Book Image. Check network connections.")
                                return
                            if result.status_code == 200:
                                newbook.images.append(result.content)
                                # self.response.write('<img src="/_getimage?key=%s&idx=%s" />' % (newbookkey.id(), str(i)))
                            else:
                                newbook.images.append(None)

                        newbookkey = newbook.update()
                        # logging.error("before %s" % booksfound)
                        booksfound.append(newbook)
                        # logging.error("after %s" % booksfound)
                        # self.render("showbook.html", book=newbook)

                        key = ndb.Key('Intelligence', isbn, parent=intelligence_key(DEFAULT_INTELLIGENCE_NAME))
                        intelligence = Intelligence(key=key)
                        intelligence.isbn = isbn
                        intelligence.name = newbook.name
                        intelligence.language = newbook.language
                        intelligence.update()
                    else:
                        self.render("addbooks.html", isbn=isbn,
                            error_isbn='ISBN not found')
                        return

                else:
                    book = items.BookItem.by_name(isbn)
                    if book is not None:
                        booksfound.append(book)

                bookshelf_book = Bookshelf(key=bookshelf_key(isbn, parent=bookshelf_key(self.username)))
                bookshelf_book.username = self.username
                bookshelf_book.isbn = isbn
                bookshelf_book.status = 4
                # rating = StellarRating(linguistic=0, logical=0, right_minded=0,intrapersonal=0, interpersonal=0, naturalistic=0)
                bookshelf_book.raters = StellarRaters()
                bookshelf_book.rating = StellarRating()
                bookshelf_book.update()
                # self.response.write(''.join([isbn," added to bookshelf"]))

        # logging.error("books found %s" % booksfound)
        self.render("showbook.html", head_title="View Books Added", books=booksfound)
        # self.render("addbooks.html", isbn=isbn, showdetails=True, intelligence=intelligence_book,
        #                     error_isbn='Book is now added to your bookshelf')


class MyLibrary(Handler):

    def get(self):
        if self.kick_guest(redirect="mylibrary.html"):
            return

        books = Bookshelf.by_user(self.username)
        # books = Bookshelf.by_user(self.username, projection=['isbn', 'rating.linguistic', 'rating.logical', 'rating.interpersonal', 'rating.intrapersonal', 'rating.naturalistic', 'rating.right_minded'])
        # logging.error(books)
        userbooks = []
        if books:
            for book in books:
                if book.isbn:
                    bookpjn = items.BookItem.by_name(isbn=book.isbn, projection=['name', 'author', 'illustrator', 
                                                     'publisher', 'extent', 'dimensions'])
                    if bookpjn:
                        if book.rating:
                            bookpjn.rating = book.rating
                        else:
                            bookpjn.rating = None
                        userbooks.append(bookpjn)


        self.render("showbook.html", head_title="View Library", books=userbooks)


class GetImage(Handler):

    def get(self):
        key = self.request.get('key')
        idx = self.request.get('idx')
        logging.error("key: %s; idx: %s" % (key, idx))
        pic = memcache.get("img|key: %s; idx: %s" % (key, idx))
        if not pic:
            logging.error("Missed Memcache for Pic")
            try:
                i = int(idx)
                if key:
                    bookitem = items.BookItem.by_name(key)
                    if bookitem:
                        img = images.Image(bookitem.images[i])
                        img.resize(width=200)
                        pic = img.execute_transforms(output_encoding=images.JPEG)
                        memcache.set("img|key: %s; idx: %s" % (key, idx), pic)
            except:
                self.redirect("/")
                return
        self.response.headers['Content-Type'] = 'image/jpeg'
        self.response.write(pic)


class UpdateUserReivews(Handler):

    def post(self):
        if self.kick_guest():
            return
        isbn = self.request.get('isbn').strip()
        cat = self.request.get('cat').strip()
        rating = int(self.request.get('rating'))
        userbook = Bookshelf.by_name(self.username, isbn)

        if userbook is None:
            return

        # logging.error("isbn %s, cat %s, rating %s, intelligence_book %s" % (isbn, cat, rating, intelligence_book))
        # logging.error("getattr %s" % getattr(intelligence_book, "rating"))
        stellar_rating = getattr(userbook, "rating")
        if stellar_rating is None:
            stellar_rating = StellarRating()

        intelligence = Intelligence.by_name(isbn)
        if intelligence is None:
            logging.error("BIG BIG PROBLEM")
            # TO-DO

        # update_intell_db
        if intelligence.rating is None:
            intelligence.rating = StellarRating()
        if intelligence.raters is None:
            intelligence.raters = StellarRaters()
        old_intell_rating = getattr(intelligence.rating, cat)
        old_intell_raters = getattr(intelligence.raters, cat)
        # logging.error("old rating: %s, raters: %s" % (old_intell_rating, old_intell_raters))

        old_user_rating = getattr(stellar_rating, cat)

        if old_user_rating is None:
            if old_intell_raters is None:
                new_intell_raters = 1
                new_intell_rating = rating
            else:
                new_intell_raters = old_intell_raters + 1
                new_intell_rating = (old_intell_rating * old_intell_raters + rating) / new_intell_raters
        else:
            new_intell_raters = old_intell_raters
            new_intell_rating = (old_intell_rating * old_intell_raters - old_user_rating + rating) / new_intell_raters

        # logging.error("new rating: %s, raters: %s" % (new_intell_rating, new_intell_raters))
        setattr(intelligence.rating, cat, new_intell_rating)
        setattr(intelligence.raters, cat, new_intell_raters)

        setattr(stellar_rating, cat, rating)
        # logging.error("getattr %s" % getattr(intelligence_book, "rating"))

        setattr(userbook, "rating", stellar_rating)
        userbook.update()
        intelligence.update()


class MainPage(Handler):

    def get(self):
        self.render("index.html")
        return

        self.populate()
        intell_query = Intelligence.query(ancestor=intelligence_key())
        intelligences = intell_query.fetch(10)
        self.render("main.html", intelligences=intelligences)

    def populate(self):
        if u'Intelligence' in metadata.get_kinds():
            logging.error('database Intelligence already exists!')
            logging.error(Intelligence.query().fetch(1, keys_only=True)[0].parent())
            return
        else:
            logging.error('creating database Intelligence from csv file')

        with open(CSV_FILE, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                key = ndb.Key('Intelligence', row[0], parent=intelligence_key(DEFAULT_INTELLIGENCE_NAME))
                intelligence = key.get()
                if intelligence:
                    logging.error('found!!!')
                    key.delete()
                intelligence = Intelligence(key=key)
                intelligence.isbn = row[0]
                intelligence.name = row[1]
                intelligence.language = row[-1]
                rating = StellarRating()
                rating.linguistic = int(row[2]) if row[2] else 0
                rating.logical = int(row[3]) if row[3] else 0
                rating.right_minded = int(row[4]) if row[4] else 0
                rating.intrapersonal = int(row[5]) if row[5] else 0
                rating.interpersonal = int(row[6]) if row[6] else 0
                rating.naturalistic = int(row[7]) if row[7] else 0
                intelligence.rating = rating
                intelligence.update()


class DeleteDBPage(Handler):
    
    def get(self):
        ndb.delete_multi(Intelligence.query().fetch(keys_only=True))
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write('<html><body>DB deleted!</body></html>')


class RenderPage(Handler):

    def get(self, page_id):
        self.render(page_id)


class HomeHandler(BaseHandler):
    def get(self):
        template = jinja_env.get_template('example.html')
        self.response.out.write(template.render(dict(
            facebook_app_id=FACEBOOK_APP_ID,
            current_user=self.current_user
        )))

    def post(self):
        url = self.request.get('url')
        file = urllib2.urlopen(url)
        graph = facebook.GraphAPI(self.current_user['access_token'])
        response = graph.put_photo(file, "Test Image")
        photo_url = ("http://www.facebook.com/"
                     "photo.php?fbid={0}".format(response['id']))
        self.redirect(str(photo_url))


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/fb', HomeHandler),
    ('/(.*\.html$)', RenderPage),
    ('/signup/?', Signup),
    ('/login/?', Login),
    ('/logout/?', Logout),
    ('/addbooks/?', AddBooksPage),
    ('/deleteDB/?', DeleteDBPage),
    ('/_getimage/?', GetImage),
    ('/mylibrary/?', MyLibrary),
    ('/api/_updateuserreviews/?', UpdateUserReivews)
], debug=DEBUG
 , config=config)

