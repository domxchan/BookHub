import logging
from google.appengine.api import memcache
from google.appengine.ext import ndb
DEFAULT_BOOKITEM_NAME = 'default_bookitem_name'

def bookitem_key(bookitem_name=DEFAULT_BOOKITEM_NAME, **kw):
    """Constructs a Datastore key for a BookItem entity with bookitem_name."""
    return ndb.Key('BookItem', bookitem_name, **kw)

class BookItem(ndb.Model):
    isbn = ndb.StringProperty(required=True)
    name = ndb.StringProperty()
    author = ndb.StringProperty(repeated=True)
    illustrator = ndb.StringProperty()
    translator = ndb.StringProperty()
    publisher = ndb.StringProperty()
    publication_date = ndb.StringProperty()
    language = ndb.StringProperty()
    origin = ndb.StringProperty()
    dimensions = ndb.StringProperty()
    colour = ndb.StringProperty()
    series = ndb.StringProperty()
    video_links = ndb.StringProperty(repeated=True)
    extent = ndb.IntegerProperty()
    book_format = ndb.StringProperty()

    desc = ndb.TextProperty()
    list_price_ccy = ndb.StringProperty()
    list_price_amt = ndb.FloatProperty()
    image_urls = ndb.StringProperty(repeated=True)
    images = ndb.BlobProperty(repeated=True)
    image_serving_url = ndb.StringProperty()
    num_images = ndb.IntegerProperty()

    price = ndb.FloatProperty()

    @classmethod
    def by_name(cls, isbn, projection=None):
        book = None
        if projection is not None:
            book = memcache.get("BookItem|isbn=%s" % isbn)
        if not book:
            logging.error("BookItem DB Query")
            # books = BookItem.query(BookItem.isbn==isbn, ancestor=bookitem_key()).fetch(limit=1, projection=projection)
            books = BookItem.query(BookItem.isbn==isbn, ancestor=bookitem_key()).fetch(limit=1)
            if books!=[]:
                book = books[0]
                if projection is not None:
                    tbook = BookItem(name=book.name, author=book.author, illustrator=book.illustrator, publisher=book.publisher,
                                     extent=book.extent, dimensions=book.dimensions, isbn=isbn, desc=book.desc)
                    memcache.set("BookItem|isbn=%s" % isbn, tbook)
                    book = tbook
            # key = ndb.Key('BookItem', isbn, parent=bookitem_key(DEFAULT_BOOKITEM_NAME))
            # return key.get()
        return book

    def update(cls):
        logging.error("BookItem DB Put")
        cls.put()
        memcache.set("BookItem|isbn=%s" % cls.isbn, cls)
