import networkx as nx
import matplotlib.pyplot as plt
import random
from road_data import get_network
from tqdm import tqdm

def get_graph():
    graph = nx.random_regular_graph(4, 100).to_directed()
    edges = list(graph.edges)
    chosen_edge = random.choice(edges)
    graph.remove_edge(chosen_edge[0], chosen_edge[1])
    return graph

#Getting a list of nodes
print(list(get_graph().nodes))

#Finding the min distance 
def dijkstra(graph, source):
    dist = {}
    prev = {}
    q = set()
    for n in graph.nodes:
        dist[n] = float('inf')
        prev[n] = None
        q.add(n)
    dist[source] = 0

    while q:
        u = min(q, key=lambda x: dist[x])
        q.remove(u)

        for neighbor in (n for n in graph.neighbors(u) if n in q):
            speed_limit = graph[u][neighbor]['speed_limit']
            alt = dist[u] + graph[u][neighbor]["length"] / (speed_limit if speed_limit else 25)
            if alt < dist[neighbor]:
                dist[neighbor] = alt
                prev[neighbor] = u
    return dist, prev

print(dijkstra(get_network(), 0)[0])





