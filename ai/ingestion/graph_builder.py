import yaml
import re
from pathlib import Path

def load_navigation(mkdocs_file="mkdocs.yml"):

    with open(mkdocs_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove python-specific YAML tags used by MkDocs plugins
    content = re.sub(r"!!python/name:[^\s]+", "null", content)

    config = yaml.safe_load(content)

    return config.get("nav", [])


def slugify(name):

    return name.lower().replace(" ", "-").replace("/", "-")


def build_graph(nav):

    nodes = []
    edges = []

    def process_nav(items, parent=None):

        for item in items:

            # Case 1 — named section or page
            if isinstance(item, dict):

                for title, value in item.items():

                    node_id = slugify(title)

                    nodes.append({
                        "id": node_id,
                        "label": title,
                        "type": "section" if isinstance(value, list) else "document"
                    })

                    if parent:
                        edges.append({
                            "from": parent,
                            "to": node_id,
                            "type": "contains"
                        })

                    if isinstance(value, list):
                        process_nav(value, node_id)

            # Case 2 — direct document path
            elif isinstance(item, str):

                title = Path(item).stem.replace("-", " ").replace("_", " ")

                node_id = slugify(title)

                nodes.append({
                    "id": node_id,
                    "label": title,
                    "type": "document",
                    "path": item
                })

                if parent:
                    edges.append({
                        "from": parent,
                        "to": node_id,
                        "type": "contains"
                    })

    process_nav(nav)

    return {
        "nodes": nodes,
        "edges": edges
    }

if __name__ == "__main__":

    nav = load_navigation()

    graph = build_graph(nav)

    print("Nodes:", len(graph["nodes"]))
    print("Edges:", len(graph["edges"]))