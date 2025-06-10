import time
import hashlib

REGISTRATION_DURATION_SECONDS = 20
NODE_MAX_FAILURES = 3
BURNED_NODE_SHUTDOWN_SECONDS = 60

def hash_node_id(host, port):
    return hashlib.sha1(f"{host}:{port}".encode()).hexdigest()

class Node:
    def __init__(self, host, port, name=None):
        self.host = host
        self.port = port
        self.name = name or ""
        self.id = hash_node_id(host, port)
        self.failures = 0
        self.burned_until = 0

    def is_burned(self):
        return time.time() < self.burned_until

    def record_failure(self):
        self.failures += 1
        if self.failures >= NODE_MAX_FAILURES:
            self.burned_until = time.time() + BURNED_NODE_SHUTDOWN_SECONDS

    def revive_if_needed(self):
        if self.is_burned() and time.time() >= self.burned_until:
            self.failures = 0
            self.burned_until = 0

    def to_dict(self):
        return {
            "id": self.id,
            "destination": {"host": self.host, "port": self.port},
            "name": self.name,
        }

class LoadBalancer:
    def __init__(self):
        self.nodes = {}
        self.start_time = time.time()
        self.rr_counter = -1

    def registration_open(self):
        return time.time() < self.start_time + REGISTRATION_DURATION_SECONDS

    def add_node(self, host, port, name=None):
        node_id = hash_node_id(host, port)
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if name:
                node.name = name
            node.revive_if_needed()
        else:
            node = Node(host, port, name)
            self.nodes[node.id] = node
        return node_id

    def list_nodes(self):
        for node in self.nodes.values():
            node.revive_if_needed()
        return [node.to_dict() for node in self.nodes.values()]

    def get_node_round_robin(self):
        active_nodes = [n for n in self.nodes.values() if not n.is_burned()]
        if not active_nodes:
            return None
        self.rr_counter = (self.rr_counter + 1) % len(active_nodes)
        return active_nodes[self.rr_counter]

    def record_failure(self, node_id):
        node = self.nodes.get(node_id)
        if node:
            node.record_failure()