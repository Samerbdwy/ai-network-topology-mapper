from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from topology_mapper import TopologyMapper
import networkx as nx
import plotly.graph_objs as go
import plotly.utils
import json as json_lib
import math

app = Flask(__name__)
CORS(app)
mapper = TopologyMapper()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan():
    data = request.json
    network_cidr = data.get('network', '192.168.1.0/24')
    
    devices = mapper.discover_devices(network_cidr)
    
    if isinstance(devices, dict) and "error" in devices:
        return jsonify({'success': False, 'error': devices["error"]})
    
    insights = mapper.get_ai_insights(devices, network_cidr)
    graph = build_topology_graph(devices)
    topology_json = generate_topology_viz(graph, len(devices))
    
    return jsonify({
        'success': True,
        'devices': devices,
        'count': len(devices),
        'insights': insights.get('insights', ''),
        'recommendations': insights.get('recommendations', ''),
        'topology': topology_json
    })

def build_topology_graph(devices):
    G = nx.Graph()
    if not devices:
        return G
    
    for device in devices:
        G.add_node(device['ip'])
    
    # Find gateway
    gateway = None
    for ip in ['192.168.1.1', '192.168.1.254', '10.0.0.1', '172.16.0.1']:
        if ip in [d['ip'] for d in devices]:
            gateway = ip
            break
    
    if not gateway and devices:
        gateway = devices[0]['ip']
    
    if gateway:
        for device in devices:
            if device['ip'] != gateway:
                G.add_edge(gateway, device['ip'])
    
    return G

def generate_topology_viz(graph, device_count):
    """Generate topology visualization optimized for network size"""
    if len(graph.nodes()) == 0:
        return json_lib.dumps({})
    
    node_count = len(graph.nodes())
    
    # DYNAMIC SIZING BASED ON NETWORK SIZE
    if node_count > 100:
        # For very large networks - use circular layout (cleaner)
        pos = nx.circular_layout(graph)
        node_size = 8
        font_size = 7
        line_width = 0.8
        show_labels = False  # Hide labels for large networks (too cluttered)
        edge_width = 0.5
        height = 500
    elif node_count > 50:
        # For large networks
        pos = nx.spring_layout(graph, k=2, iterations=30, seed=42)
        node_size = 12
        font_size = 8
        line_width = 1
        show_labels = True
        edge_width = 0.8
        height = 450
    elif node_count > 20:
        # For medium networks
        pos = nx.spring_layout(graph, k=1.5, iterations=40, seed=42)
        node_size = 16
        font_size = 9
        line_width = 1.5
        show_labels = True
        edge_width = 1
        height = 400
    else:
        # For small networks
        pos = nx.spring_layout(graph, k=1, iterations=50, seed=42)
        node_size = 22
        font_size = 10
        line_width = 2
        show_labels = True
        edge_width = 1.5
        height = 400
    
    # Find gateway for coloring
    gateway = None
    for node in graph.nodes():
        if node.endswith('.1') or node.endswith('.254'):
            gateway = node
            break
    if not gateway and node_count > 0:
        gateway = list(graph.nodes())[0]
    
    # SAMPLE NODES FOR VERY LARGE NETWORKS (performance)
    sampled_nodes = list(graph.nodes())
    if node_count > 150:
        # Only show gateway + random sample of 100 devices
        other_nodes = [n for n in graph.nodes() if n != gateway]
        import random
        random.seed(42)
        sampled_other = random.sample(other_nodes, min(100, len(other_nodes)))
        sampled_nodes = [gateway] + sampled_other
        is_sampled = True
    else:
        is_sampled = False
    
    # Create a subgraph with sampled nodes
    if is_sampled:
        subgraph = graph.subgraph(sampled_nodes)
        pos = {node: pos[node] for node in sampled_nodes if node in pos}
    else:
        subgraph = graph
    
    # Edges with dynamic styling
    edge_traces = []
    for edge in subgraph.edges():
        if edge[0] in pos and edge[1] in pos:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_traces.append(go.Scatter(
                x=[x0, x1, None], 
                y=[y0, y1, None],
                mode='lines',
                line=dict(width=edge_width, color='#8b5cf6'),
                hoverinfo='none',
                showlegend=False
            ))
    
    # Nodes
    node_x, node_y, node_text, node_colors, node_sizes = [], [], [], [], []
    
    for node in subgraph.nodes():
        if node in pos:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Truncate label if too long
            if show_labels and not is_sampled:
                node_text.append(node)
            else:
                node_text.append(node.split('.')[-1])  # Show only last octet
            
            # Color coding
            if node == gateway:
                node_colors.append('#ef4444')  # Red for gateway
                node_sizes.append(node_size + 4)  # Gateway slightly larger
            else:
                node_colors.append('#10b981')  # Green for devices
                node_sizes.append(node_size)
    
    # Hover text with full IP
    hover_text = [f"IP: {node}<br>{'Gateway/Router' if node == gateway else 'Network Device'}" 
                  for node in subgraph.nodes() if node in pos]
    
    node_trace = go.Scatter(
        x=node_x, 
        y=node_y,
        mode='markers+text' if show_labels else 'markers',
        text=node_text if show_labels else None,
        textposition='top center',
        textfont=dict(size=font_size, color='white'),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=line_width, color='white'),
            symbol='circle'
        ),
        hoverinfo='text',
        hovertext=hover_text
    )
    
    # Build figure with dynamic height
    fig = go.Figure(data=edge_traces + [node_trace])
    
    # Add annotation for sampled networks
    annotations = []
    if is_sampled:
        annotations.append(dict(
            text=f"⚠️ Showing {len(subgraph.nodes())} of {node_count} devices (performance mode)",
            xref="paper", yref="paper",
            x=0.5, y=1.05,
            showarrow=False,
            font=dict(size=11, color='#f59e0b')
        ))
    
    annotations.append(dict(
        text=f"🌐 {node_count} Network Devices",
        xref="paper", yref="paper",
        x=0.5, y=1.02 if not is_sampled else 1.10,
        showarrow=False,
        font=dict(size=12, color='#8b5cf6')
    ))
    
    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=0, r=0, t=40, b=0),
        annotations=annotations
    )
    
    return json_lib.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🗺️  AI Network Topology Mapper (Large Network Optimized)")
    print("="*50)
    print("📍 Ready: http://localhost:5004")
    print("="*50 + "\n")
    app.run(debug=True, port=5004)