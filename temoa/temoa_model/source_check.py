"""
This module is used to verify that all demand commodities are traceable back to designated
source technologies
"""
from collections import defaultdict
from itertools import chain
from logging import getLogger

from temoa.temoa_model.temoa_model import TemoaModel

"""
Tools for Energy Model Optimization and Analysis (Temoa):
An open source framework for energy systems optimization modeling

Copyright (C) 2015,  NC State University

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

A complete copy of the GNU General Public License v2 (GPLv2) is available
in LICENSE.txt.  Users uncompressing this from an archive may not have
received this license file.  If not, see <http://www.gnu.org/licenses/>.


Written by:  J. F. Hyink
jeff@westernspark.us
https://westernspark.us
Created on:  2/3/24

"""

logger = getLogger(__name__)


class CommodityNetwork:
    """
    class to hold the data and the network for a particular region/period
    """

    def __init__(self, region, period: int, M: TemoaModel):
        # check the marking of source commodities first, as the db may not be configured for source check...
        self.source_commodities: set[str] = set(M.commodity_source)
        if not self.source_commodities:
            logger.error(
                'No source commodities discovered when initializing CommodityNetwork.  Have source commodities been identified in commodities '
                "table with 's'?"
            )
            raise ValueError(
                'Attempted to do source trace with no source commodities marked.  Have source commodities been identified in commodities '
                "table with 's'?"
            )
        self.bad_connections: set[tuple] | None = None
        self.good_connections: set[tuple] | None = None
        self.M = M
        self.region = region
        self.period = period
        # the cataloguing of inputs/outputs by tech is needed for implicit links like via emissions in LinkedTech
        self.tech_inputs: dict[str, set[str]] | None = defaultdict(set)
        self.tech_outputs: dict[str, set[str]] | None = defaultdict(set)
        # {output comm: {input comm, tech} that source it}
        self.connections: dict[str, set[tuple]] = defaultdict(set)
        self.demand_commodities: set[str] = {
            d for (r, p, d) in M.Demand if r == self.region and p == self.period
        }
        if not self.demand_commodities:
            raise ValueError(
                f'No demand commodities discovered in region {self.region} period {self.period}.  Check '
                f'Demand table data'
            )
        # scan non-annual techs...
        for r, p, s, d, ic, tech, v, oc in self.M.activeFlow_rpsditvo:
            if r == self.region and p == self.period:
                self.connections[oc].add((ic, tech))
                self.tech_inputs[tech].add(ic)
                self.tech_outputs[tech].add(oc)
        # scan annual techs...
        for r, p, ic, tech, v, oc in M.activeFlow_rpitvo:
            if r == self.region and p == self.period:
                self.connections[oc].add((ic, tech))
                self.tech_inputs[tech].add(ic)
                self.tech_outputs[tech].add(oc)

        # network of {destination: {origins}}
        self.network: dict[str, set[str]] = dict()

        self.connect_linked_techs()

        # TODO:  perhaps sockets later to account for links, for now, we will just look at internal connex
        # # set of exchange techs FROM this region that supply commodity through link
        # # {tech: set(output commodities)}
        # self.output_sockets: dict[str, set[str]] = dict()
        # self.input_sockets: ...

    def connect_linked_techs(self):
        # add implicit connections from linked tech...
        for (r, driver, emission), driven in self.M.LinkedTechs.items():
            if r == self.region:
                # check that the driven tech only has 1 input....
                # Dev Note:  It isn't clear how to link to a driven tech with multiple inputs as the linkage
                # is via the emission of the driver, and establishing links to all inputs of the driven
                # would likely supply false assurance that the multiple inputs were all viable
                if len(self.tech_inputs[driven]) > 1:
                    raise ValueError(
                        'Multiple input commodities detected for a driven Linked Tech.  This is '
                        'currently not supported because establishing the validity of the multiple '
                        'input commodities is not possible with current linkage data.'
                    )
                # check that the driver & driven techs both exist
                if driver in self.tech_outputs and driven in self.tech_outputs:  # we're gtg.
                    for oc in self.tech_outputs[driver]:
                        # we need to link the commodities via an implied link
                        # so the oc from the driver needs to be linked to the ic for the driven by a 'fake' tech
                        self.connections[oc].update(
                            {(ic, '<<linked tech>>') for ic in self.tech_inputs[driven]}
                        )

                # else, document errors in linkage...
                elif driver not in self.tech_outputs and driven not in self.tech_outputs:
                    # neither tech is present, not a problem
                    logger.debug(
                        'Note (no action reqd.):  Neither linked tech %s nor %s are active in region %s, period %s',
                        driver,
                        driven,
                        self.region,
                        self.period,
                    )
                elif driver in self.tech_outputs and driven not in self.tech_outputs:
                    logger.info(
                        'No driven linked tech available for driver %s in regions %s, period %d.  Driver may function without it.',
                        driver,
                        self.region,
                        self.period,
                    )
                else:  # the driver tech is not available, a problem because the driven could be allowed to run without constraint.
                    logger.warning(
                        'Driven linked tech %s is not connected to an active driver in region %s, period %d',
                        driven,
                        self.region,
                        self.period,
                    )
                    raise ValueError(
                        'Driven linked tech %s is not connected to a driver.  See log file details. \n'
                    )

    def analyze_network(self):
        # dev note:  send a copy of connections...
        # it is consumed by the function.  (easier than managing it in the recursion)
        discovered_sources, visited = _visited_dfs(
            self.demand_commodities, self.source_commodities, self.connections.copy()
        )
        self.good_connections = _mark_good_connections(
            good_ic=discovered_sources, connections=visited.copy()
        )

        logger.info(
            'Got %d good technologies (possibly multi-vintage) from %d techs in region %s, period %d',
            len(self.good_connections),
            len(tuple(chain(*self.connections.values()))),
            self.region,
            self.period,
        )
        # report the bad connections
        # need a flat list for comparison...
        orig_connections = set()
        for oc in self.connections:
            orig_connections |= {(ic, tech, oc) for (ic, tech) in self.connections[oc]}
        self.bad_connections = orig_connections - self.good_connections
        for bc in self.bad_connections:
            logger.warning(
                'Bad (orphan/disconnected) process should be investigated/removed: \n'
                '   %s in region %s, period %d',
                bc,
                self.region,
                self.period,
            )

    def unsupported_demands(self) -> set[str]:
        """
        Look for demand commodities that are amongst the "bad connections" set which would indicate
        that they cannot be traced back to a source and are suspect to magically being filled by some
        dangling intermediate tech
        :return: set of improperly supported demands
        """
        bad_demands = {oc for ic, tech, oc in self.bad_connections if oc in self.demand_commodities}
        return bad_demands


