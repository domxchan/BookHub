import datetime
from google.appengine.ext import db
from google.appengine.tools import bulkloader
import models

class IntelligenceLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'Intelligence',
                                   [('sku', lambda x: x.decode('utf-8')),
                                    ('name', lambda x: x.decode('utf-8')),
                                    ('linguistic', lambda x: int(x) if x else 0),
                                    ('logical', lambda x: int(x) if x else 0),
                                    ('right_minded', lambda x: int(x) if x else 0),
                                    ('intrapersonal', lambda x: int(x) if x else 0),
                                    ('interpersonal', lambda x: int(x) if x else 0),
                                    ('naturalistic', lambda x: int(x) if x else 0),
                                    ('language',  lambda x: x.decode('utf-8'))
                                   ])

loaders = [IntelligenceLoader]

