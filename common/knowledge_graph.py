import networkx as nx
import pickle
import os
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib

class KnowledgeGraph:
    """
    Lightweight knowledge graph using NetworkX.
    Stores notes as nodes and relationships as edges (Obsidian-style).
    """

    def __init__(self, graph_path: str = "data/knowledge_graph.pkl"):
        self.graph_path = graph_path
        self.graph = nx.MultiDiGraph()  # Directed graph with multiple edges
        self._load_graph()

    def _load_graph(self):
        """Load existing graph from disk"""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'rb') as f:
                    self.graph = pickle.load(f)
                print(f"📊 Loaded knowledge graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            except Exception as e:
                print(f"⚠️  Error loading graph: {e}. Starting fresh.")
                self.graph = nx.MultiDiGraph()
        else:
            print("📊 Initializing new knowledge graph")

    def _save_graph(self):
        """Persist graph to disk"""
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
        with open(self.graph_path, 'wb') as f:
            pickle.dump(self.graph, f)

    def _generate_node_id(self, title: str, content: str) -> str:
        """Generate unique node ID from content"""
        content_hash = hashlib.md5(f"{title}{content}".encode()).hexdigest()[:12]
        return f"node_{content_hash}"

    def add_note(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a note/content as a node in the graph.
        Returns the node ID.
        """
        node_id = self._generate_node_id(title, content)

        # Create node attributes
        node_attrs = {
            'title': title,
            'content': content,
            'tags': tags or [],
            'created_at': datetime.now().isoformat(),
            'type': 'webpage' if url else 'note',
            'metadata': metadata or {}
        }

        if url:
            node_attrs['url'] = url

        # Add node to graph
        self.graph.add_node(node_id, **node_attrs)

        # Parse and create bidirectional links from [[Note]] syntax
        self._parse_and_create_links(node_id, content, title)

        # Auto-link based on tags (connect notes with shared tags)
        if tags:
            self._auto_link_by_tags(node_id, tags)

        self._save_graph()
        return node_id

    def _parse_and_create_links(self, source_id: str, content: str, title: str):
        """
        Parse [[Note Title]] syntax and create bidirectional links.
        This is the core Obsidian-style linking feature.
        """
        # Find all [[links]] in content and title
        link_pattern = r'\[\[([^\]]+)\]\]'
        matches = re.findall(link_pattern, content + " " + title)

        for link_text in matches:
            link_text = link_text.strip()

            # Find or create target note
            target_id = self._find_note_by_title(link_text)

            if not target_id:
                # Create placeholder note for this link
                target_id = self._create_placeholder_note(link_text)

            # Create bidirectional "mentions" edges
            self.graph.add_edge(
                source_id,
                target_id,
                relationship='mentions',
                reason=f"[[{link_text}]] reference",
                created_at=datetime.now().isoformat()
            )

            # Reverse edge for backlinks
            self.graph.add_edge(
                target_id,
                source_id,
                relationship='mentioned-by',
                reason=f"Backlink from note",
                created_at=datetime.now().isoformat()
            )

            print(f"🔗 Created bidirectional link: {source_id} ↔ {target_id}")

    def _find_note_by_title(self, title: str) -> Optional[str]:
        """Find existing note by title (case-insensitive)"""
        title_lower = title.lower()
        for node_id, data in self.graph.nodes(data=True):
            if data.get('title', '').lower() == title_lower:
                return node_id
        return None

    def _create_placeholder_note(self, title: str) -> str:
        """
        Create a placeholder note for a [[link]] that doesn't exist yet.
        This is like Obsidian's "unresolved links" feature.
        """
        node_id = self._generate_node_id(title, f"Placeholder for {title}")

        self.graph.add_node(
            node_id,
            title=title,
            content=f"# {title}\n\n*This note was created as a placeholder for a [[link]]. Add content to complete it.*",
            tags=['placeholder', 'unresolved'],
            created_at=datetime.now().isoformat(),
            type='placeholder',
            metadata={'is_placeholder': True}
        )

        print(f"📝 Created placeholder note: {title}")
        return node_id

    def _parse_tag_hierarchy(self, tag: str) -> List[str]:
        """
        Parse hierarchical tag like 'ai/ml/nlp' into all levels.
        Returns: ['ai', 'ai/ml', 'ai/ml/nlp']
        """
        if '/' not in tag:
            return [tag]

        parts = tag.split('/')
        hierarchy = []
        for i in range(len(parts)):
            hierarchy.append('/'.join(parts[:i+1]))

        return hierarchy

    def _expand_tags_with_hierarchy(self, tags: List[str]) -> List[str]:
        """
        Expand tags to include all hierarchy levels.
        Input: ['ai/ml/nlp', 'research']
        Output: ['ai', 'ai/ml', 'ai/ml/nlp', 'research']
        """
        expanded = []
        for tag in tags:
            expanded.extend(self._parse_tag_hierarchy(tag))

        return list(set(expanded))  # Remove duplicates

    def _auto_link_by_tags(self, node_id: str, tags: List[str]):
        """
        Automatically create edges between notes that share tags.
        Supports hierarchical tags like 'ai/ml/nlp'.
        This creates an Obsidian-style automatic linking.
        """
        # Expand tags to include hierarchy
        expanded_tags = self._expand_tags_with_hierarchy(tags)

        # Find other nodes with overlapping tags
        for other_node in self.graph.nodes():
            if other_node == node_id:
                continue

            other_tags = self.graph.nodes[other_node].get('tags', [])
            other_expanded = self._expand_tags_with_hierarchy(other_tags)

            # Find shared tags (considering hierarchy)
            shared_tags = set(expanded_tags) & set(other_expanded)

            if shared_tags:
                # Determine relationship strength based on hierarchy depth
                # More specific tags = stronger connection
                max_depth = max(tag.count('/') for tag in shared_tags)
                relationship_type = 'strongly-related' if max_depth >= 2 else 'related-to'

                # Create bidirectional edges
                self.graph.add_edge(
                    node_id,
                    other_node,
                    relationship=relationship_type,
                    reason=f"Shared tags: {', '.join(shared_tags)}",
                    strength=len(shared_tags),
                    created_at=datetime.now().isoformat()
                )
                self.graph.add_edge(
                    other_node,
                    node_id,
                    relationship=relationship_type,
                    reason=f"Shared tags: {', '.join(shared_tags)}",
                    strength=len(shared_tags),
                    created_at=datetime.now().isoformat()
                )

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a relationship edge between two notes.

        Common relationship types:
        - 'mentions': Source mentions target
        - 'cites': Source cites target
        - 'related-to': General relationship
        - 'builds-on': Source builds on target's ideas
        """
        edge_attrs = {
            'relationship': relationship,
            'created_at': datetime.now().isoformat()
        }

        if metadata:
            edge_attrs.update(metadata)

        self.graph.add_edge(source_id, target_id, **edge_attrs)
        self._save_graph()

    def get_related_notes(self, node_id: str, max_depth: int = 2) -> List[Dict]:
        """
        Get notes connected to this node (within max_depth).
        Returns list of related notes with their metadata.
        """
        if node_id not in self.graph:
            return []

        # Use BFS to find connected nodes within max_depth
        related = []
        visited = {node_id}
        queue = [(node_id, 0)]  # (node, depth)

        while queue:
            current, depth = queue.pop(0)

            if depth >= max_depth:
                continue

            # Get neighbors (both directions)
            neighbors = list(self.graph.neighbors(current)) + \
                       list(self.graph.predecessors(current))

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

                    # Get node attributes
                    node_data = self.graph.nodes[neighbor]

                    # Get edge relationship
                    edges = list(self.graph.get_edge_data(current, neighbor, default={}).values()) + \
                           list(self.graph.get_edge_data(neighbor, current, default={}).values())

                    relationship = edges[0].get('relationship', 'related-to') if edges else 'related-to'

                    related.append({
                        'id': neighbor,
                        'title': node_data.get('title', 'Untitled'),
                        'tags': node_data.get('tags', []),
                        'relationship': relationship,
                        'depth': depth + 1,
                        'content_preview': node_data.get('content', '')[:200]
                    })

        return related

    def search_by_tag(self, tag: str, include_hierarchy: bool = True) -> List[Dict]:
        """
        Find all notes with a specific tag.
        Supports hierarchical tags if include_hierarchy=True.

        Examples:
        - search_by_tag('ai') finds notes with 'ai', 'ai/ml', 'ai/ml/nlp', etc.
        - search_by_tag('ai', include_hierarchy=False) finds only exact 'ai' tag
        """
        results = []
        tag_lower = tag.lower()

        for node_id, data in self.graph.nodes(data=True):
            node_tags = data.get('tags', [])

            # Expand tags if hierarchy enabled
            if include_hierarchy:
                expanded_tags = self._expand_tags_with_hierarchy(node_tags)
                tag_matches = [t.lower() for t in expanded_tags]
            else:
                tag_matches = [t.lower() for t in node_tags]

            if tag_lower in tag_matches:
                results.append({
                    'id': node_id,
                    'title': data.get('title', 'Untitled'),
                    'tags': node_tags,  # Show original tags
                    'created_at': data.get('created_at'),
                    'content_preview': data.get('content', '')[:200]
                })

        return results

    def get_backlinks(self, node_id: str) -> List[Dict]:
        """
        Get all notes that link TO this note (backlinks).
        This is essential for Obsidian-style bidirectional linking.
        """
        if node_id not in self.graph:
            return []

        backlinks = []

        # Get all incoming edges (predecessors)
        for predecessor in self.graph.predecessors(node_id):
            # Get edge data
            edge_data = self.graph.get_edge_data(predecessor, node_id)

            node_data = self.graph.nodes[predecessor]

            backlinks.append({
                'id': predecessor,
                'title': node_data.get('title', 'Untitled'),
                'relationship': edge_data.get('relationship', 'unknown'),
                'created_at': node_data.get('created_at'),
                'content_preview': node_data.get('content', '')[:200],
                'tags': node_data.get('tags', [])
            })

        return backlinks

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get full node data by ID"""
        if node_id not in self.graph:
            return None

        return dict(self.graph.nodes[node_id])

    def get_stats(self) -> Dict:
        """Get graph statistics"""
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'avg_connections': round(
                self.graph.number_of_edges() / max(1, self.graph.number_of_nodes()), 2
            ),
            'tags': self._get_all_tags()
        }

    def _get_all_tags(self) -> Dict[str, int]:
        """Get all tags and their frequencies"""
        tag_counts = {}

        for _, data in self.graph.nodes(data=True):
            for tag in data.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    def visualize_connections(self, node_id: str, depth: int = 1) -> str:
        """
        Generate a text-based visualization of connections.
        Shows how notes are linked (Obsidian-style).
        """
        if node_id not in self.graph:
            return "Node not found"

        center_node = self.graph.nodes[node_id]
        output = f"📊 **{center_node.get('title', 'Untitled')}**\n"
        output += f"Tags: {', '.join(center_node.get('tags', []))}\n\n"

        related = self.get_related_notes(node_id, max_depth=depth)

        if not related:
            output += "No connections yet.\n"
        else:
            output += f"Connected to {len(related)} notes:\n\n"

            for note in related[:10]:  # Limit to first 10
                indent = "  " * note['depth']
                output += f"{indent}→ **{note['title']}**\n"
                output += f"{indent}  ({note['relationship']}) - Tags: {', '.join(note['tags'])}\n"

        return output

# Global instance
knowledge_graph = KnowledgeGraph()
