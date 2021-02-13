'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
import os
import sys
import json
import traceback
from datetime import datetime
from time import localtime, strftime, strptime

def allOfType(path, filetype):
  files = []
  for file in os.listdir(path):
    if file.endswith(filetype):
      files.append(os.path.join(path, file))
  if len(files) == 0:
    return []
  return files

def removeAgedFiles(path, age):
  for file in os.listdir(path):
    link = '%s/%s'%(path,file)
    fst = os.stat(link)
    tdelta = datetime.now() - datetime.utcfromtimestamp(int(fst.st_mtime))
    if tdelta.days > age:
      #print("Removing file: %s" % link)
      os.remove(link)

def readCSV(fileName):
  try:
    f = open(fileName, "r")
    return f.read().split('\n')
  except:
    #print("ERROR: Unable to Load file: %s."% (fileName))
    return []
  f.close()


def readFile(fileName):
  try:
    f = open(fileName, "r")
    return json.load(f)
  except:
    #print("ERROR: Unable to Load file: %s."% (fileName))
    return []
  f.close()

def writeRAW(fileName, data):
  with open(fileName, "w+", encoding="utf-8") as f:
    f.write(data)
  f.close()

def writeJSON(fileName, data):
  with open(fileName, "w+") as f:
    f.write(json.dumps(data))
  f.close()

def appendJSON(fileName, data):
  with open(fileName, "a+") as f:
    f.write(json.dumps(data))
  f.close()