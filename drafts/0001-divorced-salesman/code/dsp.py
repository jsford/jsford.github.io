#!/usr/bin/env python3

import numpy as np
from python_tsp.exact import solve_tsp_dynamic_programming

def solve_tsp(costs):
    tour, cost = solve_tsp_dynamic_programming(costs)
    return tour, cost

def solve_dsp(costs, start_city):
    costs = np.array(costs).astype(float)

    N = costs.shape[0]

    # The ghost city is always at index zero.
    ghost_city = 0

    # Add one to the start_city so we can index into the augmented cost matrix.
    aug_start_city = start_city + 1

    min_tour = None
    min_cost = np.Infinity

    for end_city in range(0, N+1):
        if end_city == ghost_city or end_city == aug_start_city:
            continue

        # Construct an augmented costs matrix with a ghost city at index zero.
        augcosts = costs
        augcosts = np.insert(augcosts, ghost_city, np.Infinity, axis=0)
        augcosts = np.insert(augcosts, ghost_city, np.Infinity, axis=1)

        augcosts[ghost_city, ghost_city] = 0 # Free to go from the ghost to the ghost.

        augcosts[ghost_city, aug_start_city] = 0 # Free to go from the ghost to the start.
        augcosts[aug_start_city, ghost_city] = 0 # Free to go from the ghost to the start.

        augcosts[ghost_city, end_city] = 0 # Free to go from the end to the ghost.
        augcosts[end_city, ghost_city] = 0 # Free to go from the end to the ghost.

        tour, cost = solve_tsp(augcosts)

        print(aug_start_city, end_city)
        print(augcosts)
        print(tour, cost)
        print()
        print()

        if cost < min_cost:
            min_tour = tour
            min_cost = cost

    # Remove the ghost city from the tour.
    min_tour = min_tour[1:]

    # Subtract one from the tour indices to index into the original cost matrix.
    min_tour = [i-1 for i in min_tour]

    # If the start_city is not first, reverse the tour.
    if( min_tour[0] != start_city ):
        min_tour.reverse()

    return min_tour, min_cost

def plot_tour(costs, tour):
    pass

if __name__=='__main__':

    costs = np.array([[ 0, 5, 4, 10],
                      [ 5, 0, 8,  5],
                      [ 4, 8, 0,  3],
                      [10, 5, 3,  0]])

    tour, cost = solve_dsp(costs, 0)
    print(tour, cost)


