import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

class Peer_in_track:
    def __init__(self, ip, info_hash, peer_id, port,  left, event):
        self.ip = ip
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.port = port

        self.left = left
        self.event = event
        self.last_contact = time.time()
    
    def get_ip(self):
        return self.ip
    def get_info_hash(self):
        return self.info_hash
    def get_peer_id(self):
        return self.peer_id
    def get_port(self):
        return self.port

    def get_left(self):
        return self.left
    def get_event(self):
        return self.event
    def get_last_contact(self):
        return self.last_contact
    def update_last_contact(self):
        self.last_contact = time.time()
    def update (self, new_peer):

        self.left = new_peer.get_left()
        self.event = new_peer.get_event()
        self.last_contact = time.time()
swarm = []
    
def handle_request_event(peer):
    global swarm
    if peer.get_event() == "started":
        for existing_peer in swarm:
            if existing_peer.get_peer_id() == peer.get_peer_id() and existing_peer.get_info_hash() == peer.get_info_hash():
                existing_peer.update(peer)
                return
        swarm.append(peer)
        return
    elif peer.get_event() == "stopped":
        swarm = [existing_peer for existing_peer in swarm if existing_peer.get_peer_id() != peer.get_peer_id()]
        return 
    elif peer.get_event() == "completed":
        # Update the peer status to completed
        for existing_peer in swarm:
            if existing_peer.get_peer_id() == peer.get_peer_id() and existing_peer.get_info_hash() == peer.get_info_hash():
                existing_peer.update(peer)
        return

def check_peer_status():
    global swarm
    while True:
        current_time = time.time()
        swarm = [peer for peer in swarm if current_time - peer.get_last_contact() <= 120] #2minute
        time.sleep(60) #1 minute
        print (swarm)
        print ('\n --------------------------------- \n')


@app.route('/', methods=['GET'])
def handle_peer_request():
    # Lấy thông tin từ yêu cầu
    peers_dict = []
    
    info_hash = request.args.get('info_hash')
    peer_id = request.args.get('peer_id')
    port = request.args.get('port')
    left = request.args.get('left')
    event = request.args.get('event')
    
    #Check whether sender give enough information
    if not all([info_hash, peer_id, port, left, event]):  
        response = {
            'failure_reason': 'Not enough information',
            'tracker_id': '1234',
            'ready_peers_list': peers_dict
        }
        return response, 400
    
    
    peer_info = {
        'ip': request.remote_addr,
        'info_hash': info_hash,
        'peer_id': peer_id,
        'port': port,
        'left': left,
        'event': event
    }
    temp_peer = Peer_in_track(peer_info['ip'], peer_info['info_hash'], peer_info['peer_id'], 
                              peer_info['port'], peer_info['left'], peer_info['event'])

                              
    if event not in ['started', 'stopped', 'completed']:
        response = {
            'failure_reason': 'Invalid event',
            'tracker_id': '1234',
            'ready_peers_list': peers_dict
        }
        return response, 400
    
    
    handle_request_event(temp_peer)

    print (swarm)
    print ('\n --------------------------------- \n')
    
    if int(left) > 0:
        for peer in swarm: 
            if int (int(peer.get_left())) >= 0 and int(peer.get_left()) < int(left) and peer.get_info_hash() == info_hash and peer.get_peer_id() != peer_id:
                peers_dict.append({
                    'peer_id': peer.get_peer_id(),
                    'ip': peer.get_ip(),
                    'port': peer.get_port()
                })
            

    response = {
        'failure_reason': 'No failure reason',
        'tracker_id': '1234',
        'ready_peers_list': peers_dict
    }
    return response, 200

if __name__ == '__main__':
    
    # Thread checking peer status every 1 minutes
    check_peer_status = threading.Thread (target = check_peer_status)
    check_peer_status.start()
    
    app.run(host='192.168.1.93', port=1234)
