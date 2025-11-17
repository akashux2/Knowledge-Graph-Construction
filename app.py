# app.py
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import json
import networkx as nx
from pyvis.network import Network
import os
import re
import requests
from bs4 import BeautifulSoup
import uuid
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import io
import csv
from openai import OpenAI

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'
GRAPH_FOLDER = os.path.join(STATIC_FOLDER, 'graphs')
for folder in [UPLOAD_FOLDER, STATIC_FOLDER, GRAPH_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# OpenRouter client setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"  # Replace with your API key
)

def extract_knowledge(text):
    try:
        completion = client.chat.completions.create(
            model="qwen/qwen2.5-vl-72b-instruct:free",
            messages=[
                {
                    "role": "user",
                    "content": f""" Extract entities and relations from the following text:  
                    
                    \"{text}\"  
                    
                    Reply ONLY in this JSON format: 
                    {{
                       "entities": ["Entity1", "Entity2", ...],
                       "relations": [["Entity1", "Relation", "Entity2"], ...] 
                    }}
                    """
                }
            ]
        )
        
        response_text = completion.choices[0].message.content
        
        # Attempt to clean the response if it's not valid JSON
        try:
            json.loads(response_text)
            return response_text
        except json.JSONDecodeError:
            # Try to extract JSON from the response using regex
            json_match = re.search(r'({.*})', response_text.replace('\n', ''), re.DOTALL)
            if json_match:
                try:
                    extracted_json = json_match.group(1)
                    json.loads(extracted_json)  # Validate it's proper JSON
                    return extracted_json
                except:
                    pass
            
            # If all else fails, create a minimal valid response
            return '{"entities": [], "relations": []}'
    except Exception as e:
        print(f"Error in extract_knowledge: {e}")
        return '{"entities": [], "relations": []}'

def create_graph(result_json, filename=None):
    try:
        parsed_data = json.loads(result_json)
        entities = parsed_data.get('entities', [])
        relations = parsed_data.get('relations', [])
        
        G = nx.DiGraph()
        
        # Add nodes with custom group for visual differentiation
        for i, entity in enumerate(entities):
            # Assign groups cyclically for visual differentiation
            group = (i % 5) + 1
            G.add_node(entity, group=group)
        
        # Add edges with relationship labels
        for rel in relations:
            source, relation, target = rel
            G.add_edge(source, target, label=relation)
        
        # Generate unique ID for the graph
        graph_id = filename or f"graph_{uuid.uuid4().hex[:8]}"
        
        # Create interactive network visualization
        net = Network(height='700px', width='100%', bgcolor='#ffffff', font_color='black', directed=True)
        net.from_nx(G)
        
        # Enhanced styling
        for node in net.nodes:
            group = G.nodes[node['id']].get('group', 1)
            
            # Color palette based on group
            colors = {
                1: "#4287f5",  # Blue
                2: "#f54242",  # Red
                3: "#42f54e",  # Green
                4: "#f5a742",  # Orange
                5: "#9942f5",  # Purple
            }
            
            node['size'] = 25
            node['color'] = {
                "background": colors.get(group, "#6a0dad"),
                "border": "#333333",
                "highlight": {"background": "#ffff00", "border": "#000000"}
            }
            node['font'] = {
                "size": 16,
                "face": "Arial",
                "color": "#000000",
                "bold": True
            }
            node['shape'] = 'dot'
            node['borderWidth'] = 2
            node['shadow'] = True
        
        for edge in net.edges:
            edge['color'] = {"color": "#888888", "opacity": 0.8}
            edge['width'] = 2
            edge['font'] = {
                "size": 14,
                "face": "Arial",
                "color": "#3366CC",
                "strokeWidth": 1,
                "strokeColor": "#ffffff"
            }
            edge['arrows'] = {'to': {'enabled': True, 'type': 'arrow'}}
            edge['smooth'] = {'type': 'continuous'}
        
        # Configure physics for better layout
        net.set_options("""
        var options = {
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08
                },
                "solver": "forceAtlas2Based",
                "minVelocity": 0.75,
                "timestep": 0.5
            },
            "interaction": {
                "hover": true,
                "navigationButtons": true,
                "keyboard": true
            }
        }
        """)
        
        # Save the graph
        graph_path = os.path.join(GRAPH_FOLDER, f"{graph_id}.html")
        net.save_graph(graph_path)
        
        # Also save the data as JSON for potential reuse
        data_path = os.path.join(GRAPH_FOLDER, f"{graph_id}.json")
        with open(data_path, 'w') as f:
            json.dump(parsed_data, f, indent=2)
        
        return graph_id
    
    except Exception as e:
        print(f"⚠️ Error in create_graph: {e}")
        return None

