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
Created on:  4/16/24

"""
import queue
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from logging import getLogger
from pathlib import Path
from queue import Queue
from typing import Iterable
import os

import numpy as np
import pandas as pd # for emergency data dumping
from matplotlib import pyplot as plt
from pyomo.core import Expression, Var, value, Objective, quicksum

from definitions import get_OUTPUT_PATH
from temoa.extensions.modeling_to_generate_alternatives.hull import Hull
from temoa.extensions.modeling_to_generate_alternatives.mga_constants import MgaWeighting
from temoa.extensions.modeling_to_generate_alternatives.vector_manager import VectorManager
from temoa.temoa_model.temoa_model import TemoaModel
from temoa.temoa_model.temoa_rules import get_loan_cost

logger = getLogger(__name__)


class DefaultItem:
    """A dummy class just to hold items that will have a reasonable __str__ and __repr__"""

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


# just a convenience to have something other than a None item for placeholder
default_cat = DefaultItem('DEFAULT')


class CostInvestVectorManager(VectorManager):
    def __init__(
        self,
        conn: sqlite3.Connection,
        base_model: TemoaModel,
        weighting: MgaWeighting,
        mga_config: dict,
        optimal_cost: float,
        cost_relaxation: float,
        seed: int | None = 2025,
    ):
        self.completed_solves = 0
        self.conn = conn
        self.base_model = base_model
        self.optimal_cost = optimal_cost
        self.cost_relaxation = cost_relaxation
        self.generation_index = 1  # index of how many models generated to couple inputs-outputs

        # Set seed for reproducibility
        np.random.seed(seed)
        logger.info(f'numpy random seed: {seed}')

        # {category : [technology, ...]}
        # the number of keys in this are the dimension of the hull
        self.category_mapping: dict | None = None

        self.random_vector_table: pd.DataFrame = None

        # {technology: [number of associated variables, ...]}
        self.technology_size: dict[str, int] = defaultdict(int)
        # in order to peel the data out of a solved model, we also need a rollup of the NAME
        # of the variable and indices in order...
        # {tech : {var_name : [indices, ...]}, ...}
        self.variable_index_mapping: dict[str, dict[str, list]] = {}

        self.coefficient_vector_queue: Queue[np.ndarray] = Queue()

        self.hull_monitor = mga_config.get('track_hull_volume', False)
        if self.hull_monitor:
            self.hull_points: np.ndarray | None = None
            self.hull: Hull | None = None
            self.perf_data = {}

        self.include_min_bases = mga_config.get('include_min_bases', True)
        if self.include_min_bases:
            logger.info('Including MGA minimisation basis vectors.')
        self.include_max_bases = mga_config.get('include_max_bases', True)
        if self.include_max_bases:
            logger.info('Including MGA maximisation basis vectors.')
        self.vector_file = Path(mga_config.get('random_vectors_file', None))
        self.reuse_random_vectors = False
        if self.vector_file is not None:
            self.reuse_random_vectors = True
            logger.info('Random vectors will be cached and reused from: %s', self.vector_file)

        self.initialize()
        self.basis_coefficients: Queue[np.ndarray] = self._generate_basis_coefficients(
            self.category_mapping, self.technology_size, self.include_min_bases, self.include_max_bases
        )
        

    def initialize(self) -> None:
        """
        Fill the internal data stores from db and model
        :return:
        """
        self.basis_coefficients = []
        techs_implemented = self.base_model.tech_all  # some may have been culled by source tracing
        logger.debug('Initializing Technology Vectors data elements')
        raw = self.conn.execute('SELECT category, tech FROM Technology ORDER BY tech').fetchall()
        self.category_mapping = defaultdict(list)
        for row in raw:
            cat, tech = row
            if cat in {None, ''}:
                # Ignore uncategorised (None or blank) technologies
                #cat = default_cat # devnote: Why? This would clump every uncategorised tech into one giant category for MGA
                continue
            if tech in techs_implemented:
                self.category_mapping[cat].append(tech)
                self.variable_index_mapping[tech] = defaultdict(list)

        if len(self.category_mapping) == 0:
            msg = "No categories were set in the Technology table!"
            logger.error(msg)
            raise RuntimeError(msg)
        else:
            print(f"Categories and number of technologies per category: {[(c, len(t)) for c, t in self.category_mapping.items()]}")

        if len(self.category_mapping) > 6:
            logger.info('More than 6 technology categories detected. Setting hull_monitor to False.')
            self.hull_monitor = False

        for cat in self.category_mapping:
            logger.debug('Category %s members: %d', cat, len(self.category_mapping[cat]))

        # now pull new capacity variables
        for idx in self.base_model.NewCapacityVar_rtv:
            if idx[2] not in self.base_model.time_optimize: continue
            tech = idx[1]
            if tech not in self.variable_index_mapping.keys(): continue
            self.technology_size[tech] += 1
            self.variable_index_mapping[tech][self.base_model.V_NewCapacity.name].append(idx)
        logger.debug('Catalogued %d Technology Variables', sum(self.technology_size.values()))

    @property
    def expired(self) -> bool:
        return False  # this Manager can always generate more...

    def group_variable_names(self, tech) -> list[Var]:
        return list(self.category_mapping.keys())

    def random_coefficients(self, n: int):
        return np.random.random(n) - 0.5
    
    def random_input_vector_model(self) -> TemoaModel:
        new_model = self.base_model.clone()
        new_model.name = self.new_model_name()
        var_vec, cost_vec = self.var_vector(new_model)
        
        # --------------------------------------------------------------------------------------------------
        # This block only if saving and reusing random vectors
        if self.reuse_random_vectors:
            if self.random_vector_table is None: self.random_vector_table = self.get_random_vectors_cache()
            
            df = self.random_vector_table
            if df is None:
                print("Created random vector table.")
                coeffs = self.random_coefficients(len(var_vec))
                df = pd.DataFrame(index=[str(var) for var in var_vec], data=coeffs, columns=[new_model.name])

            if new_model.name in df.columns:
                print("Running a random vector from table.")
                try:
                    coeffs = np.array([df[new_model.name][str(var)] for var in var_vec])
                except:
                    raise RuntimeError("Tried to get a random vector from file but failed. Has the model setup changed?")
            else:
                print("Running a new random vector.")
                coeffs = self.random_coefficients(len(var_vec))
                df_2 = pd.DataFrame(index=[str(var) for var in var_vec], data=coeffs, columns=[new_model.name])
                df = pd.concat([df, df_2], axis='columns')

            df.to_csv(self.vector_file)
            df.to_csv(Path(get_OUTPUT_PATH(), self.vector_file.name))

            self.random_vector_table = df
        # --------------------------------------------------------------------------------------------------
        else:
            coeffs = self.random_coefficients(len(var_vec)) # If we aren't saving and reusing the random vectors
            
        coeffs /= sum(abs(coeffs))
        obj_expr = quicksum(c * e for c, e in zip(coeffs, cost_vec))
        new_model.obj = Objective(expr=obj_expr)

        return new_model
    
    def get_random_vectors_cache(self) -> pd.DataFrame:
        if os.path.isfile(self.vector_file):
            print("Got random vector table from file.")
            return pd.read_csv(self.vector_file, index_col=0)
        else:
            print(f"Tried to get random vectors cache from file but doesn't exist: {self.vector_file}")
            return None

    def model_generator(self) -> Iterator[TemoaModel]:
        """
        Generate instances to solve. Start with the basis vectors, then ...
        :return: a TemoaModel instance
        """

        """ # Re-run the base model to get it in the dataset
        new_model = self.base_model.clone()
        new_model.name = self.new_model_name()
        print("Rerunning base model")
        yield new_model """

        if (self.include_min_bases or self.include_max_bases):
            # traverse the basis vectors first
            new_model = self.base_model.clone()
            obj_vector = self._make_basis_objective_vector(new_model)
            while obj_vector is not None:
                print("Running a basis vector")
                new_model.obj = Objective(expr=obj_vector)
                new_model.name = self.new_model_name()
                yield new_model
                new_model = self.base_model.clone()
                obj_vector = self._make_basis_objective_vector(new_model)

        # Random only
        while True:
            if self.hull_monitor:
                try: self.regenerate_hull()
                except: pass
            yield self.random_input_vector_model()

    def new_model_name(self) -> str:
        """produce a new name with updated index suffix"""
        base_name = self.base_model.name.split('-')[0]
        new_name = '-'.join((base_name, str(self.generation_index)))
        self.generation_index += 1
        return new_name

    def process_results(self, M: TemoaModel):
        """
        retrieve the necessary variable values to make another hull point
        :param M:
        :return: None
        """
        self.completed_solves += 1
        res = []
        for cat in self.category_mapping:
            element = 0
            for tech in self.category_mapping[cat]:
                for var_name in self.variable_index_mapping[tech]:
                    model_var = M.find_component(var_name)
                    if not isinstance(model_var, Var):
                        raise RuntimeError('hooked a bad fish')
                    element += sum(
                        value(model_var[idx]) for idx in self.variable_index_mapping[tech][var_name]
                    )
            res.append(element)
        
        # add it to the hull points
        if self.hull_monitor:
            hull_point = np.array(res)
            hull_point[hull_point < 0.01] = 0
            if self.hull_points is None:
                self.hull_points = np.atleast_2d(hull_point)
            else:
                self.hull_points = np.vstack((self.hull_points, hull_point))
            if self.hull_monitor:
                self.tracker()

        return res

    def stop_resolving(self) -> bool:
        pass

    @property
    def groups(self) -> Iterable[str]:
        return self.category_mapping.keys()

    def group_members(self, group) -> list[str]:
        return self.category_mapping.get(group, [])

    # noinspection PyTypeChecker
    def _make_basis_objective_vector(self, M: TemoaModel) -> Iterable[Expression] | None:
        """generator for basis vectors which will be the coefficients in the obj expression in the basis solves"""
        if self.basis_coefficients.empty():
            return None
        try:
            coeffs = self.basis_coefficients.get()
        except queue.Empty:
            return None

        # now we need to roll out a vector of the variables and pair them with coefficients...
        var_vec, cost_vec = self.var_vector(M)

        # verify a unit vector
        err = abs(abs(sum(coeffs)) - 1)
        assert err < 1e-6, 'unit vector size error'
        expr = sum(c * e for c, e in zip(coeffs, cost_vec) if c != 0)
        #expr += 1E-6 * self.loan_costs(M)
        return expr

    def var_vector(self, M: TemoaModel) -> tuple[list[Var], list[Expression]]:
        """Produce a properly sequenced array of variables from the current model for use in obj vector"""

        P_0 = min(M.time_optimize)
        GDR = value(M.GlobalDiscountRate)

        costs = []
        vars = []
        for cat in self.category_mapping:
            if cat == default_cat: continue
            for tech in self.category_mapping[cat]:
                for var_name in self.variable_index_mapping[tech]:
                    var = M.find_component(var_name)
                    if not isinstance(var, Var):
                        raise RuntimeError(
                            'Failed to retrieve a named variable from the model: %s', var_name
                        )
                    for r, t, v in self.variable_index_mapping[tech][var_name]:
                        # Iterating over indices that exist in CostInvest and time_optimize
                        if (r, t, v) in M.CostInvest.sparse_iterkeys() and v in M.time_optimize:
                            vars.append(var[r, t, v])
                            costs.append(get_loan_cost(M, r, t, v, P_0, GDR))
        return vars, costs

    def regenerate_hull(self):
        """make the hull..."""
        logger.debug('Generating the cvx hull from %d points', len(self.hull_points))
        self.hull = Hull(self.hull_points)
        fresh_vecs = self.hull.get_all_norms()
        np.random.shuffle(fresh_vecs)
        logger.info('Made %d fresh vectors', len(fresh_vecs))
        logger.info('Current Hull volume:  %0.2f', self.hull.cv_hull.volume)
        logger.info(
            'Current new vector rejection rate (for collinearity):  %0.2f',
            self.hull.norm_rejection_proportion,
        )
        self.load_normals(fresh_vecs)

    def load_normals(self, normals: np.array):
        for vector in normals:
            self.coefficient_vector_queue.put(vector)

    def input_vectors_available(self) -> int:
        return self.coefficient_vector_queue.qsize()

    @staticmethod
    def _generate_basis_coefficients (
        category_mapping: dict,
        technology_size: dict,
        include_min_bases: bool,
        include_max_bases: bool
    ) -> Queue:
        # Sequentially build the coefficient vector in the order of the categories and associated techs
        q = Queue()
        for selected_cat in category_mapping:
            res = []
            if selected_cat == default_cat:
                continue
            for cat in category_mapping:
                num_marks = sum(technology_size[tech] for tech in category_mapping[cat])
                if cat == selected_cat:
                    marks = [
                        1,
                    ] * num_marks
                else:
                    marks = [
                        0,
                    ] * num_marks
                res.extend(marks)

            entry = np.array(res)
            entry = entry / np.array(np.sum(entry))
            if include_min_bases: q.put(entry)  # +ve value -> minimisation
            if include_max_bases: q.put(-entry)  # -ve value -> maximisation

        return q

    def tracker(self):
        """
        A little function to track the size of the hull, after it is built initially
        Note:  This hull is a "throw away" and only used for volume calc, but it is pretty quick
        """
        points = self.hull_points[:, np.amax(self.hull_points, axis=0) - np.amin(self.hull_points, axis=0) > 1]
        pd.DataFrame(points).to_csv(Path(get_OUTPUT_PATH(), 'hull_points.csv'))
        try: self.hull = Hull(points) # bit of a hack... works when there are enough points...
        except Exception as e:
            print(e)
            return
        volume = self.hull.volume
        logger.info(f'Tracking hull at {volume}')
        self.perf_data.update({len(self.hull_points): volume})

    def finalize_tracker(self):
        if not self.hull_monitor:
            return
        fout = Path(get_OUTPUT_PATH(), 'hull_performance.png')
        pts = sorted(self.perf_data.keys())
        y = [self.perf_data[pt] for pt in pts]
        try:
            plt.plot(pts, y)
            plt.xlabel('Iteration')
            plt.ylabel('N-Dimensional Hull Volume')
            plt.savefig(str(fout))
        except Exception as e:
            print(e)
            pass