import itertools
from queue import LifoQueue


class Node:
    def __init__(self, id, lemma=None, form=None, sent_name=None, pos_tag=None, pos_extended=None, is_included=False, num_deep_children=0):
        self.id = id
        self.lemma = lemma
        self.form = form
        self.sent_name = sent_name
        self.pos_tag = pos_tag
        self.pos_extended = pos_extended
        self.is_included = is_included
        self.num_deep_children = num_deep_children


class Edge:
    def __init__(self, node_id_from, node_id_to, weight=None):
        self.node_from = node_id_from
        self.node_to = node_id_to
        self.weight = weight  # relation type


class Tree:

    def __init__(self):
        self.edges = []
        self.nodes = []
        self.created = set()
        self.heights = {}
        self.edges_dict_from = {}
        self.edges_dict_to = {}
        self.nodes_dict_id = {}
        self.additional_nodes = set()
        self.similar_lemmas = {}
        self.global_similar_mapping = {}
        self.dict_lemmas = {}
        self.dict_lemmas_rev = []

    @staticmethod
    def copy_node_details(existing_node, id_count):
        new_node = Node(id=id_count,
                        form=existing_node.form,
                        sent_name=existing_node.sent_name,
                        is_included=existing_node.is_included,
                        pos_tag=existing_node.pos_tag,
                        pos_extended=existing_node.pos_extended)
        return new_node

    def set_help_dict(self):
        self.edges_dict_from = {k: list(v) for k, v in itertools.groupby(sorted(self.edges, key=lambda x: x.node_from),
                                                                         key=lambda x: x.node_from)}
        self.nodes_dict_id = {node.id: node for node in self.nodes}
        self.edges_dict_to = {k: list(v) for k, v in
                              itertools.groupby(sorted(self.edges, key=lambda x: x.node_to), key=lambda x: x.node_to)}
        self.node_id_sent = {node.id: node.sent_name for node in self.nodes}

    def add_node(self, node):
        self.nodes.append(node)

    def add_edge(self, edge):
        self.edges.append(edge)

    def get_node(self, node_id):
        return self.nodes_dict_id.get(node_id)  # return Node class instance

    def get_edge(self, to_id):
        return self.edges_dict_to.get(to_id)

    def remove_edge(self, to_id):
        self.edges = list(filter(lambda x: x.node_to != to_id, self.edges))

    def get_children(self, node_id):
        edges = self.edges_dict_from.get(node_id)
        return set(map(lambda x: x.node_to, edges if edges is not None else []))

    def add_new_edges(self, new_node_id, children):
        for child_id in children:
            new_edge = Edge(new_node_id, child_id, self.get_edge(child_id)[0].weight)
            if child_id in self.edges_dict_to.keys():
                self.edges_dict_to[child_id].append(new_edge)
            else:
                self.edges_dict_to[child_id] = [new_edge]
            self.edges.append(new_edge)
            if new_node_id in self.edges_dict_from.keys():
                self.edges_dict_from[new_node_id].append(new_edge)
            else:
                self.edges_dict_from[new_node_id] = [new_edge]

    def add_edge_to_dict(self, edge):
        self.edges_dict_to[edge.node_to] = [edge]
        if edge.node_from in self.edges_dict_from.keys():
            self.edges_dict_from[edge.node_from].append(edge)
        else:
            self.edges_dict_from[edge.node_from] = edge
        self.edges.append(edge)

    def add_node_to_dict(self, node):
        self.nodes_dict_id[node.id] = node
        self.created.add(node.id)
        self.nodes.append(node)

    def get_children_nodes(self, children):
        children_nodes = {str(Tree.get_edge(self, child)[0].weight) + str(Tree.get_node(self, child).lemma): child for
                          child in children}
        return children_nodes

    def create_new_node(self, new_id, lemma, form, sent, pos_tag, pos_extended, weight, from_id):
        new_node = Node(new_id, lemma, form, sent, pos_tag, pos_extended)
        Tree.add_node(self, new_node)
        new_edge = Edge(from_id, new_id, weight)
        Tree.add_edge(self, new_edge)

    def get_target_from_children(self, children, subtree_node):
        children_nodes = Tree.get_children_nodes(self, children)
        return children_nodes[subtree_node]

    def calculate_heights(self):
        visited = {node.id: False for node in self.nodes}
        stack = LifoQueue()
        stack.put(0)
        prev = None
        while stack.qsize() > 0:
            curr = stack.get()
            stack.put(curr)
            if not visited[curr]:
                visited[curr] = True
            children = self.get_children(curr)
            if len(children) == 0:
                self.heights[curr] = [0]
                prev = curr
                stack.get()
            else:
                all_visited_flag = True
                children_filtered = set(children) - self.additional_nodes
                for child in children_filtered:
                    if not visited[child]:
                        all_visited_flag = False
                        stack.put(child)
                if all_visited_flag:
                    curr_height = []
                    if len(children_filtered) > 1:
                        for child in children_filtered:
                            for child_height in self.heights[child]:
                                curr_height.append(child_height + 1)
                    else:
                        curr_height = [h + 1 for h in self.heights[prev]]
                    self.heights[curr] = list(set(curr_height))
                    prev = curr
                    stack.get()

    def simple_dfs(self, root_id, subtree_vertices):
        node_sequence = []
        parents_dict = {}
        node = self.get_node(root_id)
        if node is not None:
            node_sequence.append(node)
            visited = []
            stack = [root_id]
            while len(stack) > 0:
                curr = stack[-1]
                if curr not in visited:
                    visited.append(curr)
                children = sorted(self.get_children(curr))
                if len(children) == 0:
                    stack.pop()
                else:
                    all_visited_flag = True
                    for child in children:
                        if child in subtree_vertices and child not in visited:
                            all_visited_flag = False
                            stack.append(child)
                            parents_dict[child] = curr
                            node = self.get_node(child)
                            node_sequence.append(node)
                    if all_visited_flag:
                        stack.pop()
        return node_sequence

    def dfs_subtree(self, vertex, subtree_vertices):
        sequence = []
        node = self.get_node(vertex)
        if node is not None:
            sequence.append(vertex)
            visited = []
            stack = [vertex]
            while len(stack) > 0:
                curr = stack[-1]
                if curr not in visited:
                    visited.append(curr)
                children = self.get_children(curr)
                if len(children) == 0:
                    stack.pop()
                else:
                    all_visited_flag = True
                    for child in children:
                        if child in subtree_vertices and child not in visited:
                            all_visited_flag = False
                            stack.append(child)
                            sequence.append(child)
                    if all_visited_flag:
                        stack.pop()
        return sequence