def scrape_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Remove extra whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        print(f"Error scraping URL: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    text = ""
    source_type = "text"
    filename = None
    
    if 'text' in request.form and request.form['text'].strip():
        text = request.form['text'].strip()
        source_type = "text"
        filename = f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    elif 'url' in request.form and request.form['url'].strip():
        url = request.form['url'].strip()
        source_type = "url"
        safe_url = re.sub(r'[^\w]', '_', url)
        filename = f"url_{safe_url[:30]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        text = scrape_text_from_url(url)
        if not text:
            return render_template('error.html', message="Could not extract text from the provided URL.")

    
    elif 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        source_type = "file"
        filename = f"file_{os.path.splitext(file.filename)[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            text = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return render_template('error.html', message="File encoding not supported. Please upload a UTF-8 encoded text file.")
    
    else:
        return render_template('error.html', message="Please provide text, URL, or file to generate a knowledge graph.")
    
    # Limit text size if necessary to avoid API issues
    if len(text) > 10000:
        text = text[:10000]
    
    result_json = extract_knowledge(text)
    graph_id = create_graph(result_json, filename)
    
    if graph_id:
        return redirect(url_for('view_graph', graph_id=graph_id))
    else:
        return render_template('error.html', message="Failed to generate knowledge graph. Please try again.")

@app.route('/view_graph/<graph_id>')
def view_graph(graph_id):
    # Load the graph data for additional statistics
    try:
        with open(os.path.join(GRAPH_FOLDER, f"{graph_id}.json"), 'r') as f:
            graph_data = json.load(f)
            
        entity_count = len(graph_data.get('entities', []))
        relation_count = len(graph_data.get('relations', []))
        
        return render_template(
            'view_graph.html', 
            graph_id=graph_id,
            entity_count=entity_count,
            relation_count=relation_count,
            graph_data=json.dumps(graph_data)
        )
    except Exception as e:
        print(f"Error loading graph data: {e}")
        return render_template('error.html', message="Failed to load graph data.")

@app.route('/graphs')
def list_graphs():
    graphs = []
    for file in os.listdir(GRAPH_FOLDER):
        if file.endswith('.html'):
            graph_id = os.path.splitext(file)[0]
            try:
                # Get creation time
                created = datetime.fromtimestamp(os.path.getctime(os.path.join(GRAPH_FOLDER, file)))
                
                # Try to load corresponding JSON for stats
                json_path = os.path.join(GRAPH_FOLDER, f"{graph_id}.json")
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                        entities = len(data.get('entities', []))
                        relations = len(data.get('relations', []))
                else:
                    entities = 0
                    relations = 0
                
                graphs.append({
                    'id': graph_id,
                    'created': created.strftime('%Y-%m-%d %H:%M:%S'),
                    'entities': entities,
                    'relations': relations
                })
            except Exception as e:
                print(f"Error processing graph {file}: {e}")
    
    # Sort by creation date, newest first
    graphs.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('graphs.html', graphs=graphs)

@app.route('/download/<graph_id>/<format>')
def download_graph(graph_id, format):
    json_path = os.path.join(GRAPH_FOLDER, f"{graph_id}.json")
    
    if not os.path.exists(json_path):
        return jsonify({"error": "Graph not found"}), 404
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    if format == 'json':
        # Return JSON file
        return send_file(
            json_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=f"{graph_id}.json"
        )
    
    elif format == 'csv':
        # Create CSV file
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write entities
        writer.writerow(['Entity'])
        for entity in data.get('entities', []):
            writer.writerow([entity])
        
        writer.writerow([])  # Empty row as separator
        
        # Write relations
        writer.writerow(['Source', 'Relation', 'Target'])
        for relation in data.get('relations', []):
            writer.writerow(relation)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{graph_id}.csv"
        )
    
    elif format == 'png' or format == 'svg':
        # Create a static image using networkx and matplotlib
        G = nx.DiGraph()
        
        for entity in data.get('entities', []):
            G.add_node(entity)
        
        for source, relation, target in data.get('relations', []):
            G.add_edge(source, target, label=relation)
        
        plt.figure(figsize=(12, 10))
        pos = nx.spring_layout(G, seed=42)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue', edgecolors='black')
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, width=2, alpha=0.7, edge_color='gray', arrows=True, arrowsize=20)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
        
        # Draw edge labels
        edge_labels = {(source, target): G[source][target]['label'] for source, target in G.edges()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        
        plt.axis('off')
        plt.tight_layout()
        
        img_data = io.BytesIO()
        plt.savefig(img_data, format=format, bbox_inches='tight', transparent=True, dpi=300)
        img_data.seek(0)
        plt.close()
        
        return send_file(
            img_data,
            mimetype=f'image/{format}',
            as_attachment=True,
            download_name=f"{graph_id}.{format}"
        )
    
    else:
        return jsonify({"error": "Invalid format requested"}), 400

@app.route('/search', methods=['POST'])
def search_graph():
    graph_id = request.form.get('graph_id')
    query = request.form.get('query', '').lower()
    
    json_path = os.path.join(GRAPH_FOLDER, f"{graph_id}.json")
    
    if not os.path.exists(json_path):
        return jsonify({"error": "Graph not found"}), 404
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    results = {
        "entities": [],
        "relations": []
    }
    
    # Search entities
    for entity in data.get('entities', []):
        if query in entity.lower():
            results["entities"].append(entity)
    
    # Search relations
    for relation in data.get('relations', []):
        source, rel, target = relation
        if query in source.lower() or query in rel.lower() or query in target.lower():
            results["relations"].append(relation)
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)