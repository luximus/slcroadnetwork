import logging
import os

import geopandas as gpd
import networkx as nx
import pandas as pd
import shapely as shp
from shapely.ops import linemerge
from tqdm import tqdm

from logginghandlers import create_handler

__logger = logging.getLogger(__name__)
__logger.addHandler(create_handler(logging.INFO))
__logger.setLevel(logging.INFO)


def get_network() -> nx.DiGraph:
    def get_start_and_end_points(geom: shp.LineString) -> tuple[tuple[int, int], tuple[int, int]]:
        start, *_, end = geom.coords
        return (round(start[0], 5), round(start[1], 5)), (round(end[0], 5), round(end[1], 5))

    def meters_to_miles(measure_meters: float) -> float:
        return measure_meters * 100 / 2.54 / 12 / 5280

    if os.path.isfile('../resources/SaltLakeCountyRoadNetwork.xml.gz'):
        __logger.info('Road network already created.')
        road_network = nx.read_graphml('../resources/SaltLakeCountyRoadNetwork.xml.gz')
        nx.relabel_nodes(road_network, int, copy=False)  # type: ignore
        return road_network

    if os.path.isfile('../resources/SaltLakeCountyRoads.geojson'):
        __logger.info('Loading Salt Lake County road data...')
        slc_road_gdf = gpd.read_file('../resources/SaltLakeCountyRoads.geojson')
    else:
        if not os.path.isfile('../resources/Utah_County_Boundaries/Utah_County_Boundaries.shp'):
            raise FileNotFoundError('The Utah county boundaries cannot be found.')
        if not os.path.isdir('../resources/UtahRoadsNetworkAnalysis.gdb'):
            raise FileNotFoundError('The Utah roads database cannot be found.')

        __logger.info('Loading Salt Lake County boundary...')
        county_boundaries = gpd.read_file('../resources/Utah_County_Boundaries/Utah_County_Boundaries.shp')
        slcounty_boundary: gpd.GeoSeries = county_boundaries.loc[county_boundaries['NAME'] == 'SALT LAKE', 'geometry']

        __logger.info('Loading state-wide road network data from Street Network Analysis...')
        slc_road_gdf = gpd.read_file('../resources/UtahRoadsNetworkAnalysis.gdb', mask=slcounty_boundary, layer=0)

        __logger.info('Removing unnecessary columns...')
        slc_road_gdf: gpd.GeoDataFrame = slc_road_gdf.loc[:, ['FULLNAME', 'ONEWAY', 'SPEED_LMT', 'F_T_IMP_MIN',
                                                              'T_F_IMP_MIN', 'geometry']]

        __logger.info('Merging multi-line strings...')
        slc_road_gdf.loc[:, 'geometry'] = slc_road_gdf.geometry.apply(linemerge)
        slc_road_gdf.rename(columns={
            'FULLNAME': 'name',
            'ONEWAY': 'one_way',
            'SPEED_LMT': 'speed_limit',
            'F_T_IMP_MIN': 'traversal_time_l',
            'T_F_IMP_MIN': 'traversal_time_r'
        }, inplace=True)

        __logger.info('Cleaning data...')
        slc_road_gdf = slc_road_gdf.astype({
            'name': 'str',
            'one_way': 'uint8',
            'speed_limit': 'uint32',
            'traversal_time_l': 'float',
            'traversal_time_r': 'float'
        })
        slc_road_gdf.loc[slc_road_gdf['speed_limit'] == 0, 'speed_limit'] = 20

        __logger.info('Estimating true road length...')
        # The logic behind this is fairly complex. ESRI:102005 is a coordinate reference system where the Euclidean
        # distance between objects is approximately equal to the real distance. `to_crs` reprojects all the coordinates
        # to this "equidistant" coordinate system, which then allows us to just use the `length` property to determine
        # the length. The length is in meters, so it must be converted to miles.
        slc_road_gdf['length'] = slc_road_gdf.to_crs(('esri', 102005)).geometry.apply(lambda geom: meters_to_miles(geom.length))

        __logger.info('Saving filtered data...')
        slc_road_gdf.to_file('../resources/SaltLakeCountyRoads.geojson', driver='GeoJSON')

    if not os.path.isfile('../resources/SaltLakeCountyRoads.gpkg'):
        __logger.info('Saving geometry to file...')
        slc_road_gdf.geometry.to_file('../resources/SaltLakeCountyRoads.gpkg', driver='GPKG')

    road_network = nx.DiGraph()
    one_way_status = slc_road_gdf.one_way
    traversal_time_l = slc_road_gdf.traversal_time_l
    traversal_time_r = slc_road_gdf.traversal_time_r
    data: pd.Series
    for (start, end), (index, data) in tqdm(
            zip(slc_road_gdf.geometry.apply(get_start_and_end_points), slc_road_gdf.drop(columns=['one_way', 'traversal_time_l', 'traversal_time_r', 'geometry']).iterrows()),
            total=len(slc_road_gdf),
            desc='Creating Salt Lake County road network...'):
        if start == end:
            continue
        one_way = one_way_status[index]
        attrs = data.to_dict() | {'geometry_index': index}
        if one_way == 0:  # Two-way
            road_network.add_edge(start, end, **attrs, traversal_time=traversal_time_l[index])
            road_network.add_edge(end, start, **attrs, traversal_time=traversal_time_r[index])
        elif one_way == 1:  # One-way from start to end
            road_network.add_edge(start, end, **attrs, traversal_time=traversal_time_l[index])
        elif one_way == 2:  # One-way from end to start
            road_network.add_edge(end, start, **attrs, traversal_time=traversal_time_r[index])

    __logger.info('Eliminating disconnected components...')
    road_network: nx.DiGraph = nx.subgraph(road_network, max(nx.weakly_connected_components(road_network), key=len))

    __logger.info('Getting intersection points...')
    points = [pt.coords[0] for pt in gpd.GeoSeries([shp.Point(x, y) for x, y in sorted(road_network.nodes())],
                                                   crs=slc_road_gdf.crs).to_crs(epsg=4326)]

    __logger.info('Entering intersection location data...')
    road_network = nx.convert_node_labels_to_integers(road_network, ordering='sorted')
    nx.set_node_attributes(road_network, {index: pt[0]
                                          for index, pt in tqdm(enumerate(points), total=len(points), desc='x')}, 'x')
    nx.set_node_attributes(road_network, {index: pt[1]
                                          for index, pt in tqdm(enumerate(points), total=len(points), desc='y')}, 'y')

    __logger.info('Saving road network to file SaltLakeCountyRoadNetwork.xml.gz...')
    nx.write_graphml(road_network, '../resources/SaltLakeCountyRoadNetwork.xml.gz')

    return road_network


if __name__ == '__main__':
    net = get_network()
    print(net)
