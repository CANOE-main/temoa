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
import sqlite3

from temoa.extensions.modeling_to_generate_alternatives.mga_constants import MgaAxis, MgaWeighting
from temoa.extensions.modeling_to_generate_alternatives.tech_activity_vector_manager import (
    TechActivityVectorManager,
)
from temoa.extensions.modeling_to_generate_alternatives.tech_capacity_vector_manager import (
    TechCapacityVectorManager,
)
from temoa.extensions.modeling_to_generate_alternatives.random_capacity_vector_manager import (
    RandomCapacityVectorManager,
)
from temoa.extensions.modeling_to_generate_alternatives.random_activity_vector_manager import (
    RandomActivityVectorManager,
)
from temoa.extensions.modeling_to_generate_alternatives.vector_manager import VectorManager
from temoa.temoa_model.temoa_model import TemoaModel


def get_manager(
    axis: MgaAxis,
    weighting: MgaWeighting,
    model: TemoaModel,
    con: sqlite3.Connection | None,
    **kwargs,
) -> VectorManager:
    match axis:
        case MgaAxis.TECH_CATEGORY_ACTIVITY:
            print("Running MGA using tech activity")
            return TechActivityVectorManager(
                base_model=model, conn=con, weighting=weighting, **kwargs
            )
        case MgaAxis.TECH_CATEGORY_CAPACITY:
            print("Running MGA using tech category capacity")
            return TechCapacityVectorManager(
                base_model=model, conn=con, weighting=weighting, **kwargs
            )
        case MgaAxis.RANDOM_TECH_CAPACITY:
            print("Running MGA using random tech capacity")
            return RandomCapacityVectorManager(
                base_model=model, conn=con, weighting=weighting, **kwargs
            )
        case MgaAxis.RANDOM_TECH_ACTIVITY:
            print("Running MGA using random tech activity")
            return RandomActivityVectorManager(
                base_model=model, conn=con, weighting=weighting, **kwargs
            )
        case _:
            raise NotImplementedError('This axis is not yet supported')
