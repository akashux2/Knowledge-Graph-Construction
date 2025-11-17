# graph_builder.py

import json
import networkx as nx
from pyvis.network import Network
import os

def create_graph(result_json):
    try:
        parsed_data = json.loads(result_json)
        entities = parsed_data.get('entities', [])
        relations = parsed_data.get('relations', [])

        G = nx.DiGraph()

        for entity in entities:
            G.add_node(entity)

        for rel in relations:
            source, relation, target = rel
            G.add_edge(source, target, label=relation)

        net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='black', directed=True)

        net.from_nx(G)

        # Custom styling
        for node in net.nodes:
            node['size'] = 20
            node['color'] = {
                "background": "#6a0dad",  # Purple color
                "border": "#4b0082"
            }
            node['font'] = {
                "size": 20,
                "color": "black",
            }

        for edge in net.edges:
            edge['color'] = {
                "color": "#888"
            }
            edge['width'] = 2
            edge['font'] = {
                "size": 15,
                "color": "blue",
                "strokeWidth": 0,
                "strokeColor": "#ffffff"
            }
            edge['arrows'] = 'to'  # Arrow direction

        output_folder = 'static'
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        graph_file = os.path.join(output_folder, 'graph.html')
        net.save_graph(graph_file)

        return 'graph.html'

    except Exception as e:
        print("⚠️ Error in create_graph:", e)
        return None