def _mark_good_connections(
    good_ic: set[str], connections: dict[str, set[tuple]], start: str | None = None
) -> set[tuple]:
    """
    Now that we have ID'ed the good ic that have been discovered, we need to work back up
    the chain of visited nodes to identify the good connections (this is the reverse of the
    previous search where we looked backward from demand.  Here we look up from the Input Commodities
    :param start: The current node to start from
    :param good_ic: The set of Input Commodities that were discovered by the first search
    :param connections:  The set of connections to analyze.  It is consumed by the function via pop()
    :return:
    """

    # end conditions...
    if not good_ic and not start:  # nothing to discover
        return set()
    else:
        good_connections = set()

    if not start:
        for start in good_ic:
            good_connections |= _mark_good_connections(good_ic, connections, start=start)

    # recurse...
    for oc, tech in connections.pop(start, []):  # prevent re-expanding this later by popping
        good_connections.add((start, tech, oc))
        # explore all upstream
        good_connections |= _mark_good_connections(
            good_ic=good_ic, connections=connections, start=oc
        )
    return good_connections


def _visited_dfs(
    start_nodes: set[str],
    end_nodes: set[str],
    connections: dict[str, set[tuple]],
    current_start=None,
) -> tuple[set, dict[str, set[tuple]]]:
    """
    recursive depth-first search to identify discovered source nodes and connections from
    a start point and set of connections
    :param start_nodes: the set of demand commodities (oc ∈ demand)
    :param end_nodes: source nodes, or ones traceable to source nodes
    :param connections: the connections to explore {output: {(ic, tech)}}
    :param current_start: the current node (ic) index
    :return: the set of viable tech tuples (ic, tech, oc)
    """
    # setup...
    discovered_sources = set()
    visited = defaultdict(set)

    # end conditions...
    if not current_start and not start_nodes:  # no more starts, we're done
        return set(), dict()
    if not current_start:  # start from each node in the starts
        for node in start_nodes:
            ds, v = _visited_dfs(
                start_nodes=start_nodes,
                end_nodes=end_nodes,
                connections=connections,
                current_start=node,
            )
            discovered_sources.update(ds)
            for k in v:
                visited[k].update(v[k])
        return discovered_sources, visited

    # we have a start node, dig from here.
    for ic, tech in connections.pop(current_start, []):  # we can pop, no need to re-explore
        visited[ic].add((current_start, tech))
        if ic in end_nodes:  # we have struck gold
            # add the current ic to discoveries
            discovered_sources.add(ic)
        else:
            # explore from here
            ds, v = _visited_dfs(
                start_nodes,
                end_nodes,
                connections,
                current_start=ic,
            )
            discovered_sources.update(ds)
            for k in v:
                visited[k].update(v[k])
    return discovered_sources, visited


def source_trace(M: 'TemoaModel') -> bool:
    """
    trace the demand commodities back to designated source technologies
    :param M: the model to inspect
    :return: True if all demands are traceable, False otherwise
    """
    logger.debug('Starting source trace')
    demands_traceable = True
    for region in M.regions:
        for p in M.time_optimize:
            try:
                commodity_network = CommodityNetwork(region=region, period=p, M=M)
            except ValueError:  # failed to initialize, just quit...
                break
            commodity_network.analyze_network()
            unsupported_demands = commodity_network.unsupported_demands()
            if unsupported_demands:
                demands_traceable = False
                for commodity in unsupported_demands:
                    logger.error(
                        'Demand %s is not supported back to source commodities in region %s period %d',
                        commodity,
                        commodity_network.region,
                        commodity_network.period,
                    )
    logger.debug('Completed source trace')
    return demands_traceable
