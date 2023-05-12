import networkx as nx

from road_data import get_network


def find_intersections(road_network: nx.DiGraph, roads: list[str]) -> list[int]:
    intersections = list(road_network.nodes)
    for road in roads:
        road_edges = [edge for *edge, attrs in road_network.edges(data=True) if attrs.get('name') == road]
        if not road_edges:
            raise KeyError(road)

        road_intersections = set()
        for edge in road_edges:
            road_intersections.update(edge)

        intersections = [intersection for intersection in intersections if intersection in road_intersections]

    return intersections


if __name__ == '__main__':
    net = get_network()
    inters = find_intersections(net, ['9400 S', '1700 E'])
    print(inters)
    for node in inters:
        print(net[node])
