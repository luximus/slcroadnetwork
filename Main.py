import networkx as nx
import matplotlib.pyplot as plt
import random

def get_graph():
    graph = nx.random_regular_graph(4, 100).to_directed()
    edges = list(graph.edges)
    chosen_edge = random.choice(edges)
    graph.remove_edge(chosen_edge[0], chosen_edge[1])
    return graph

#Getting a list of nodes
print(list(get_graph().nodes))

#Finding the min distance
dist = {}
prev = {}
q = set()
def dijkstra(graph, source):
    for n in graph.nodes:
        dist[n] = float('inf')
        prev[n] = None
        q.add(n)
    dist[source] = 0

    while q:
        u = q.pop(min(q, key=lambda x: dist[x]))

        for neighbor in (n for n in graph.neighbors(u) if n in q):
            alt = dist[n] + graph[graph][neighbor]["length"] / graph[graph][neighbor]["speed_limit"]
            if alt < dist[neighbor]:
                dist[neighbor] = alt
                prev[neighbor] = n
        return dist, prev







