import random
from itertools import combinations

import networkx as nx
import numpy as np
from tqdm import tqdm

from road_data import get_network


def relative_load_on_road(road_network: nx.Graph, road_name: str, sample_size=10) -> dict[tuple[int, int], float]:
    edges = [(start, end) for start, end, attrs in road_network.edges(data=True) if attrs.get('name') == road_name]
    betweenness = {}
    for edge in tqdm(edges, total=len(edges), desc=f'Finding edge betweenness centrality for {road_name}'):
        sample = random.sample(list(road_network.nodes), k=sample_size)

        total = 0
        for source, target in combinations(sample, r=2):
            total_paths = 0
            paths_thru_edge = 0
            try:
                for path in nx.all_shortest_paths(road_network, source=source, target=target, weight='traversal_time'):
                    if edge in [(start, end) for start, end in zip(path, path[1:])]:
                        paths_thru_edge += 1
                    total_paths += 1
                total += paths_thru_edge / total_paths
            except nx.NetworkXNoPath:
                pass

        betweenness[edge] = total / (sample_size * (sample_size - 1))
    return betweenness


if __name__ == '__main__':
    net = get_network()
    bb_i80 = relative_load_on_road(net, 'I-80 WB FWY')
    print(bb_i80)
    bb_1300s = relative_load_on_road(net, '1300 S')
    print(bb_1300s)
    bb_beacon = relative_load_on_road(net, 'BEACON DR')
    print(bb_beacon)
    print(f'Average load on I-80 westbound: {np.average(np.array(list(bb_i80.values())))}')
    print(f'Average load on 1300 S: {np.average(np.array(list(bb_1300s.values())))}')
    print(f'Average load on Beacon Drive: {np.average(np.array(list(bb_beacon.values())))}')
