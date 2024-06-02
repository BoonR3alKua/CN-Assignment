import bencodepy
import os
import hashlib
from collections import OrderedDict
import tkinter as tk
from tkinter import filedialog
import json
from tkinter.filedialog import askdirectory
from tkinter import Tk
import math
# Kieu du lieu torrent

class Torrent:
    def __init__(self, announce, info):
        self.announce = announce
        self.info = info
        self.length = info.get('length')
        self.name = info.get('name')
        self.piece_length = info.get('piece length')
        self.pieces = info.get ('pieces')

        self.left = self.length
        self.info_hash = ''
        self.pieces_list = []
        self.hash_pieces_list = []
    def get_announce(self):
        return self.announce
    def get_length(self):
        return self.length
    def get_name(self):
        return self.name
    def get_piece_length(self):
        return self.piece_length
    def get_pieces(self):
        return self.pieces
    def get_info(self):
        return self.info
    def get_left (self):
        return self.left
    def get_info_hash(self):
        return self.info_hash
    def get_pieces_list (self):
        return self.pieces_list
    def get_hash_pieces_list (self):
        return self.hash_pieces_list
    def set_left(self, left):
        self.left = left
    def set_info_hash (self, info_hash):
        self.info_hash = info_hash
    def set_pieces_list (self, length, piece_length):
        num = math.ceil(length/piece_length)
        self.pieces_list = [None]*num
    def set_hash_pieces_list (self, length, piece_length):
        num = math.ceil(length/piece_length)
        self.hash_pieces_list = [None]*num

def read_torrent_file(filepath):
    with open(filepath, 'rb') as f:
        torrent_data = bencodepy.decode(f.read())
    announce = torrent_data[b'announce'].decode('utf-8')
    info_temp = torrent_data[b'info']
    infor_temp = OrderedDict(info_temp)
    
    info = dict(infor_temp)
    info = {key.decode('utf-8'): (value if key == b'pieces' else value.decode('utf-8', errors='ignore')) if isinstance(value, bytes) else value for key, value in info.items()}
    
    return Torrent(announce, info)

def torrent2hash(info):
    sorted_info = dict(sorted(info.items()))
    info_bytes = str.encode(repr(sorted_info))
    hasher = hashlib.sha1(info_bytes)
    return hasher.hexdigest()


def open_file(root, filepath):
    filepath.append(filedialog.askopenfilename())
    print(f"Open: {filepath[0]}")
    root.destroy()

def import_file():
    root = tk.Tk()
    filepath = []
    root.after(0, lambda: open_file(root, filepath))
    root.mainloop()
    if filepath:  # Kiểm tra xem danh sách có trống không
        return filepath[0]
    else:
        print("No file selected.")
        return None

def open_directory(root, despath):
    despath.append(askdirectory())
    print(f"Selected directory: {despath[0]}")
    root.destroy()
    
def choose_directory():
    root = Tk()
    despath = []
    root.after(0, lambda: open_directory(root, despath))
    root.mainloop()
    if despath:  # Check if the list is not empty
        return despath[0]
    else:
        print("No directory selected.")
        return None

def create_Torrent_full():
    despath = ""
    filepath = []
    folderpath = ""
    while True: #find filepath,despath and folderpath
        if despath and (filepath or folderpath):  
            break
        answer = input ("Choose your location (L)/ Choose your file (Fi)/ Choose your Folder(Fo) or Exit (E) \n")
        if (answer.lower() == "l"):
            despath = choose_directory()
        elif (answer.lower() =='fi'):
            filepath = import_file() 
        elif (answer.lower() == 'fo'):
            folderpath = choose_directory()
        elif (answer.lower() == 'e '):
            break
        
    despath = despath.replace('/', '\\')
    if despath and filepath:
        torrentname = input ("Enter the name of new torrent file: ")
        full_path = os.path.join (despath, torrentname +   ".torrent")
        open(full_path,'a').close()
        create_torrent_file(filepath, full_path, 256)
        print(f"Creating torrent file at {full_path}")
    elif despath and folderpath:
        torrentname = input ("Enter the name of new torrent file: ")
        full_path = os.path.join (despath, torrentname +   ".torrent")
        open(full_path,'a').close()
        create_torrent_folder(folderpath, full_path, 256)
        print(f"Creating torrent file at {full_path}")
        return
    
def create_torrent_file(file_path, des_path, piece_length):
    piece_length = piece_length*1024;
    with open(file_path, 'rb') as f:
        file_data = f.read()

    # chia file thanh tung manh 512 KB
    pieces = [file_data[i:i+piece_length] for i in range(0, len(file_data), piece_length)]
    sha1_hashes = [hashlib.sha1(piece).digest() for piece in pieces]

    torrent_info = {
        'length': os.path.getsize(file_path),
        'name': os.path.basename(file_path),
        'piece length': piece_length,  # Kích thước phần là 512KB
        'pieces': sha1_hashes
    }
    
    torrent = {
        'announce': '192.168.1.93',
        'info': torrent_info
    }
    torrent_bencoded = bencodepy.encode(torrent)
    with open(des_path, 'wb') as f:
        f.write(torrent_bencoded)

def create_torrent_folder(folder_path, des_path, piece_length):
    piece_length = piece_length*1024
    torrent_info = {
        'name': os.path.basename(folder_path),
        'piece length': piece_length,
        'files': []
    }

    all_data = b''
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                file_data = f.read()
            all_data += file_data
            torrent_info['files'].append({
                'length': len(file_data),
                'path': file_path.replace(folder_path + os.sep, '').split(os.sep),
            })

    pieces = [all_data[i:i+piece_length] for i in range(0, len(all_data), piece_length)]
    print (f'Pieces list: {pieces}')
    sha1_hashes = [hashlib.sha1(piece).digest() for piece in pieces]
    torrent_info['pieces'] = sha1_hashes

    torrent = {
        'announce': '192.168.1.93',
        'info': torrent_info
    }
    torrent_bencoded = bencodepy.encode(torrent)
    with open(des_path, 'wb') as f:
        f.write(torrent_bencoded)
        
        
