import random

import geopandas as gpd
import networkx as nx
import pandas as pd
import shapely as shp
from shapely.ops import linemerge
import numpy as np
from tqdm import tqdm

from pathlib import Path
import logging
from logginghandlers import create_handler
import os

__logger = logging.getLogger(__name__)
__logger.addHandler(create_handler(logging.INFO))
__logger.setLevel(logging.INFO)


def create_network_file() -> Path:
    def get_start_and_end_points(geom: shp.LineString) -> tuple[tuple[int, int], tuple[int, int]]:
        start, *_, end = geom.coords
        return (round(start[0], 3), round(start[1], 3)), (round(end[0], 3), round(end[1], 3))

    # def calculate_capacity(row: gpd.GeoSeries) -> float:
    #     functional_system = row.f_system
    #     if (functional_system == 1 or functional_system == 2) and row.access_control == 1:  # Freeways
    #         free_flow_speed = 75.4 - row.lane_width - row.shoulder_width_r
    #         return (2_200 + 10 * (min(70, free_flow_speed) - 50)) / (
    #                     1 + row.truck * ((row.aadt_single_unit + row.aadt_combination) / row.aadt))
    #     elif functional_system == 3 or functional_system == 4:  # Arterials
    #         return 0.4 * row.peak_lanes * 1_900  # Assume percent green time is 40%
    #     elif functional_system == 5 or functional_system == 6:  # Collectors
    #         return 1_200 if row.peak_lanes == 1 else 1_500
    #     else:  # All other types of roads
    #         return 1_490

    if os.path.isfile('../resources/SaltLakeCountyRoadNetwork.xml.gz'):
        __logger.info('Road network already created.')
        return Path('../resources/SaltLakeCountyRoadNetwork.xml.gz')

    slcounty_boundary = None  # type: ignore
    if os.path.isfile('../resources/SaltLakeCountyRoads.geojson'):
        __logger.info('Loading Salt Lake County road data...')
        slc_road_gdf = gpd.read_file('../resources/SaltLakeCountyRoads.geojson')
    else:
        __logger.info('Loading Salt Lake County boundary...')
        county_boundaries = gpd.read_file('../resources/Utah_County_Boundaries/Utah_County_Boundaries.shp')
        slcounty_boundary: gpd.GeoSeries = county_boundaries.loc[county_boundaries['NAME'] == 'SALT LAKE', 'geometry']

        __logger.info('Loading state-wide road network data from Transportation.Roads...')
        slc_road_gdf = gpd.read_file('../resources/Utah_Roads.gdb', mask=slcounty_boundary)

        __logger.info('Removing unnecessary columns...')
        slc_road_gdf: gpd.GeoDataFrame = slc_road_gdf.loc[:, ['DOT_RTNAME', 'FULLNAME', 'ONEWAY', 'SPEED_LMT',
                                                              'DOT_AADT', 'geometry']]
        # slc_road_gdf = slc_road_gdf.merge(slc_highway_gdf, how='left', left_on=['DOT_RTNAME', 'DOT_F_MILE', 'DOT_T_MILE'],  # type: ignore
        #                                   right_on=['route_id', 'begin_point', 'end_point'])
        # slc_road_gdf.drop(columns=['DOT_RTNAME', 'route_id'], inplace=True)
        # slc_road_gdf.reset_index(drop=True, inplace=True)

        __logger.info('Merging multi-line strings...')
        slc_road_gdf.loc[:, 'geometry'] = slc_road_gdf.geometry.apply(linemerge)
        slc_road_gdf.rename(columns={
            'DOT_RTNAME': 'route_id',
            'FULLNAME': 'name',
            'ONEWAY': 'one_way',
            'SPEED_LMT': 'speed_limit',
            'DOT_AADT': 'aadt_2022',
        }, inplace=True)

        __logger.info('Cleaning data...')
        slc_road_gdf = slc_road_gdf.astype({
            'name': 'str',
            'one_way': 'category',
            'speed_limit': 'uint32',
            'aadt_2022': 'float'
        })

        __logger.info('Estimating true road length...')
        slc_road_gdf['length'] = slc_road_gdf.to_crs(('esri', 102005)).geometry.apply(lambda geom: geom.length)

        __logger.info('Saving filtered data...')
        slc_road_gdf.to_file('../resources/SaltLakeCountyRoads.geojson', driver='GeoJSON')

    if os.path.isfile('../resources/SaltLakeCountyHighways.geojson'):
        __logger.info('Loading Salt Lake County highway data...')
        slc_highway_gdf = gpd.read_file('../resources/SaltLakeCountyHighways.geojson')
    else:
        if slcounty_boundary is None:
            __logger.info('Loading Salt Lake County boundary...')
            county_boundaries = gpd.read_file('../resources/Utah_County_Boundaries/Utah_County_Boundaries.shp')
            slcounty_boundary: gpd.GeoSeries = county_boundaries.loc[county_boundaries['NAME'] == 'SALT LAKE', 'geometry']

        __logger.info('Loading national road network data from HPMS...')
        slc_highway_gdf = gpd.read_file('../resources/HPMS2016.gdb', mask=slcounty_boundary)

        __logger.info('Removing unnecessary columns...')
        slc_highway_gdf: gpd.GeoDataFrame = slc_highway_gdf.loc[:, ['route_id', 'begin_point', 'end_point', 'f_system',
                                                                    'urban_code', 'access_control', 'through_lanes',
                                                                    'peak_lanes', 'counter_peak_lanes', 'aadt',
                                                                    'aadt_single_unit', 'pct_peak_single',
                                                                    'aadt_combination', 'pct_peak_combination',
                                                                    'k_factor', 'dir_factor', 'lane_width',
                                                                    'median_type', 'shoulder_width_r', 'truck']]

        __logger.info('Merging multi-line strings...')
        slc_highway_gdf.loc[: 'geometry'] = slc_highway_gdf.geometry.apply(linemerge)
        slc_highway_gdf.rename(columns={
            'aadt': 'aadt_2016',
            'f_system': 'functional_system',
            'truck': 'in_truck_network'
        })

        __logger.info('Cleaning data...')
        slc_highway_gdf.loc[:, 'is_rural'] = False
        slc_highway_gdf.loc[pd.to_numeric(slc_highway_gdf['urban_code'], downcast='unsigned') == 99_999, 'is_rural'] = True
        slc_highway_gdf.drop(columns='urban_code', inplace=True)
        # slc_road_gdf.loc[slc_road_gdf['through_lanes'].isna() & slc_road_gdf['one_way'].apply(int) == 0, 'through_lanes'] = 2
        # slc_road_gdf.loc[slc_road_gdf['through_lanes'].isna() & slc_road_gdf['one_way'].apply(int) != 0, 'through_lanes'] = 1
        slc_highway_gdf.loc[pd.to_numeric(slc_highway_gdf['lane_width'], downcast='unsigned') == 0] = 12
        slc_highway_gdf.fillna({
            'functional_system': 7,
            'access_control': 2,
            'peak_lanes': 1,
            'lane_width': 12,
            'k_factor': pd.to_numeric(slc_highway_gdf['k_factor']).mean(),
            'median_type': 1,
            'in_truck_network': False,
        }, inplace=True)
        slc_highway_gdf = slc_highway_gdf.astype({
            'aadt_2016': 'float',
            'aadt_single_unit': 'float',
            'aadt_combination': 'float',
            'functional_system': 'category',
            'access_control': 'category',
            'through_lanes': 'uint8',
            'peak_lanes': 'uint8',
            'counter_peak_lanes': 'uint8',
            'pct_peak_single': 'float',
            'pct_peak_combination': 'float',
            'k_factor': 'uint32',
            'dir_factor': 'uint32',
            'lane_width': 'uint32',
            'median_type': 'category',
            'in_truck_network': 'bool'
        })

        __logger.info('Saving filtered data...')
        slc_highway_gdf.to_file('resources/SaltLakeCountyHighways.geojson', driver='GeoJSON')

    road_network = nx.DiGraph()
    one_way_status = slc_road_gdf.one_way
    two_way_roads_without_thru_lane_data: list[tuple[tuple[float, float], tuple[float, float], pd.Series]] = []
    odd_two_way_roads_without_thru_lane_data_or_peak_lane_data: list[tuple[tuple[float, float], tuple[float, float], pd.Series]] = []
    default_fields = ['name', 'speed_limit', 'length', 'median_type', 'lane_width', 'shoulder_width_r',
                      'pct_peak_single', 'pct_peak_combination', 'in_truck_network', 'access_control', 'is_rural']
    aadt_types = ['aadt_2022', 'aadt_2016', 'aadt_single_unit', 'aadt_combination']
    data: pd.Series
    for (start, end), (index, data) in tqdm(
            zip(slc_road_gdf.geometry.apply(get_start_and_end_points), slc_road_gdf.iterrows()),
            total=len(slc_road_gdf),
            desc='Creating Salt Lake County road network...'):
        one_way = one_way_status[index]
        if one_way == 0:  # Two-way
            road_network.add_edge(start, end, **data[default_fields].to_dict(), geometry_index=index)
            road_network.add_edge(end, start, **data[default_fields].to_dict(), geometry_index=index)
            if data.peak_lanes != 0 and data.counter_peak_lanes != 0:
                two_way_roads_without_thru_lane_data.append((start, end, data))
            else:
                if data.through_lanes % 2 != 0:
                    odd_two_way_roads_without_thru_lane_data_or_peak_lane_data.append((start, end, data))
                else:
                    road_network[start][end]['through_lanes'] = data.through_lanes // 2
                    road_network[end][start]['through_lanes'] = data.through_lanes // 2
                    road_network[start][end]['aadt_2022'] = data.aadt_2022 // 2
                    road_network[end][start]['aadt_2022'] = data.aadt_2022 // 2
                    road_network[start][end]['aadt_2016'] = data.aadt_2016 // 2
                    road_network[end][start]['aadt_2016'] = data.aadt_2016 // 2

        elif one_way == 1:  # One-way from start to end
            road_network.add_edge(start, end,
                                  **data[default_fields + ['through_lanes'] + aadt_types].to_dict(),
                                  geometry_index=index)
        elif one_way == 2:  # One-way from end to start
            road_network.add_edge(end, start,
                                  **data[default_fields + ['through_lanes'] + aadt_types].to_dict(),
                                  geometry_index=index)

    __logger.info('Eliminating disconnected components...')
    road_network: nx.DiGraph = nx.subgraph(road_network, max(nx.weakly_connected_components(road_network), key=len))

    __logger.info('Finishing through-lane and AADT calculations...')
    betweenness = nx.edge_betweenness_centrality(road_network, weight='length', normalized=False)  # It's important to use the networkx function because of its faster implementation.

    for start, end, data in (road for road in two_way_roads_without_thru_lane_data if road in road_network.edges):
        (peak_start, peak_end), (non_peak_start, non_peak_end) = sorted([(start, end), (end, start)],
                                                                        key=lambda edge: betweenness[edge],
                                                                        reverse=True)
        road_network[peak_start][peak_end]['through_lanes'] = data.peak_lanes
        road_network[non_peak_start][non_peak_end]['through_lanes'] = data.peak_lanes

        if not np.isnan(data.k_factor) and not np.isnan(data.dir_factor):
            peak_traffic_factor = (data.k_factor / 100) * (data.dir_factor / 100) * 24
            non_peak_traffic_factor = ((100 - data.k_factor) / 100) * (data.dir_factor / 100) * 24
        else:
            peak_traffic_factor = betweenness[(peak_start, peak_end)] / (betweenness[(peak_start, peak_end)] + betweenness[(non_peak_start, non_peak_end)])
            non_peak_traffic_factor = 1 - peak_traffic_factor
        for aadt_type in aadt_types:
            if not np.isnan(data[aadt_type]):
                road_network[peak_start][peak_end][aadt_type] = int(peak_traffic_factor * data[aadt_type])
                road_network[non_peak_start][non_peak_end][aadt_type] = int(non_peak_traffic_factor * data[aadt_type])
            else:
                road_network[peak_start][peak_end][aadt_type] = np.nan

    for start, end, data in (road for road in odd_two_way_roads_without_thru_lane_data_or_peak_lane_data if road in road_network.edges):
        (peak_start, peak_end), (non_peak_start, non_peak_end) = sorted([(start, end), (end, start)],
                                                                        key=lambda edge: betweenness[edge],
                                                                        reverse=True)
        road_network[peak_start][peak_end]['through_lanes'] = data.through_lanes // 2 + 1
        road_network[non_peak_start][non_peak_end]['through_lanes'] = data.through_lanes // 2

        if not np.isnan(data.k_factor) and not np.isnan(data.dir_factor):
            peak_traffic_factor = (data.k_factor / 100) * (data.dir_factor / 100) * 24
            non_peak_traffic_factor = ((100 - data.k_factor) / 100) * (data.dir_factor / 100) * 24
        else:
            peak_traffic_factor = betweenness[(peak_start, peak_end)] / (betweenness[(peak_start, peak_end)] + betweenness[(non_peak_start, non_peak_end)])
            non_peak_traffic_factor = 1 - peak_traffic_factor
        for aadt_type in aadt_types:
            if not np.isnan(data[aadt_type]):
                road_network[peak_start][peak_end][aadt_type] = int(peak_traffic_factor * data[aadt_type])
                road_network[non_peak_start][non_peak_end][aadt_type] = int(non_peak_traffic_factor * data[aadt_type])
            else:
                road_network[peak_start][peak_end][aadt_type] = np.nan

    __logger.info('Getting intersection points...')
    slc_road_gdf = slc_road_gdf.loc[sorted(set(nx.get_edge_attributes(road_network, 'geometry_index').values()))]
    points = [pt.coords[0] for pt in gpd.GeoSeries([shp.Point(x, y) for x, y in sorted(road_network.nodes())],
                                                   crs=slc_road_gdf.crs).to_crs(epsg=4326)]

    __logger.info('Entering intersection location data...')
    road_network = nx.convert_node_labels_to_integers(road_network, ordering='sorted')
    nx.set_node_attributes(road_network, {index: pt[0]
                                          for index, pt in tqdm(enumerate(points), desc='x')}, 'x')
    nx.set_node_attributes(road_network, {index: pt[1]
                                          for index, pt in tqdm(enumerate(points), desc='y')}, 'y')

    __logger.info('Saving road network to file SaltLakeCountyRoadNetwork.xml.gz...')
    nx.write_graphml(road_network, '../resources/SaltLakeCountyRoadNetwork.xml.gz')

    if not os.path.isfile('../resources/SaltLakeCountyRoadData.csv.zip'):
        slc_road_df = pd.DataFrame(slc_road_gdf.drop(columns=['one_way', 'geometry']))
        __logger.info('Saving road data to SaltLakeCountyRoadData.csv.zip...')
        slc_road_df.to_csv('../resources/SaltLakeCountyRoadData.csv.zip')

    return Path('../resources/SaltLakeCountyRoadNetwork.xml.gz'), Path('../resources/SaltLakeCountyRoadData.csv.zip')


if __name__ == '__main__':
    print(create_network_file())


# urbanized areas: 50959, 64945, 72559, 78499, 99998
