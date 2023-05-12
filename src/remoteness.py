import networkx as nx
import matplotlib.pyplot as plt
import random
from road_data import get_network
from tqdm import tqdm
import numpy as np

def remoteness(graph, source):
    """
    Finds the average minimum distance of one node to every other node in the graph.
    """
    dist = {}
    prev = {}
    q = set()
    for n in graph.nodes:
        dist[n] = float('inf')
        prev[n] = None
        q.add(n)
    if source not in dist:
        raise KeyError(source)
    dist[source] = 0

    while q:
        u = min(q, key=lambda x: dist[x])
        q.remove(u)

        for neighbor in (n for n in graph.neighbors(u) if n in q):
            alt = dist[u] + graph[u][neighbor]["traversal_time"]
            if alt < dist[neighbor]:
                dist[neighbor] = alt
                prev[neighbor] = u
    return np.average(np.array(list(dist.values())))


if __name__ == "__main__":
    print(remoteness(get_network(), 2)[0])
