import random
from itertools import combinations
import math

import networkx as nx
from tqdm import tqdm

from road_data import get_network


def efficiency(graph: nx.Graph, sample: int | None = 20) -> float:
    if sample is not None:
        samp = random.sample(list(graph.nodes), k=sample)
        total = 0
        for source, target in tqdm(combinations(samp, r=2), total=math.comb(sample, 2)):
            try:
                total += 1 / nx.shortest_path_length(graph, source=source, target=target, weight='traversal_time')
            except nx.NetworkXNoPath:
                pass
        return total / (sample * (sample - 1))
    else:
        return sum(1 / d for _, distances in
                   tqdm(nx.shortest_path_length(graph, weight='traversal_time'), total=len(graph)) for d
                   in distances.values() if d != 0)


if __name__ == '__main__':
    net = get_network()
    print(efficiency(net))
