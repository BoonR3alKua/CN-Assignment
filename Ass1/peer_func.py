import sys
from torrent import *
import socket
import urllib.parse
import requests
from flask import Flask, request, jsonify, Response
import json
from threading import Thread
import operator
import math
import threading
import queue
import time
import socket

stop_contact_to_tracker = False

thread_contact_list = []

class Peer:
    def __init__(self, ip, port, peer_id, torrent, bitfield):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.torrent = torrent
        self.bitfield = bitfield

    def get_ip(self):
        return self.ip
    def get_port(self):
        return self.port
    def get_peer_id(self):
        return self.peer_id
    def get_torrent(self):
        return self.torrent
    def get_bitfield(self):
        return self.bitfield
    def set_bitfield(self, bitfield):
        self.bitfield = bitfield
        

        
def keep_contact_with_tracker(torrent, port_sys, tracker_port_sys, peer_id_sys):
    global stop_contact_to_tracker
    while not stop_contact_to_tracker: #Khi chua co tin hieu dung thread contact thi dinh ky 1 phut se ket noi mot lan
        tracker_host = torrent.get_announce()
        tracker_port = tracker_port_sys
        port = port_sys
        peer_id = peer_id_sys
        left = torrent.get_left()
        info_hash = torrent.get_info_hash()

        params = {
            'info_hash': info_hash,
            'peer_id': peer_id,
            'port': port,

            'left': left,
            'event': "started"
        }
        tracker_host = 'http://' + tracker_host + ':' + str(tracker_port)
        response = requests.get(tracker_host, params=params)
        
        time.sleep(60) #sleep 1 minute

def send_request_to_tracker(torrent, event, port_sys, tracker_port_sys, peer_id_sys):
    tracker_host = torrent.get_announce()
    tracker_port = tracker_port_sys
    port = port_sys
    peer_id = peer_id_sys
    left = torrent.get_left()
    info_hash = torrent.get_info_hash()

    
    
    params = {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'port': port,
        'left': left,
        'event': event
    }
    tracker_host = 'http://' + tracker_host + ':' + str(tracker_port)
    response = requests.get(tracker_host, params=params)
    
    if response.status_code == 200:
        print('Request sent to tracker successfully.') # truong hop left > 0
        try:
            response_json = json.loads(response.text)
            failure_reason = response_json['failure_reason']
            tracker_id = response_json['tracker_id']
            peers_list = response_json['ready_peers_list']
            print('Received list of peers:', peers_list)
            thread = threading.Thread(target=keep_contact_with_tracker, args=(torrent, port_sys, tracker_port_sys, peer_id_sys))
            thread.start()
            thread_contact_list.append(thread)
            return peers_list
        except json.JSONDecodeError: # truong hop left = 0
            thread = threading.Thread(target=keep_contact_with_tracker, args=(torrent, port_sys, tracker_port_sys, peer_id_sys))
            thread.start()
            thread_contact_list.append(thread)
            return
    elif response.status_code == 400:
        data = json.loads(response.text)
        print (data['failure_reason'])
    else:
        print('Failed to send request to tracker.')
        return 
    
def verify_data_left(location, torrent):
    
    length = 0
    if 'files' in torrent.get_info():
        for file in torrent.get_info()['files']:
            length += file[b'length']
    else:
        length = torrent.get_info()['length']
        
    files = os.listdir(location[0])
    torrent.set_pieces_list (length, torrent.get_piece_length())
    torrent.set_hash_pieces_list (length, torrent.get_piece_length())
    for file in files:
        path = os.path.join(location[0], file)
        if 'files' in torrent.get_info(): #multiple files torrent
            
            for file_info in torrent.get_info()['files']:
                if file_info[b'path'][0].decode() == file:
                    with open(path, 'rb') as f:
                        data = f.read()
                        length -= len(data)
                    break
        else: #single file torrent
            if torrent.get_info()['name'] == file:
                with open(path, 'rb') as f:
                    data = f.read()
                    length -= len(data)
                break
    
    torrent.set_left(length)
    return

