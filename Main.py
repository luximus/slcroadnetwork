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
Q = []
def dijkstra(get_graph(), source):
    for n in get_graph().nodes:
        dist[n] = float('inf')
        prev[n] = None
        Q.append(n)
    dist[source] = 0

    while Q.len()!=0:
        




