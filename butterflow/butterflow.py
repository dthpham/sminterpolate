import os
from config import Config
from __init__ import conf_path

if not os.path.exists(conf_path):
  open(conf_path, 'a').close()

config = Config.from_file(conf_path)