def split_pieces_and_hash(location, torrent, pieces_list, hash_pieces_list):
    #todo
    all_data = b''
    files = os.listdir(location[0])
    
    for file in files:
        path = os.path.join(location[0], file)
        if 'files' in torrent.get_info(): #multiple files torrent
            for file_info in torrent.get_info()['files']:
                if file_info[b'path'][0].decode() == file:
                    with open(path, 'rb') as f:
                        data = f.read()
                        all_data += data
                    break
        else: #single file torrent
            if torrent.get_info()['name'] == file:
                with open(path, 'rb') as f:
                    data = f.read()
                    all_data += data
                break
    pieces = [all_data[i:i+torrent.get_piece_length()] for i in range(0, len(all_data), torrent.get_piece_length())]
   
    pieces_list.clear()
    pieces_list.extend(pieces)
    sha1_hashes = [hashlib.sha1(piece).digest() for piece in pieces]
    hash_pieces_list.clear()
    hash_pieces_list.extend(sha1_hashes)
    return sha1_hashes
    
def generate_bitfield(location, torrent, pieces_list, hash_pieces_list):
    bitfield = ''
    hash_pieces = split_pieces_and_hash(location, torrent, pieces_list, hash_pieces_list)
    for torrent_piece in torrent.get_pieces():
        if torrent_piece in hash_pieces:
            bitfield += '1'
        else:
            bitfield += '0'
    print (f'Generated bitfield: {bitfield} successfully.')
    return bitfield

def calculate_piece_count(peer_list):
    piece_counts = {}
    for peer in peer_list:
        # Convert the bitfield string to a list of booleans
        bitfield = [bool(int(bit)) for bit in peer.get_bitfield()]
        for index, has_piece in enumerate(bitfield):
            if has_piece:
                if index in piece_counts:
                    piece_counts[index] += 1
                else:
                    piece_counts[index] = 1
    return piece_counts 

def download_block(peer, piece_index, block_length, block_queue, blocks_list):
    while not block_queue.empty():
        # Get a block index from the queue
        time.sleep(0.02)
        try:
            block_index = block_queue.get(block=True, timeout=1)
        except queue.Empty:
            break
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((peer.get_ip(), int (peer.get_port()) + 1))
            
            info_hash= peer.get_torrent().get_info_hash()
            peer_id= peer.get_peer_id()
            piece_index= piece_index
            block_index= block_index
            block_length= block_length
            
            print (f'Sending Block {block_index + 1}/ Piece {piece_index + 1} to peer {peer.get_peer_id()}')
            request = f'{info_hash},{peer_id},{piece_index},{block_index},{block_length}'
            
            client_socket.send (request.encode('utf-8'))
            data = client_socket.recv(block_length)
            try:
                decoded_data = data.decode('utf-8')
                if data.decode('utf-8') == 'Block index out of range':
                    print (f'Block is out of index')
                    while not block_queue.empty():
                        try:
                            block_queue.get_nowait()
                        except queue.Empty:
                            continue
                        block_queue.task_done()
                    break
                elif data.decode ('utf-8').startswith('Error occurred: '):
                    print(f'Error downloading block {block_index} from peer {peer}: {e}')
                    block_queue.put(block_index)
            except UnicodeDecodeError:
                blocks_list[block_index] = data
                print (f'Block {block_index + 1}/ piece {piece_index + 1} downloaded from peer {peer.get_peer_id()} successfully. \n')


            
        except Exception as e:
            print(f"Error occurred: {e}")
            block_queue.put(block_index)
        finally:
            client_socket.close()
            block_queue.task_done()
    print ('\nThread finished')
    
def send_interested(peer_host, info_hash):
    intereseted_request = {'message': 'INTERESTED', 'info_hash': info_hash}
    response = requests.post(peer_host, data=json.dumps(intereseted_request))

    if response.status_code == 200:
        bitfield_response = json.loads(response.text)
        bitfield = bitfield_response.get('bitfield', '')
        print ('Received bitfield:', bitfield)
        return bitfield
    else:
        print ('Failed to send interested request.')

