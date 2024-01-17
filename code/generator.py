import numpy as np
import pandas as pd
import geopandas as gpd
import warnings
from shapely.geometry import Point
import matplotlib.pyplot as plt
import sys

np.set_printoptions(threshold=sys.maxsize)
pd.set_option('display.max_rows', None)

warnings.simplefilter(action='ignore', category=FutureWarning)
POPULATION_PATH = '../data/ny_population.xlsx'
REGISTRATION_PATH = '../data/ny_registration.xlsx'
COUNTIES_PATH = '../data/new-york-counties.geojson'


def clean_df():
    """
    Create cleaned geopandas DataFrame.

    Returns
    -------
    gdf : GeoDataFrame
        A merged dataframe with population data, registration data, and geographic data.
    """
    # merge dataframes
    population = pd.read_excel(POPULATION_PATH).sort_values('county')
    registration = pd.read_excel(REGISTRATION_PATH).sort_values('county')
    demographics = pd.merge(population, registration, on='county')
    geo_df = gpd.read_file(COUNTIES_PATH).sort_values('name')
    gdf = pd.merge(demographics, geo_df, left_on='county', right_on='name', how='inner')

    # convert to geodataframe and clean columns
    gdf = gpd.GeoDataFrame(gdf, geometry=gdf.geometry)
    gdf = gdf.drop(columns=['name'])
    cols = list(gdf.columns)
    cols.pop(cols.index('county'))
    cols.insert(0, 'county')
    gdf = gdf[cols]
    gdf.reset_index(drop=True, inplace=True)
    gdf.index.rename('id', inplace=True)
    gdf.population = gdf.population.replace(',', '', regex=True)
    gdf = gdf.apply(pd.to_numeric, errors='ignore')

    return gdf


def state_bounds(gdf):
    """
    Get coordinate boundaries of a given state.

    Parameters
    ----------
    gdf : GeoDataFrame
        A dataframe containing geospatial data in the 'geometry' column

    Returns
    -------
    lst : list
        A nested list of our boundaries, in the format [[minx, maxx], [miny, maxy]]
    """

    # get state bounds
    bound_df = gdf.geometry.bounds
    minx = bound_df.minx.min()
    miny = bound_df.miny.min()
    maxx = bound_df.maxx.max()
    maxy = bound_df.maxy.max()

    # add 5% gap both sides
    xrange = maxx - minx
    minx -= (xrange / 20)
    maxx += (xrange / 20)
    yrange = maxy - miny
    miny -= (yrange / 20)
    maxy += (yrange / 20)
    return [[minx, maxx], [miny, maxy]]


def np_coords(bounds, width=120, height=100):
    """
    Creates numpy array where each point corresponds to a lat/long coordinate.

    Parameters
    ----------
    bounds : nested lst
        A list of our lat and long bounds (x is long y is lat), in the format of [[minx, maxx], [miny, maxy]]
    width : int
        The number of cols in the desired NumPy array
    height : int
        The number of rows in the desired NumPy array

    Returns
    -------
    arr : NumPy array
        An array of specified width and height where each point corresponds to a lat/long coordinate (in
        format of (long, lat) because of Shapely coordinate system)
    """

    # get data from bounds
    xrange = bounds[0][1] - bounds[0][0]
    yrange = bounds[1][1] - bounds[1][0]
    xmin = bounds[0][0]
    ymax = bounds[1][1]

    # difference between each np cell
    xdiff = xrange / (width - 1)
    ydiff = yrange / (height - 1)

    # initialize empty array
    arr = np.empty((height, width), dtype=object)
    for iy, ix in np.ndindex(arr.shape):
        arr[iy, ix] = Point((xmin + (xdiff * ix), ymax - (ydiff * iy)))

    return arr


def check_county(x, counties):
    """
    Given a point z, checks which county z is in and returns that point.
    """
    for idx, county in enumerate(counties):
        if county.contains(x):
            return idx
    return -1


def coords_to_counties(gdf, arr):
    counties = list(gdf.geometry.values)

    # get_county = lambda row: np.argmin([county.contains(x) for county in counties])
    dist_arr = np.empty_like(arr)

    # multipolygon has (long, lat) instead of (lat, long), so flip coord pair before checking
    for iy, ix in np.ndindex(arr.shape):
        dist_arr[iy, ix] = check_county(arr[iy, ix], counties)

    return dist_arr


