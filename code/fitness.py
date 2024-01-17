import numpy as np
from collections import defaultdict
import generator as gen
import profile


# contiguous districts ? minimize number of sides to polygon
# for each cell, check the numbers around it in a 3x3 grid with x (the number) in the center.
# if you can draw a length 3 line through x where all numbers are x, it's fine. if not, add 1 to the
# number of sides.

@profile
def contiguity(sol):
    



def district_demographics(bool_arr, sol):
    dct = {'dem': 0, 'rep': 0, 'oth': 0, 'total': 0}
    for party in dct:
        dct[party] = np.nansum(sol[party][bool_arr].astype(float))
    return dct


# competitiveness -- compare if majority in each district won to total voting demographics of state?
@profile
def competitiveness(sol):
    # get districts not including empty space
    dists = np.unique(sol['map'])
    # dists = np.delete(dists, np.argwhere(dists == -1))
    majs = defaultdict(int)

    # get majority in each district
    for dist in dists:
        if dist == -1:
            continue
        bool_arr = (sol['map'] == dist).astype(bool)
        dem = district_demographics(bool_arr, sol)
        dem.pop('total')
        # print(dem)
        max_dem = list(dem.keys())[list(dem.values()).index(max(list(dem.values())))]
        majs[max_dem] += 1

    # get "fair" statewide distribution
    bool_arr = sol['map'] != -1
    dem = district_demographics(bool_arr, sol)
    dem.pop('total')
    total = sum(dem.values())
    dem = {k: round(v / total * 26) for k, v in dem.items()}

    score = 0
    # compare two distributions, score
    for key in dem:
        if key in majs.keys():
            score += abs(majs[key] - dem[key])
        else:
            score += dem[key]

    score /= len(dists) - 1

    return score


# population balance (each district should have apprx. equal population size)
@profile
def population(sol):
    # get districts not including empty space
    dists = np.unique(sol['map'])
    dists = np.delete(dists, np.argwhere(dists == -1))
    pops = list()

    # get population of each district and append to array
    for dist in dists:
        bool_arr = sol['map'] == dist
        pop = sol['pop'][bool_arr].sum()
        pops.append(pop)

    return np.var(pops)


solution = gen.create_sol()
gen.plot_array(solution['map'])
