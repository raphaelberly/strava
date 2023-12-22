import sys
import yaml

sys.path.append('..')
from lib.database import Database


# Log in to database
with open('../conf/secrets.yaml') as file:
    db = Database(**yaml.safe_load(file)['db'])
