from google.appengine.ext import ndb

DEFAULT_INTELLIGENCE_NAME = 'default_intelligence_name'

def intelligence_key(intelligence_name=DEFAULT_INTELLIGENCE_NAME):
    """Constructs a Datastore key for an Intelligence entity with intelligence_name."""
    return ndb.Key('Intelligence', intelligence_name)

class Intelligence(ndb.Model):
    sku = ndb.KeyProperty(required=True)
    name = ndb.StringProperty()
    language = ndb.StringProperty()
    linguistic = ndb.IntegerProperty()
    logical = ndb.IntegerProperty()
    right_minded = ndb.IntegerProperty()
    intrapersonal = ndb.IntegerProperty()
    interpersonal = ndb.IntegerProperty()
    naturalistic = ndb.IntegerProperty()