def send_stop_request_to_tracker(port_sys, tracker_port_sys, peer_id_sys, tracker_list):
    print ('Sending stop request to tracker ...')
    for torrent in tracker_list:
        tracker_host = torrent.get_announce()
        tracker_port = tracker_port_sys
        port = port_sys
        peer_id = peer_id_sys
        left = torrent.get_left()
        info_hash = torrent.get_info_hash()
        
        params = {
            'info_hash': info_hash,
            'peer_id': peer_id,
            'port': port,
            'left': left,
            'event': "stopped"
        }
        tracker_host = 'http://' + tracker_host + ':' + str(tracker_port)
        response = requests.get(tracker_host, params=params)



def ask_user_to_connect_to_peers(peer_list, peers, needed_torrent):
    answer = input("Do you want to connect with other peers? (Y/N) \n")
    if (answer.lower() == 'y'): #if they want to connect to other peers
        for peer in peers:
            print('IP ', peer['ip'], ', Port: ', peer['port'])
            params = {
                'info_hash': needed_torrent.get_info_hash(),
                'peer_id': peer['peer_id']
            }
            peer_host = 'http://' + peer['ip'] + ':' + str(peer['port'])
            response = requests.get(peer_host, params=params)
            
            if response.status_code == 200:
                print('Connected to peer', peer['peer_id'] , 'successfully.')
                # Todo
                bitfield = send_interested(peer_host, params['info_hash'])
                new_peer = Peer(peer['ip'], peer['port'], peer['peer_id'], needed_torrent, bitfield)
                peer_list.append(new_peer)
            else:
                print('Failed to send request.')
    elif (answer.lower() == 'n'):
        # Todo
        return

def ask_user_to_send_download_request(peer_list, pieces_list):
    print ("Starting download ...")
    piece_count = calculate_piece_count(peer_list)
    print (f'Piece count: {piece_count}')
    while piece_count:
        sorted_pieces = sorted(piece_count.items(), key=operator.itemgetter(1))
        rarest_piece = sorted_pieces[0][0]
        if rarest_piece in pieces_list:
            piece_count.pop(rarest_piece)
            continue
        
        peers_with_piece = [peer for peer in peer_list if peer.get_bitfield()[rarest_piece] == '1']
        
        piece_length = peers_with_piece[0].get_torrent().get_piece_length()
        block_length = 16384 #16 KB
        num_blocks = math.ceil(piece_length/block_length)
        
        block_queue = queue.Queue()
        for block_index in range(num_blocks):
            block_queue.put(block_index)  # tao hang doi cho cac block
        
        blocks_list = [None]*num_blocks # Create a list of blocks list to store downdloaded blocks from peers
        downloading_thread = []
        for index, peer in enumerate(peers_with_piece):
            # Create up to 5 threads for each peer
            print (f'{index}. Downloading from peer {peer.get_peer_id()} ... \n')
            thread = threading.Thread(target=download_block, args=(peer, rarest_piece, block_length, block_queue, blocks_list))
            thread.start()
            downloading_thread.append(thread)

        #Ending all threads 
        block_queue.join()
        for thread in downloading_thread:
            thread.join()
            print (f'Thread {thread} finished')
        blocks_list = [block if block is not None else b'' for block in blocks_list]
        complete_piece = b''.join(blocks_list)
        pieces_list[rarest_piece] = complete_piece
        piece_count.pop(rarest_piece)

    print (f'\nDownloaded all pieces successfully.')

def ask_user_to_write_file (location, torrent):
    print ('\nWriting file ...')
    existing_files = os.listdir(location[0])
    torrent_info = torrent.get_info()
    file_data = b''.join(torrent.get_pieces_list())
    data_offset = 0
    
    
    if 'files' in torrent.get_info(): #multiple files torrent
        for file_info in torrent_info['files']:
            file_path = os.path.join(location[0], file_info[b'path'][0].decode())
            if os.path.basename(file_path) not in existing_files:
                with open(file_path, 'wb') as f:
                    file_name = os.path.basename(file_path)
                    print(f'\nCreated file {file_name}')
                    data = file_data[data_offset: data_offset + file_info[b'length']]
                    data_offset += file_info[b'length']
                    f.write(data)
                    print (f'Write data to file {file_name} successfully.')
            else:
                data_offset += file_info[b'length']
                print (f'File {file_path} already exists.')
    else: #single file only
        file_path = os.path.join(location[0], torrent_info['name'])
        if torrent_info['name'] not in existing_files:
            with open(file_path, 'wb') as f:
                data = file_data[data_offset: data_offset + torrent_info['length']]
                f.write(data)
                print (f'Write data to file {file_path} successfully.')
        else:
            print (f'File {file_path} already exists.')
            
