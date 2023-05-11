import pandas as pd

from road_data import get_network

import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import colors, cm
import numpy as np
import logging
from logginghandlers import create_handler
import os
from typing import Any


__logger = logging.getLogger(__name__)
__logger.addHandler(create_handler(logging.INFO))
__logger.setLevel(logging.INFO)


if os.path.exists('../resources/SaltLakeCountyRoads.gpkg'):
    __logger.info('Geometry file detected. Loading...')
    __road_geometries = gpd.read_file('../resources/SaltLakeCountyRoads.gpkg')
else:
    __road_geometries = None


def save_image(graph: nx.DiGraph, path='road_network.pdf', attribute: str | None = None, with_labels=False):
    if attribute is None or __road_geometries is None:
        fig, ax = plt.subplots()
        if __road_geometries is None:
            pos = {index: (100*x, 100*y) for (index, x), y in zip(nx.get_node_attributes(graph, 'x').items(),
                                                                  nx.get_node_attributes(graph, 'y').values())}
            nx.draw_networkx_edges(graph, pos=pos, ax=ax, width=0.5, arrowsize=1)
            if with_labels:
                nx.draw_networkx_edge_labels(graph, pos=pos, edge_labels=nx.get_edge_attributes(graph, 'name'), ax=ax)
    else:
        fig: plt.Figure
        ax1: plt.Axes
        ax2: plt.Axes
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(100, 100))
        ax1.set_aspect('equal')
        ax2.set_aspect('equal')
        ax1.set_title(f'{attribute}: direction 1')
        ax2.set_title(f'{attribute}: direction 2')
        ax1.title.set_fontsize(100)
        ax2.title.set_fontsize(100)
        ax1_values: dict[int, Any] = {}
        ax2_values: dict[int, Any] = {}
        for graph_index, geometry_index in nx.get_edge_attributes(graph, 'geometry_index').items():
            value = graph[graph_index[0]][graph_index[1]][attribute]
            if geometry_index in ax1_values:
                ax2_values[geometry_index] = value
            else:
                ax1_values[geometry_index] = value
                ax2_values[geometry_index] = value
        __road_geometries.iloc[sorted(ax1_values.keys()), :].plot(ax=ax1, column=pd.Series(ax1_values).sort_index(), cmap='plasma')
        __road_geometries.iloc[sorted(ax2_values.keys()), :].plot(ax=ax2, column=pd.Series(ax2_values).sort_index(), cmap='plasma')

        values = nx.get_edge_attributes(graph, attribute).values()
        minimum, maximum = min(values), max(values)
        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=minimum, vmax=maximum), cmap='plasma'), ax=(ax1, ax2))
        for tick in cbar.ax.get_yticklabels():
            tick.set_fontsize(100)

    fig.savefig(path)


if __name__ == '__main__':
    save_image(get_network(), attribute='speed_limit', path='road_network.pdf')