def get_neighbors(gdf):
    """
    Get a dictionary of all counties and their neighbors

    Parameters
    ----------
    gdf : GeoDataFrame
        A geopandas dataframe with geographic data.

    Returns
    -------
    neighbors_dct : dict
        A dictionary where keys are counties and values are neighboring counties
    """

    neighbors_dct = {}
    for index, county in gdf.iterrows():
        # get 'not disjoint' counties
        neighbors = gdf[~gdf.geometry.disjoint(county.geometry)]['county'].tolist()

        # remove own county name
        neighbors = [name for name in neighbors if county['county'] != name]

        # add to dict
        neighbors_dct[county['county']] = neighbors

    return neighbors_dct


def numpy_dems(county_arr, gdf):
    # get total population for each county, divide by number of squares
    ids = list(gdf.index)
    pop = np.empty_like(county_arr, dtype=float)
    dems = np.empty_like(county_arr, dtype=float)
    reps = np.empty_like(county_arr, dtype=float)
    oth = np.empty_like(county_arr, dtype=float)
    totals = np.empty_like(county_arr, dtype=float)

    for id in ids:
        county_series = gdf.loc[gdf.index == id]
        county = np.where(county_arr == id)
        num_squares = len(county[0])
        pop_square = county_series.population.values[0] / num_squares

        num_dems = county_series.dem.values[0]
        num_reps = county_series.rep.values[0]
        num_oth = county_series.oth.values[0]
        num_total = county_series.total.values[0]

        pop[county] = pop_square
        dems[county] = num_dems
        reps[county] = num_reps
        oth[county] = num_oth
        totals[county] = num_total

    return pop, dems, reps, oth, totals


def generate_sol(county_arr, neighbors, num_dists):
    # initialize district counter and final array
    dist = 0
    dist_arr = -np.ones_like(county_arr, dtype=float)

    # create assignment df
    df = pd.DataFrame()
    df['county'] = list(neighbors.keys())
    df['assigned'] = -1
    df.index.rename('id', inplace=True)

    # until we have n districts
    while dist < num_dists:
        # randomly select a county that hasn't been assigned, convert all neighbors to district
        county = df.loc[df.assigned == -1].sample().index.values[0]
        change_arr = np.where(county_arr == county)

        # update assignments in df (for temp purposes)
        df.loc[df.index == county, 'assigned'] = dist
        dist_arr[change_arr] = dist
        dist += 1

    # randomly expand existing districts until every county is assigned
    while not df.loc[df.assigned == -1].empty:
        # select county
        county = df.loc[df.assigned != -1].sample()
        county_dist = county.assigned.values[0]
        county = county.county.values[0]
        cnt_neighbors = neighbors[county]

        # find unassigned neighbors
        swaps = []
        for nghb in cnt_neighbors:
            if df.loc[df.county == nghb].assigned.values[0] == -1:
                swaps.append(df.loc[df.county == nghb].index.values[0])

        # modify dataframe and district array
        change_arr = np.unravel_index(np.where(
            df.loc[df.index.isin(swaps)].index.values[:, None] == county_arr.ravel())[1],
                                      county_arr.shape)
        df.loc[swaps, 'assigned'] = county_dist
        dist_arr[change_arr] = county_dist

    return dist_arr


def plot_array(arr):
    plt.imshow(np.float64(arr), interpolation='nearest')
    plt.tick_params(left=False, right=False, labelleft=False,
                    labelbottom=False, bottom=False)
    plt.show()


def create_sol(width=180, height=150):
    # get geodataframe, generate numpy array of counties
    gdf = clean_df()
    neighbors = get_neighbors(gdf)
    bounds = state_bounds(gdf)
    coords = np_coords(bounds, width=width, height=height)
    counties = coords_to_counties(gdf, coords)

    # generate initial solution
    init_sol = generate_sol(counties, neighbors, 26)
    pop, dems, reps, oth, totals = numpy_dems(counties, gdf)

    return {'map': init_sol, 'counties': counties, 'pop': pop, 'dem': dems, 'rep': reps, 'oth': oth, 'total': totals}
