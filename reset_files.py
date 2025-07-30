import os
import shutil

database_file = "chat.db"
uploads_folder = "uploads"
icons_folder = "icons"

if os.path.exists(database_file):
  os.remove(database_file)
else:
  print(f"{database_file} does not exist")

if os.path.exists(icons_folder):
  shutil.rmtree(icons_folder)
  os.mkdir(icons_folder)
else:
  print(f"{icons_folder} does not exist")

if os.path.exists(uploads_folder):
  shutil.rmtree(uploads_folder)
  os.mkdir(uploads_folder)
else:
  print(f"{uploads_folder} does not exist")