def ask_user_to_send_completed_request(port_sys, tracker_port_sys, peer_id_sys, location, torrent):
    print ('\nSending completed request ...')
    verify_data_left(location, torrent)
    
    tracker_host = torrent.get_announce()
    tracker_port = tracker_port_sys
    port = port_sys
    peer_id = peer_id_sys
    left = torrent.get_left()
    info_hash = torrent.get_info_hash()

    params = {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'port': port,
        
        'left': left,
        'event': "completed"
    }
    
    tracker_host = 'http://' + tracker_host + ':' + str(tracker_port)
    response = requests.get(tracker_host, params=params)
    
    if response.status_code == 200:
        print('Downloaded successfully. Request sent to tracker.')
        return
    else:
        print('Failed to send completed request.')

def ask_user_to_choose_location(location):
    root = Tk()
    root.after(0, lambda: open_directory(root, location))
    root.mainloop()
    if location:  # Check if the list is not empty
        return location
    else:
        print("No directory selected.")
        return None
 
def ask_user(port_sys, tracker_port_sys, peer_id_sys, location, torrent_list):
    global stop_contact_to_tracker
    while True:
        print ('\n -------------------------------------------- \n')
        answer = input("Which action do you want: Import(I)/ Run(R) or Stop(S)\n")
        if (answer.lower() == 'i'):
            filepath = import_file()
            torrent = read_torrent_file(filepath)
            info_hash = torrent2hash(torrent.get_info())
            torrent.set_info_hash(info_hash)
            verify_data_left(location, torrent) 
            torrent_list.append((torrent)) #save torrent into torrents list
        elif (answer.lower() == 'r'):
            while True:
                if torrent_list: 
                    count = 1
                    print (f'\n--------------------------------------\n')
                    for torrent in torrent_list:
                        print(f'{count}. Torrent {torrent.get_name()}')
                        count += 1
                    print (f'\n--------------------------------------\n')
                    answer = input("\nChoose index of torrent file want to run or Exit (e) ?\n")
                    if answer.isdigit():
                        index = int (answer)
                        if (index < 1 or index > count):
                            print ('Wrong input, please try again')
                            continue
                        else:  
                            needed_torrent = torrent_list[index - 1]
                            peers = send_request_to_tracker(needed_torrent, 'started', port_sys, tracker_port_sys, peer_id_sys)
                            if peers:
                                peer_ready_to_download = []
                                # lay list cac peer va bitfield cua cac peer
                                ask_user_to_connect_to_peers(peer_ready_to_download, peers, needed_torrent)
                                #tu cac bitfield cua cac peer, tinh ra duoc cac piece can download->tao list cac peer co piece nay va tao tung thread de gui yeu cau download toi
                                print ('Peer ready to download:', peer_ready_to_download)
                                ask_user_to_send_download_request(peer_ready_to_download, needed_torrent.get_pieces_list()) 
                                #sau khi pieces_list cua file torrent da du thi thuc hien viec ghi lai file
                                ask_user_to_write_file(location, needed_torrent)
                                #xu ly cac van de sau khi hoan thanh viec tai
                                ask_user_to_send_completed_request(port_sys, tracker_port_sys, peer_id_sys, location, needed_torrent)
                            else:
                                
                                break
                    elif (answer.lower() == 'e'):
                        break
                    
                else: # No torrent file in the system
                    print ('No torrents in the system')
                    break
        elif (answer.lower() == 's'):
            print ("Stopping ... ")
            send_stop_request_to_tracker(port_sys, tracker_port_sys, peer_id_sys, torrent_list)
            stop_contact_to_tracker = True
            for index, thread in enumerate(thread_contact_list):
                print (f'Stopping thread contact to tracker {index} ...')
                thread.join()