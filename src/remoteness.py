import networkx as nx
from road_data import get_network
from tqdm import tqdm
import numpy as np
from search import find_intersections


def remoteness(graph: nx.Graph, source: int) -> float:
    """
    Finds the average minimum distance of one node to every other node in the graph.

    :param graph: The graph to search.
    :param source: The source node.
    :return: A measure of how far away the node is in temporal distance from the others, which is determined by the
    average minimum distance from the node to all other nodes.
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

    pbar = tqdm(total=len(q))
    while q:
        u = min(q, key=lambda x: dist[x])
        q.remove(u)

        for neighbor in (n for n in graph.neighbors(u) if n in q):
            alt = dist[u] + graph[u][neighbor]["traversal_time"]
            if alt < dist[neighbor]:
                dist[neighbor] = alt
                prev[neighbor] = u
        pbar.update()
    pbar.close()
    return np.average(np.array([x for x in dist.values() if not np.isinf(x)]))


if __name__ == "__main__":
    net = get_network()
    print(remoteness(net, find_intersections(net, ["STATE ST", "1700 S"])[0]))
