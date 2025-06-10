import requests
import logging
from flask import Blueprint, request, jsonify, Response, abort
from load_balancer.load_balancer import LoadBalancer

loadbalancer_api = Blueprint("loadbalancer_api", __name__)
lb = LoadBalancer()
logger = logging.getLogger('load_balancer')

def validate_text(val, max_length):
    return (
        isinstance(val, str)
        and len(val) <= max_length
        and all(c.isalnum() or c in "_-" for c in val)
    )

@loadbalancer_api.route("/internal/nodes", methods=["POST"])
def register_node():
    logger.info('Received node registration request')
    
    if not lb.registration_open():
        logger.warning('Node registration rejected: registration period is over')
        return jsonify({"errorMessage": "the request was rejected because registration period is over"}), 403

    payload = request.get_json(force=True, silent=True)
    if not payload or "destination" not in payload:
        logger.error('Node registration failed: missing destination in payload')
        return jsonify({"errorMessage": "Missing destination"}), 400

    dest = payload["destination"]
    host = dest.get("host")
    port = dest.get("port")
    name = payload.get("name", "")

    if not host or not validate_text(host, 50):
        logger.error(f'Node registration failed: invalid host "{host}"')
        return jsonify({"errorMessage": "Invalid host in destination"}), 400
    try:
        port = int(port)
        if not (0 < port <= 65535):
            raise ValueError()
    except Exception:
        logger.error(f'Node registration failed: invalid port "{port}"')
        return jsonify({"errorMessage": "Invalid port in destination"}), 400
    if name and not validate_text(name, 50):
        logger.error(f'Node registration failed: invalid name "{name}"')
        return jsonify({"errorMessage": "Invalid name"}), 400

    node_id = lb.add_node(host, port, name)
    logger.info(f'Successfully registered node {name} at {host}:{port} with ID: {node_id}')
    return jsonify({"id": node_id}), 200

@loadbalancer_api.route("/internal/nodes", methods=["GET"])
def get_nodes():
    nodes = lb.list_nodes()
    logger.info(f'Nodes list requested - returning {len(nodes)} nodes')
    return jsonify({"data": nodes}), 200

@loadbalancer_api.route("/blobs/<blob_id>", methods=["GET", "POST", "DELETE"])
def proxy_blob(blob_id):
    logger.info(f'Received {request.method} request for blob: {blob_id}')
    
    if lb.registration_open():
        logger.warning(f'Blob operation rejected: registration period is still active')
        return jsonify({"errorMessage": "blob operations are not available during registration period"}), 403
    
    node = lb.get_node_round_robin()
    if not node:
        logger.error('No available backend nodes for request')
        return Response("No available backend nodes", status=503)

    url = f"http://{node.host}:{node.port}/api/v0/blobs/{blob_id}"
    logger.info(f'Proxying {request.method} request to node {node.name} ({node.host}:{node.port})')

    try:
        headers = {k: v for k, v in request.headers if k.lower() != 'host'}
        method = request.method
        
        if method == "GET" or method == "DELETE":
            res = requests.request(method, url, headers=headers, stream=True, timeout=5)
        elif method == "POST":
            content_length = request.headers.get('Content-Length')
            if content_length:
                data = request.get_data()
                res = requests.request(method, url, headers=headers, data=data, timeout=5)
            else:
                res = requests.request(method, url, headers=headers, data=request.get_data(), timeout=5)
        else:
            logger.error(f'Unsupported HTTP method: {method}')
            abort(405)

        logger.info(f'Backend response: {res.status_code} from node {node.name}')
        
        def generate():
            for chunk in res.iter_content(8192):
                yield chunk

        return Response(generate(), status=res.status_code, headers=dict(res.headers))

    except requests.exceptions.RequestException as e:
        logger.error(f'Backend node {node.name} ({node.id}) failed: {str(e)}')
        lb.record_failure(node.id)
        return Response(f"Backend node {node.id} failed", status=503)