from generator import create_sol
import evo
import fitness
import agents


def main():
    # create environment, add agents and objectives
    E = evo.Environment()

    E.add_fitness_criteria('competitiveness', fitness.competitiveness)
    E.add_fitness_criteria('population', fitness.population)

    E.add_agent('fix_undersupport', agents.fix_undersupport)
    E.add_agent('mutate', agents.mutate)
    E.add_agent('fix_unwilling', agents.fix_unwilling)
    E.add_agent('fix_unpreferred', agents.fix_unpreferred)
