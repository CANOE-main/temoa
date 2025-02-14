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
"""

from logging import getLogger
from sys import stderr as SE
from typing import TYPE_CHECKING

from pyomo.core import Var, Expression
from pyomo.environ import Constraint, value

from temoa.temoa_model.temoa_initialize import (
    DemandConstraintErrorCheck,
    CommodityBalanceConstraintErrorCheck,
    AnnualCommodityBalanceConstraintErrorCheck,
    gather_group_regions,
)

if TYPE_CHECKING:
    from temoa.temoa_model.temoa_model import TemoaModel

logger = getLogger(__name__)
# ---------------------------------------------------------------
# Define the derived variables used in the objective function
# and constraints below.
# ---------------------------------------------------------------


def AdjustedCapacity_Constraint(M: 'TemoaModel', r, p, t, v):
    r"""
    This constraint updates the capacity of a process by taking into account retirements.
    For a given :code:`(r,p,t,v)` index, this constraint sets the capacity equal to
    the amount installed in period :code:`v` and subtracts from it any and all retirements
    that occurred up until the period in question, :code:`p`."""
    if t not in M.tech_retirement:
        if v in M.time_exist:
            return M.V_Capacity[r, p, t, v] == value(M.ExistingCapacity[r, t, v])
        else:
            return M.V_Capacity[r, p, t, v] == M.V_NewCapacity[r, t, v]

    else:
        retired_cap = sum(
            M.V_RetiredCapacity[r, S_p, t, v] for S_p in M.time_optimize if p >= S_p > v
        )
        if v in M.time_exist:
            return M.V_Capacity[r, p, t, v] == value(M.ExistingCapacity[r, t, v]) - retired_cap
        else:
            return M.V_Capacity[r, p, t, v] == M.V_NewCapacity[r, t, v] - retired_cap


def Capacity_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""
    This constraint ensures that the capacity of a given process is sufficient
    to support its activity across all time periods and time slices. The calculation
    on the left hand side of the equality is the maximum amount of energy a process
    can produce in the timeslice :code:`(s,d)`. Note that the curtailment variable
    shown below only applies to technologies that are members of the curtailment set.
    Curtailment is necessary to track explicitly in scenarios that include a high
    renewable target. Without it, the model can generate more activity than is used
    to meet demand, and have all activity (including the portion curtailed) count
    towards the target. Tracking activity and curtailment separately prevents this
    possibility.

    .. math::
       :label: Capacity

           \left (
                   \text{CFP}_{r, t, v}
             \cdot \text{C2A}_{r, t}
             \cdot \text{SEG}_{s, d}
             \cdot \text{PLF}_{r, p, t, v}
           \right )
           \cdot \textbf{CAP}_{r, t, v}
           =
           \sum_{I, O} \textbf{FO}_{r, p, s, d, i, t, v, o}
           +
           \sum_{I, O} \textbf{CUR}_{r, p, s, d, i, t, v, o}

       \\
       \forall \{r, p, s, d, t, v\} \in \Theta_{\text{FO}}
    """
    if t in M.tech_storage:
        return Constraint.Skip
    # The expressions below are defined in-line to minimize the amount of
    # expression cloning taking place with Pyomo.

    useful_activity = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )
    if (r, s, d, t, v) in M.CapacityFactorProcess:
        # use the data provided
        capacity = value(M.CapacityFactorProcess[r, s, d, t, v])
    else:  # use the capacity factor for the tech
        capacity = value(M.CapacityFactorTech[r, s, d, t])
    
    if t in M.tech_curtailment:
        # If technologies are present in the curtailment set, then enough
        # capacity must be available to cover both activity and curtailment.
        return (
            capacity
            * value(M.CapacityToActivity[r, t])
            * value(M.SegFrac[s, d])
            * value(M.ProcessLifeFrac[r, p, t, v])
            * M.V_Capacity[r, p, t, v] == useful_activity + sum(
                M.V_Curtailment[r, p, s, d, S_i, t, v, S_o]
                for S_i in M.processInputs[r, p, t, v]
                for S_o in M.processOutputsByInput[r, p, t, v, S_i]
            )
        )
    else:
        return (
            capacity
            * value(M.CapacityToActivity[r, t])
            * value(M.SegFrac[s, d])
            * value(M.ProcessLifeFrac[r, p, t, v])
            * M.V_Capacity[r, p, t, v]
            >= useful_activity
        )


def CapacityAnnual_Constraint(M: 'TemoaModel', r, p, t, v):
    r"""
Similar to Capacity_Constraint, but for technologies belonging to the
:code:`tech_annual`  set. Technologies in the tech_annual set have constant output
across different timeslices within a year, so we do not need to ensure
that installed capacity is sufficient across all timeslices, thus saving
some computational effort. Instead, annual output is sufficient to calculate
capacity.

.. math::
   :label: CapacityAnnual

       \left (
               \text{CFP}_{r, t, v}
         \cdot \text{C2A}_{r, t}
         \cdot \text{PLF}_{r, p, t, v}
       \right )
       \cdot \textbf{CAP}_{r, t, v}
   =
       \sum_{I, O} \textbf{FOA}_{r, p, i, t \in T^{a}, v, o}

   \\
   \forall \{r, p, t \in T^{a}, v\} \in \Theta_{\text{Activity}}


"""
    CF = 1  # placeholder CF

    activity_rptv = sum(
        M.V_FlowOutAnnual[r, p, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    return (
        CF
        * value(M.CapacityToActivity[r, t])
        * value(M.ProcessLifeFrac[r, p, t, v])
        * M.V_Capacity[r, p, t, v]
        >= activity_rptv
    )


def ActivityByTech_Constraint(M: 'TemoaModel', t):
    r"""
    This constraint is utilized by the MGA objective function and defines
    the total activity of a technology over the planning horizon. The first version
    below applies to technologies with variable output at the timeslice level,
    and the second version applies to technologies with constant annual output
    in the :code:`tech_annual` set.

    .. math::
       :label: ActivityByTech

           \textbf{ACT}_{t} = \sum_{R, P, S, D, I, V, O} \textbf{FO}_{r, p, s, d,i, t, v, o}
           \;
           \forall t \not\in T^{a}

           \textbf{ACT}_{t} = \sum_{R, P, I, V, O} \textbf{FOA}_{r, p, i, t, v, o}
           \;
           \forall t \in T^{a}
    """
    if t not in M.tech_annual:
        indices = []
        for s_index in M.FlowVar_rpsditvo:
            if t in s_index:
                indices.append(s_index)
        activity = sum(M.V_FlowOut[s_index] for s_index in indices)
    else:
        indices = []
        for s_index in M.FlowVarAnnual_rpitvo:
            if t in s_index:
                indices.append(s_index)
        activity = sum(M.V_FlowOutAnnual[s_index] for s_index in indices)

    if int is type(activity):
        return Constraint.Skip

    expr = M.V_ActivityByTech[t] == activity
    return expr


def CapacityAvailableByPeriodAndTech_Constraint(M: 'TemoaModel', r, p, t):
    r"""

The :math:`\textbf{CAPAVL}` variable is nominally for reporting solution values,
but is also used in the Max and Min constraint calculations.  For any process
with an end-of-life (EOL) on a period boundary, all of its capacity is available
for use in all periods in which it is active (the process' PLF is 1). However,
for any process with an EOL that falls between periods, Temoa makes the
simplifying assumption that the available capacity from the expiring technology
is available through the whole period in proportion to its remaining lifetime.
For example, if a process expires 3 years into an 8-year model time period,
then only :math:`\frac{3}{8}` of the installed capacity is available for use
throughout the period.

.. math::
   :label: CapacityAvailable

   \textbf{CAPAVL}_{r, p, t} = \sum_{v, p_i \leq p} {PLF}_{r, p, t, v} \cdot \left
   ( \textbf{CAP}_{r, t, v} - \textbf{CAPRET}_{r, p_i, t, v} \right )

   \\
   \forall p \in \text{P}^o, r \in R, t \in T
"""
    cap_avail = sum(
        value(M.ProcessLifeFrac[r, p, t, S_v]) * M.V_Capacity[r, p, t, S_v]
        for S_v in M.processVintages[r, p, t]
    )

    expr = M.V_CapacityAvailableByPeriodAndTech[r, p, t] == cap_avail
    return expr


def RetiredCapacity_Constraint(M: 'TemoaModel', r, p, t, v):
    r"""

Temoa allows for the economic retirement of technologies presented in the
:code:`tech_retirement` set. This constraint sets the upper limit of retired
capacity to the total installed capacity.
In the equation below, we set the upper bound of the retired capacity to the
previous period's total installed capacity (CAPAVL)

.. math::
   :label: RetiredCapacity

   \textbf{CAPRET}_{r, p, t, v} \leq \sum_{V} {PLF}_{r, p, t, v} \cdot \textbf{CAP}_{r, t, v}
   \\
   \forall \{r, p, t, v\} \in \Theta_{\text{RetiredCapacity}}
"""
    if p == M.time_optimize.first():
        cap_avail = value(M.ExistingCapacity[r, t, v])
    else:
        cap_avail = M.V_Capacity[r, M.time_optimize.prev(p), t, v]
    expr = M.V_RetiredCapacity[r, p, t, v] <= cap_avail
    return expr


# ---------------------------------------------------------------
# Define the Objective Function
# ---------------------------------------------------------------
def TotalCost_rule(M):
    r"""

    Using the :code:`FlowOut` and :code:`Capacity` variables, the Temoa objective
    function calculates the cost of energy supply, under the assumption that capital
    costs are paid through loans. This implementation sums up all the costs incurred,
    and is defined as :math:`C_{tot} = C_{loans} + C_{fixed} + C_{variable}`. Each
    term on the right-hand side represents the cost incurred over the model
    time horizon and discounted to the initial year in the horizon (:math:`{P}_0`).
    The calculation of each term is given below.

    .. math::
       :label: obj_loan

       C_{loans} = \sum_{r, t, v \in \Theta_{IC}} \left (
         \left [
                 CI_{r, t, v} \cdot LA_{r, t, v}
                 \cdot \frac{(1 + GDR)^{P_0 - v +1} \cdot (1 - (1 + GDR)^{-LLP_{r, t, v}})}{GDR} \right. \right.
                 \\ \left. \left. \cdot \frac{ 1-(1+GDR)^{-LPA_{r,t,v}} }{ 1-(1+GDR)^{-LTP_{r,t,v}} }
         \right ]
         \cdot \textbf{CAP}_{r, t, v}
         \right )

    Note that capital costs (:math:`{IC}_{r,t,v}`) are handled in several steps. First, each capital cost
    is amortized using the loan rate (i.e., technology-specific discount rate) and loan
    period. Second, the annual stream of payments is converted into a lump sum using
    the global discount rate and loan period. Third, the new lump sum is amortized
    at the global discount rate and technology lifetime. Fourth, loan payments beyond
    the model time horizon are removed and the lump sum recalculated. The terms used
    in Steps 3-4 are :math:`\frac{ GDR }{ 1-(1+GDR)^{-LTP_{r,t,v} } }\cdot
    \frac{ 1-(1+GDR)^{-LPA_{t,v}} }{ GDR }`. The product simplifies to
    :math:`\frac{ 1-(1+GDR)^{-LPA_{r,t,v}} }{ 1-(1+GDR)^{-LTP_{r,t,v}} }`, where
    :math:`LPA_{r,t,v}` represents the active lifetime of process t in region r :math:`(r,t,v)`
    before the end of the model horizon, and :math:`LTP_{r,t,v}` represents the full
    lifetime of a regional process :math:`(r,t,v)`. Fifth, the lump sum is discounted back to the
    beginning of the horizon (:math:`P_0`) using the global discount rate. While an
    explicit salvage term is not included, this approach properly captures the capital
    costs incurred within the model time horizon, accounting for technology-specific
    loan rates and periods.

    .. math::
       :label: obj_fixed

       C_{fixed} = \sum_{r, p, t, v \in \Theta_{CF}} \left (
         \left [
                 CF_{r, p, t, v}
           \cdot \frac{(1 + GDR)^{P_0 - p +1} \cdot (1 - (1 + GDR)^{-{MPL}_{r, t, v}})}{GDR}
         \right ]
         \cdot \textbf{CAP}_{r, t, v}
         \right )

    .. math::
       :label: obj_variable

        &C_{variable} = \\ &\quad \sum_{r, p, t, v \in \Theta_{CV}} \left (
               CV_{r, p, t, v}
         \cdot
         \frac{
           (1 + GDR)^{P_0 - p + 1} \cdot (1 - (1 + GDR)^{-{MPL}_{r,p,t,v}})
         }{
           GDR
         }\cdot \sum_{S,D,I, O} \textbf{FO}_{r, p, s, d,i, t, v, o}
         \right ) \\ &\quad + \sum_{r, p, t \not \in T^{a}, v \in \Theta_{VC}} \left (
               CV_{r, p, t, v}
         \cdot
         \frac{
           (1 + GDR)^{P_0 - p + 1} \cdot (1 - (1 + GDR)^{-{MPL}_{r,p,t,v}})
         }{
           GDR
         }
         \cdot \sum_{I, O} \textbf{FOA}_{r, p,i, t \in T^{a}, v, o}
         \right )

    .. math::
        :label: obj_emissions

        &C_{emissions} = \\ &\quad \sum_{r, p, t, v \in \Theta_{CV}} \left (
               CE_{r, p, c} \cdot EAC_{r,e,i,t,v,o}
         \cdot
         \frac{
           (1 + GDR)^{P_0 - p + 1} \cdot (1 - (1 + GDR)^{-{MPL}_{r,p,t,v}})
         }{
           GDR
         }\cdot \sum_{S,D,I, O} \textbf{FO}_{r, p, s, d,i, t, v, o}
         \right ) \\ &\quad + \sum_{r, p, t \not \in T^{a}, v \in \Theta_{CE}} \left (
               CE_{r, p, c} \cdot EAC_{r,e,i,t,v,o}
         \cdot
         \frac{
           (1 + GDR)^{P_0 - p + 1} \cdot (1 - (1 + GDR)^{-{MPL}_{r,p,t,v}})
         }{
           GDR
         }
         \cdot \sum_{I, O} \textbf{FOA}_{r, p,i, t \in T^{a}, v, o}
         \right )

    """

    return sum(PeriodCost_rule(M, p) for p in M.time_optimize)


def loan_cost(
    capacity: float | Var,
    invest_cost: float,
    loan_annualize: float,
    lifetime_loan_process: float | int,
    lifetime_process: int,
    P_0: int,
    P_e: int,
    GDR: float,
    vintage: int,
) -> float | Expression:
    """
    function to calculate the loan cost.  It can be used with fixed values to produce a hard number or
    pyomo variables/params to make a pyomo Expression
    :param capacity: The capacity to use to calculate cost
    :param invest_cost: the cost/capacity
    :param loan_annualize: parameter
    :param lifetime_loan_process: lifetime of the loan
    :param P_0: the year to discount the costs back to
    :param P_e: the 'end year' or cutoff year for loan payments
    :param GDR: Global Discount Rate
    :param vintage: the base year of the loan
    :return: fixed number or pyomo expression based on input types
    """
    if GDR == 0:  # return the non-discounted result
        annuity = capacity * invest_cost * loan_annualize * lifetime_loan_process / lifetime_process
        payments_made = min(lifetime_process, P_e - vintage)
        return annuity * payments_made
    x = 1 + GDR  # a convenience
    res = (
        capacity
        * (
            invest_cost
            * loan_annualize
            * (
                lifetime_loan_process
                if not GDR
                else (x ** (P_0 - vintage + 1) * (1 - x ** (-lifetime_loan_process)) / GDR)
            )
        )
        * (
            (1 - x ** (-min(lifetime_process, P_e - vintage)))
            / (1 - x ** (-lifetime_process))
        )
    )
    return res


def fixed_or_variable_cost(
    cap_or_flow: float | Var,
    cost_factor: float,
    cost_years: float,
    GDR: float | None,
    P_0: float,
    p: int,
) -> float | Expression:
    """
    Extraction of the fixed and var cost formulation.  (It is same for both with either capacity or
    flow as the driving variable.)
    :param cap_or_flow: Capacity if fixed cost / flow out if variable
    :param cost_factor: the cost (either fixed or variable) of the cap/flow variable
    :param cost_years: for how many years is this cost incurred
    :param GDR: discount rate or None
    :param P_0: the period to discount this back to
    :param p: the period under evaluation
    :return:
    """
    x = 1 + GDR
    res = cap_or_flow * (
        cost_factor
        * (
            cost_years
            if not GDR
            else (x ** (P_0 - p + 1) * (1 - x ** (-cost_years)) / GDR)
        )
    )
    return res


def PeriodCost_rule(M: 'TemoaModel', p):
    P_0 = min(M.time_optimize)
    P_e = M.time_future.last()  # End point of modeled horizon
    GDR = value(M.GlobalDiscountRate)
    MPL = M.ModelProcessLife

    if value(M.MyopicBaseyear) != 0:
        P_0 = value(M.MyopicBaseyear)

    loan_costs = sum(
        loan_cost(
            M.V_NewCapacity[r, S_t, S_v],
            value(M.CostInvest[r, S_t, S_v]),
            value(M.LoanAnnualize[r, S_t, S_v]),
            value(M.LoanLifetimeProcess[r, S_t, S_v]),
            value(M.LifetimeProcess[r, S_t, S_v]),
            P_0,
            P_e,
            GDR,
            vintage=S_v,
        )
        for r, S_t, S_v in M.CostInvest.sparse_iterkeys()
        if S_v == p
    )

    fixed_costs = sum(
        fixed_or_variable_cost(
            M.V_Capacity[r, p, S_t, S_v],
            value(M.CostFixed[r, p, S_t, S_v]),
            value(MPL[r, p, S_t, S_v]),
            GDR,
            P_0,
            p=p,
        )
        for r, S_p, S_t, S_v in M.CostFixed.sparse_iterkeys()
        if S_p == p
    )

    variable_costs = sum(
        fixed_or_variable_cost(
            M.V_FlowOut[r, p, s, d, S_i, S_t, S_v, S_o],
            value(M.CostVariable[r, p, S_t, S_v]),
            value(M.PeriodLength[p]),
            GDR,
            P_0,
            p,
        )
        for r, S_p, S_t, S_v in M.CostVariable.sparse_iterkeys()
        if S_p == p and S_t not in M.tech_annual
        for S_i in M.processInputs[r, S_p, S_t, S_v]
        for S_o in M.processOutputsByInput[r, S_p, S_t, S_v, S_i]
        for s in M.time_season
        for d in M.time_of_day
    )

    variable_costs_annual = sum(
        fixed_or_variable_cost(
            M.V_FlowOutAnnual[r, p, S_i, S_t, S_v, S_o],
            value(M.CostVariable[r, p, S_t, S_v]),
            value(M.PeriodLength[p]),
            GDR,
            P_0,
            p,
        )
        for r, S_p, S_t, S_v in M.CostVariable.sparse_iterkeys()
        if S_p == p and S_t in M.tech_annual
        for S_i in M.processInputs[r, S_p, S_t, S_v]
        for S_o in M.processOutputsByInput[r, S_p, S_t, S_v, S_i]
    )

    # The emissions costs occur over the five possible emission sources.
    # to do any/all of them we need 2 baseline sets:  The regular and annual sets
    # of indices that are valid which is basically the filter of:
    #     EmissionActivty by CostEmission
    # and to ensure that the techology is active we need to filter that
    # result with processInput.keys()

    # ================= Emissions and Flex and Curtailment =================
    # Flex flows are deducted from V_FlowOut, so it is NOT NEEDED to tax them again.  (See commodity balance constr)
    # Curtailment does not draw any inputs, so it seems logical that curtailed flows not be taxed either
    # Earlier versions of this code had accounting for flex & curtailment that have been removed.

    base = [
        (r, p, e, i, t, v, o)
        for (r, e, i, t, v, o) in M.EmissionActivity
        if (r, p, e) in M.CostEmission  # tightest filter first
        and (r, p, t, v) in M.processInputs
    ]

    # then expand the base for the normal (season/tod) set and annual separately:
    normal = [
        (r, p, e, s, d, i, t, v, o)
        for (r, p, e, i, t, v, o) in base
        for s in M.time_season
        for d in M.time_of_day
        if t not in M.tech_annual
    ]

    annual = [(r, p, e, i, t, v, o) for (r, p, e, i, t, v, o) in base if t in M.tech_annual]

    # 1. variable emissions
    var_emissions = sum(
        fixed_or_variable_cost(
            cap_or_flow=M.V_FlowOut[r, p, s, d, i, t, v, o] * value(M.EmissionActivity[r, e, i, t, v, o]),
            cost_factor=value(M.CostEmission[r, p, e]),
            cost_years=value(M.PeriodLength[p]),
            GDR=GDR,
            P_0=P_0,
            p=p,
        )
        for (r, p, e, s, d, i, t, v, o) in normal
    )

    # 2. flex emissions -- removed (double counting, flex wastes are SUBTRACTIVE from flowout)

    # 3. curtailment emissions -- removed (curtailment is no-flow, for accounting only, so no emissions)

    # 4. annual emissions
    var_annual_emissions = sum(
        fixed_or_variable_cost(
            cap_or_flow=M.V_FlowOutAnnual[r, p, i, t, v, o] * value(M.EmissionActivity[r, e, i, t, v, o]),
            cost_factor=value(M.CostEmission[r, p, e]),
            cost_years=value(M.PeriodLength[p]),
            GDR=GDR,
            P_0=P_0,
            p=p,
        )
        for (r, p, e, i, t, v, o) in annual
        if t not in M.tech_flex
    )

    # 5. flex annual emissions -- removed (double counting, flex wastes are SUBTRACTIVE from flowout)

    # 6. embodied - treated as a fixed cost in a single year (year of construction)
    embodied_emissions = sum(
        fixed_or_variable_cost(
            cap_or_flow=M.V_NewCapacity[r, t, v] * value(M.EmissionEmbodied[r, e, t, v]),
            cost_factor=value(M.CostEmission[r, p, e]),
            cost_years=1, # We assume the embodied emissions are emitted in the same year as the capacity is installed.
            GDR=GDR,
            P_0=P_0,
            p=p,
        )
        for (r, e, t, v) in M.EmissionEmbodied.sparse_iterkeys()
        if v == p
    )

    period_emission_cost = var_emissions + var_annual_emissions + embodied_emissions

    period_costs = (
        loan_costs + fixed_costs + variable_costs + variable_costs_annual + period_emission_cost
    )
    return period_costs


# ---------------------------------------------------------------
# Define the Model Constraints.
# The order of constraint definitions follows the same order as the
# declarations in temoa_model.py.
# ---------------------------------------------------------------


def Demand_Constraint(M: 'TemoaModel', r, p, s, d, dem):
    r"""

    The Demand constraint drives the model.  This constraint ensures that supply at
    least meets the demand specified by the Demand parameter in all periods and
    slices, by ensuring that the sum of all the demand output commodity (:math:`c`)
    generated by both commodity flow at the time slice level (:math:`\textbf{FO}`) and
    the annual level (:math:`\textbf{FOA}`) must meet the modeler-specified demand
    in each time slice.

    .. math::
       :label: Demand

           \sum_{I, T-T^{a}, V} \textbf{FO}_{r, p, s, d, i, t \not \in T^{a}, v, dem} +
           SEG_{s,d} \cdot  \sum_{I, T^{a}, V} \textbf{FOA}_{r, p, i, t \in T^{a}, v, dem}
           =
           {DEM}_{r, p, dem} \cdot {DSD}_{r, s, d, dem}

    Note that the validity of this constraint relies on the fact that the
    :math:`C^d` set is distinct from both :math:`C^e` and :math:`C^p`. In other
    words, an end-use demand must only be an end-use demand.  Note that if an output
    could satisfy both an end-use and internal system demand, then the output from
    :math:`\textbf{FO}` and :math:`\textbf{FOA}` would be double counted."""

    supply = sum(
        M.V_FlowOut[r, p, s, d, S_i, S_t, S_v, dem]
        for S_t, S_v in M.commodityUStreamProcess[r, p, dem]
        if S_t not in M.tech_annual
        for S_i in M.processInputsByOutput[r, p, S_t, S_v, dem]
    )

    supply_annual = sum(
        M.V_FlowOutAnnual[r, p, S_i, S_t, S_v, dem]
        for S_t, S_v in M.commodityUStreamProcess[r, p, dem]
        if S_t in M.tech_annual
        for S_i in M.processInputsByOutput[r, p, S_t, S_v, dem]
    ) * value(M.SegFrac[s, d])

    DemandConstraintErrorCheck(supply + supply_annual, r, p, s, d, dem)

    expr = (
        supply + supply_annual == value(M.Demand[r, p, dem]) * get_demand_distribution(M, r, p, s, d, dem)
    )

    return expr


def DemandActivity_Constraint(M: 'TemoaModel', r, p, s, d, t, v, dem, s_0, d_0):
    r"""

    For end-use demands, it is unreasonable to let the model arbitrarily shift the
    use of demand technologies across time slices. For instance, if household A buys
    a natural gas furnace while household B buys an electric furnace, then both units
    should be used throughout the year.  Without this constraint, the model might choose
    to only use the electric furnace during the day, and the natural gas furnace during the
    night.

    This constraint ensures that the ratio of a process activity to demand is
    constant for all time slices.  Note that if a demand is not specified in a given
    time slice, or is zero, then this constraint will not be considered for that
    slice and demand.  This is transparently handled by the :math:`\Theta` superset.

    .. math::
       :label: DemandActivity

          DEM_{r, p, s, d, dem} \cdot \sum_{I} \textbf{FO}_{r, p, s_0, d_0, i, t \not \in T^{a}, v, dem}
       =
          DEM_{r, p, s_0, d_0, dem} \cdot \sum_{I} \textbf{FO}_{r, p, s, d, i, t \not \in T^{a}, v, dem}

       \\
       \forall \{r, p, s, d, t, v, dem, s_0, d_0\} \in \Theta_{\text{DemandActivity}}

    Note that this constraint is only applied to the demand commodities with diurnal
    variations, and therefore the equation above only includes :math:`\textbf{FO}`
    and not  :math:`\textbf{FOA}`
    """

    act_a = sum(
        M.V_FlowOut[r, p, s_0, d_0, S_i, t, v, dem]
        for S_i in M.processInputsByOutput[r, p, t, v, dem]
    )
    act_b = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, dem] for S_i in M.processInputsByOutput[r, p, t, v, dem]
    )

    expr = (
        act_a * get_demand_distribution(M, r, p, s, d, dem)
        == act_b * get_demand_distribution(M, r, p, s_0, d_0, dem)
    )
    return expr


def CommodityBalance_Constraint(M: 'TemoaModel', r, p, s, d, c):
    r"""
    Where the Demand constraint :eq:`Demand` ensures that end-use demands are met,
    the CommodityBalance constraint ensures that the endogenous system demands are
    met.  This constraint requires the total production of a given commodity
    to equal the amount consumed, thus ensuring an energy balance at the system
    level. In this most general form of the constraint, the energy commodity being
    balanced has variable production at the time slice level. The energy commodity
    can then be consumed by three types of processes: storage technologies, non-storage
    technologies with output that varies at the time slice level, and non-storage
    technologies with constant annual output.

    Separate expressions are required in order to account for the consumption of
    commodity :math:`c` by downstream processes. For the commodity flow into storage
    technologies, we use :math:`\textbf{FI}_{r, p, s, d, i, t, v, c}`. Note that the FlowIn
    variable is defined only for storage technologies, and is required because storage
    technologies balance production and consumption across time slices rather than
    within a single time slice. For commodity flows into non-storage processes with time
    varying output, we use :math:`\textbf{FO}_{r, p, s, d, i, t, v, c}/EFF_{r, i,t,v,o}`.
    The division by :math:`EFF_{r, c,t,v,o}` is applied to the output flows that consume
    commodity :math:`c` to determine input flows. Finally, we need to account
    for the consumption of commodity :math:`c` by the processes in
    :code:`tech_annual`. Since the commodity flow of these processes is on an
    annual basis, we use :math:`SEG_{s,d}` to calculate the consumption of
    commodity :math:`c` in time-slice :math:`(s,d)` from the annual flows.
    Formulating an expression for the production of commodity :math:`c` is
    more straightforward, and is simply calculated by
    :math:`\textbf{FO}_{r, p, s, d, i, t, v, c}`.

    In some cases, the overproduction of a commodity may be required, such
    that the supply exceeds the endogenous demand. Refineries represent a
    common example, where the share of different refined products are governed
    by TechOutputSplit, but total production is driven by a particular commodity
    like gasoline. Such a situtation can result in the overproduction of other
    refined products, such as diesel or kerosene. In such cases, we need to
    track the excess production of these commodities. To do so, the technology
    producing the excess commodity should be added to the :code:`tech_flex` set.
    This flexible technology designation will activate a slack variable
    (:math:`\textbf{FLX}_{r, p, s, d, i, t, v, c}`) representing
    the excess production in the :code:`CommodityBalanceAnnual_Constraint`. Note
    that the :code:`tech_flex` set is different from :code:`tech_curtailment` set;
    the latter is technology- rather than commodity-focused and is used in the
    :code:`Capacity_Constraint` to track output that is used to produce useful
    output and the amount curtailed, and to ensure that the installed capacity
    covers both.

    This constraint also accounts for imports and exports between regions
    when solving multi-regional systems. The import (:math:`\textbf{FIM}`) and export
    (:math:`\textbf{FEX}`) variables are created on-the-fly by summing the
    :math:`\textbf{FO}` variables over the appropriate import and export regions,
    respectively, which are defined in :code:`temoa_initialize.py` by parsing the
    :code:`tech_exchange` processes.

    Finally, for annual commodities, AnnualCommodityBalance is used which balances
    the sum of flows over each year.

    *production + imports = consumption + exports + flex waste*

    .. math::
       :label: CommodityBalance

           \sum_{I, T, V} \textbf{FO}_{r, p, s, d, i, t, v, c}
           +
           &\sum_{reg} \textbf{FIM}_{r-reg, p, s, d, i, t, v, c} \; \forall reg \neq r
           \\
           = &\sum_{T^{s}, V, I} \textbf{FIS}_{r, p, s, d, c, t, v, o}
           \\ &\quad +
           \sum_{T-T^{s}, V, O} \textbf{FO}_{r, p, s, d, c, t, v, o} /EFF_{r, c,t,v,o}
           \\
           &\quad + \; SEG_{s,d} \cdot
           \sum_{I, T^{a}, V} \textbf{FOA}_{r, p, c, t \in T^{a}, v, o} /EFF_{r, c,t,v,o} \\
           &\quad + \sum_{reg} \textbf{FEX}_{r-reg, p, s, d, c, t, v, o} \; \forall reg \neq r
           \\ &\quad + \;
           \textbf{FLX}_{r, p, s, d, i, t, v, c}

           \\
           &\forall \{r, p, s, d, c\} \in \Theta_{\text{CommodityBalance}}

    """
    if c in M.commodity_demand: # Is this necessary? Demand comms have no downstream process no shouldnt be in indices
        return Constraint.Skip

    # Only storage techs have a flow in variable
    # For other techs, it would be redundant as in = out / eff
    stored = sum(
        M.V_FlowIn[r, p, s, d, c, S_t, S_v, S_o]
        for S_t, S_v in M.commodityDStreamProcess[r, p, c]
        if S_t in M.tech_storage
        for S_o in M.processOutputsByInput[r, p, S_t, S_v, c]
    )

    consumed = sum(
        M.V_FlowOut[r, p, s, d, c, S_t, S_v, S_o] / get_variable_efficiency(M, r, p, s, d, c, S_t, S_v, S_o)
        for S_t, S_v in M.commodityDStreamProcess[r, p, c]
        if S_t not in M.tech_storage and S_t not in M.tech_annual
        for S_o in M.processOutputsByInput[r, p, S_t, S_v, c]
    )

    consumed_annual = value(M.SegFrac[s, d]) * sum(
        M.V_FlowOutAnnual[r, p, c, S_t, S_v, S_o] / get_variable_efficiency(M, r, p, s, d, c, S_t, S_v, S_o)
        for S_t, S_v in M.commodityDStreamProcess[r, p, c]
        if S_t not in M.tech_storage and S_t in M.tech_annual
        for S_o in M.processOutputsByInput[r, p, S_t, S_v, c]
    )

    # Includes output from storage
    produced = sum(
        M.V_FlowOut[r, p, s, d, S_i, S_t, S_v, c]
        for S_t, S_v in M.commodityUStreamProcess[r, p, c]
        if S_t not in M.tech_annual
        for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
    )

    produced_annual = value(M.SegFrac[s, d]) * sum(
        M.V_FlowOutAnnual[r, p, S_i, S_t, S_v, c]
        for S_t, S_v in M.commodityUStreamProcess[r, p, c]
        if S_t in M.tech_annual
        for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
    )

    # export of commodity c from region r to other regions
    exported = 0
    if (r, p, c) in M.exportRegions:
        exported = sum(
            M.V_FlowOut[r + '-' + reg, p, s, d, c, S_t, S_v, S_o]
            / get_variable_efficiency(M, r + '-' + reg, p, s, d, c, S_t, S_v, S_o)
            for reg, S_t, S_v, S_o in M.exportRegions[r, p, c]
        )

    # import of commodity c from other regions into region r
    imported = 0
    if (r, p, c) in M.importRegions:
        imported = sum(
            M.V_FlowOut[reg + '-' + r, p, s, d, S_i, S_t, S_v, c]
            for reg, S_t, S_v, S_i in M.importRegions[r, p, c]
        )

    flex_waste = 0
    flex_waste_annual = 0
    if c in M.flex_commodities:
        flex_waste = sum(
            M.V_Flex[r, p, s, d, S_i, S_t, S_v, c]
            for S_t, S_v in M.commodityUStreamProcess[r, p, c]
            if S_t not in M.tech_annual and S_t in M.tech_flex
            for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
        )
        flex_waste_annual = value(M.SegFrac[s, d]) * sum(
            M.V_FlexAnnual[r, p, S_i, S_t, S_v, c]
            for S_t, S_v in M.commodityUStreamProcess[r, p, c]
            if S_t in M.tech_annual and S_t in M.tech_flex
            for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
        )

    supplied = produced + produced_annual + imported
    demanded = stored + consumed + consumed_annual + exported + flex_waste + flex_waste_annual

    CommodityBalanceConstraintErrorCheck(
        supplied,
        demanded,
        r,
        p,
        s,
        d,
        c,
    )

    expr = supplied == demanded

    return expr


def AnnualCommodityBalance_Constraint(M: 'TemoaModel', r, p, c):
    r"""
    Similar to CommodityBalance_Constraint but only balances the supply and demand of the commodity
    at the annual level, summing all flows over the year. Applies only to commodities tagged as annual
    'a' in the Commodity table.
    """

    if c in M.commodity_demand: # Is this necessary? Demand comms have no downstream process no shouldnt be in indices
        return Constraint.Skip
    
    # Only storage techs have a flow in variable
    # For other techs, it would be redundant as in = out / eff
    stored = sum(
        M.V_FlowIn[r, p, S_s, S_d, c, S_t, S_v, S_o]
        for S_s in M.time_season
        for S_d in M.time_of_day
        for S_t, S_v in M.commodityDStreamProcess[r, p, c]
        if S_t in M.tech_storage
        for S_o in M.processOutputsByInput[r, p, S_t, S_v, c]
    )

    consumed = sum(
        M.V_FlowOut[r, p, S_s, S_d, c, S_t, S_v, S_o] / get_variable_efficiency(M, r, p, S_s, S_d, c, S_t, S_v, S_o)
        for S_s in M.time_season
        for S_d in M.time_of_day
        for S_t, S_v in M.commodityDStreamProcess[r, p, c]
        if S_t not in M.tech_storage and S_t not in M.tech_annual
        for S_o in M.processOutputsByInput[r, p, S_t, S_v, c]
    )

    consumed_annual = sum(
        M.V_FlowOutAnnual[r, p, c, S_t, S_v, S_o] / value(M.Efficiency[r, c, S_t, S_v, S_o])
        for S_t, S_v in M.commodityDStreamProcess[r, p, c]
        if S_t not in M.tech_storage and S_t in M.tech_annual
        for S_o in M.processOutputsByInput[r, p, S_t, S_v, c]
    )

    # Includes output from storage
    produced = sum(
        M.V_FlowOut[r, p, S_s, S_d, S_i, S_t, S_v, c]
        for S_s in M.time_season
        for S_d in M.time_of_day
        for S_t, S_v in M.commodityUStreamProcess[r, p, c]
        if S_t not in M.tech_annual
        for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
    )

    produced_annual = sum(
        M.V_FlowOutAnnual[r, p, S_i, S_t, S_v, c]
        for S_t, S_v in M.commodityUStreamProcess[r, p, c]
        if S_t in M.tech_annual
        for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
    )

    # export of commodity c from region r to other regions
    exported = 0
    if (r, p, c) in M.exportRegions:
        exported = sum(
            M.V_FlowOut[r + '-' + S_r, p, S_s, S_d, c, S_t, S_v, S_o]
            / get_variable_efficiency(M, r + '-' + S_r, p, S_s, S_d, c, S_t, S_v, S_o)
            for S_s in M.time_season
            for S_d in M.time_of_day
            for S_r, S_t, S_v, S_o in M.exportRegions[r, p, c]
        )

    # import of commodity c from other regions into region r
    imported = 0
    if (r, p, c) in M.importRegions:
        imported = sum(
            M.V_FlowOut[S_r + '-' + r, p, S_s, S_d, S_i, S_t, S_v, c]
            for S_s in M.time_season
            for S_d in M.time_of_day
            for S_r, S_t, S_v, S_i in M.importRegions[r, p, c]
        )

    flex_waste = 0
    flex_waste_annual = 0
    if c in M.flex_commodities:
        flex_waste = sum(
            M.V_Flex[r, p, S_s, S_d, S_i, S_t, S_v, c]
            for S_s in M.time_season
            for S_d in M.time_of_day
            for S_t, S_v in M.commodityUStreamProcess[r, p, c]
            if S_t not in M.tech_annual and S_t in M.tech_flex
            for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
        )
        flex_waste_annual = sum(
            M.V_FlexAnnual[r, p, S_i, S_t, S_v, c]
            for S_t, S_v in M.commodityUStreamProcess[r, p, c]
            if S_t in M.tech_flex and S_t in M.tech_annual
            for S_i in M.processInputsByOutput[r, p, S_t, S_v, c]
        )

    supplied = produced + produced_annual + imported
    demanded = stored + consumed + consumed_annual + exported + flex_waste + flex_waste_annual

    AnnualCommodityBalanceConstraintErrorCheck(
        supplied,
        demanded,
        r,
        p,
        c,
    )

    expr = supplied == demanded

    return expr


def ResourceExtraction_Constraint(M: 'TemoaModel', reg, p, r):
    r"""
    The ResourceExtraction constraint allows a modeler to specify an annual limit on
    the amount of a particular resource Temoa may use in a period. The first version
    of the constraint pertains to technologies with variable output at the time slice
    level, and the second version pertains to technologies with constant annual output
    belonging to the :code:`tech_annual` set.

    .. math::
       :label: ResourceExtraction

       \sum_{S, D, I, t \in T^r \& t \not \in T^{a}, V} \textbf{FO}_{r, p, s, d, i, t, v, c} \le RSC_{r, p, c}

       \forall \{r, p, c\} \in \Theta_{\text{ResourceExtraction}}

       \sum_{I, t \in T^r \& t \in T^{a}, V} \textbf{FOA}_{r, p, i, t, v, c} \le RSC_{r, p, c}

       \forall \{r, p, c\} \in \Theta_{\text{ResourceExtraction}}
    """
    logger.warning(
        'The ResourceBound parameter / ResourceExtraction constraint is not currently supported.  '
        'Recommend removing data from supporting table'
    )
    # dev note:  This constraint does not have a table in the current schema
    #            Additionally, the below (incorrect) construct assumes that a resource cannot be used
    #            by BOTH a non-annual and annual tech.  It should be re-written to add these
    # dev note:  Cant think of a case where this would be needed but cant use MaxActivityGroup
    try:
        collected = sum(
            M.V_FlowOut[reg, p, S_s, S_d, S_i, S_t, S_v, r] # is r the input or the output!?
            for S_i, S_t, S_v in M.processByPeriodAndOutput.keys()
            for S_s in M.time_season
            for S_d in M.time_of_day
        )
    except KeyError:
        collected = sum(
            M.V_FlowOutAnnual[reg, p, S_i, S_t, S_v, r]
            for S_i, S_t, S_v in M.processByPeriodAndOutput.keys()
        )

    expr = collected <= value(M.ResourceBound[reg, p, r])
    return expr


def BaseloadDiurnal_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""

    Some electric generators cannot ramp output over a short period of time (e.g.,
    hourly or daily). Temoa models this behavior by forcing technologies in the
    :code:`tech_baseload` set to maintain a constant output across all times-of-day
    within the same season. Note that the output of a baseload process can vary
    between seasons.

    Ideally, this constraint would not be necessary, and baseload processes would
    simply not have a :math:`d` index.  However, implementing the more efficient
    functionality is currently on the Temoa TODO list.

    .. math::
       :label: BaseloadDaily

             SEG_{s, D_0}
       \cdot \sum_{I, O} \textbf{FO}_{r, p, s, d,i, t, v, o}
       =
             SEG_{s, d}
       \cdot \sum_{I, O} \textbf{FO}_{r, p, s, D_0,i, t, v, o}

       \\
       \forall \{r, p, s, d, t, v\} \in \Theta_{\text{BaseloadDiurnal}}
    """
    # Question: How to set the different times of day equal to each other?

    # Step 1: Acquire a "canonical" representation of the times of day
    l_times = sorted(M.time_of_day)  # i.e. a sorted Python list.
    # This is the commonality between invocations of this method.

    index = l_times.index(d)
    if 0 == index:
        # When index is 0, it means that we've reached the beginning of the array
        # For the algorithm, this is a terminating condition: do not create
        # an effectively useless constraint
        return Constraint.Skip

    # Step 2: Set the rest of the times of day equal in output to the first.
    # i.e. create a set of constraints that look something like:
    # tod[ 2 ] == tod[ 1 ]
    # tod[ 3 ] == tod[ 1 ]
    # tod[ 4 ] == tod[ 1 ]
    # and so on ...
    d_0 = l_times[0]

    # Step 3: the actual expression.  For baseload, must compute the /average/
    # activity over the segment.  By definition, average is
    #     (segment activity) / (segment length)
    # So:   (ActA / SegA) == (ActB / SegB)
    #   computationally, however, multiplication is cheaper than division, so:
    #       (ActA * SegB) == (ActB * SegA)
    activity_sd = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    activity_sd_0 = sum(
        M.V_FlowOut[r, p, s, d_0, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = activity_sd * value(M.SegFrac[s, d_0]) == activity_sd_0 * value(M.SegFrac[s, d])

    return expr


def RegionalExchangeCapacity_Constraint(M: 'TemoaModel', r_e, r_i, p, t, v):
    r"""

    This constraint ensures that the process (t,v) connecting regions
    r_e and r_i is handled by one capacity variables.

    .. math::
       :label: RegionalExchangeCapacity

          \textbf{CAP}_{r_e,t,v}
          =
          \textbf{CAP}_{r_i,t,v}

          \\
          \forall \{r_e, r_i, t, v\} \in \Theta_{\text{RegionalExchangeCapacity}}
    """

    expr = M.V_Capacity[r_e + '-' + r_i, p, t, v] == M.V_Capacity[r_i + '-' + r_e, p, t, v]

    return expr


def StorageEnergy_Constraint(M: 'TemoaModel', r, p, s, d, t, v):

    # This is the sum of all input=i sent TO storage tech t of vintage v with
    # output=o in p,s,d
    charge = sum(
        M.V_FlowIn[r, p, s, d, S_i, t, v, S_o] * get_variable_efficiency(M, r, p, s, d, S_i, t, v, S_o)
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    # This is the sum of all output=o withdrawn FROM storage tech t of vintage v
    # with input=i in p,s,d
    discharge = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_o in M.processOutputs[r, p, t, v]
        for S_i in M.processInputsByOutput[r, p, t, v, S_o]
    )

    stored_energy = charge - discharge

    s_next, d_next = M.time_next[s, d]

    expr = M.V_StorageLevel[r, p, s, d, t, v] + stored_energy == M.V_StorageLevel[r, p, s_next, d_next, t, v]

    return expr





def StorageEnergyUpperBound_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""

    This constraint ensures that the amount of energy stored does not exceed
    the upper bound set by the energy capacity of the storage device, as calculated
    on the right-hand side.

    Because the number and duration of time slices are user-defined, we need to adjust
    the storage duration, which is specified in hours. First, the hourly duration is divided
    by the number of hours in a year to obtain the duration as a fraction of the year.
    Since the :math:`C2A` parameter assumes the conversion of capacity to annual activity,
    we need to express the storage duration as fraction of a year. Then, :math:`SEG_{s,d}`
    summed over the time-of-day slices (:math:`d`) multiplied by 365 days / yr yields the
    number of days per season. This step is necessary because conventional time sliced models
    use a single day to represent many days within a given season. Thus, it is necessary to
    scale the storage duration to account for the number of days in each season.

    .. math::
       :label: StorageEnergyUpperBound

          \textbf{SL}_{r, p, s, d, t, v} \le
          \textbf{CAP}_{r,t,v} \cdot C2A_{r,t} \cdot \frac {SD_{r,t}}{8760 hrs/yr}
          \cdot \sum_{d} SEG_{s,d} \cdot 365 days/yr

          \\
          \forall \{r, p, s, d, t, v\} \in \Theta_{\text{StorageEnergyUpperBound}}

    """

    energy_capacity = (
        M.V_Capacity[r, p, t, v]
        * value(M.CapacityToActivity[r, t])
        * (value(M.StorageDuration[r, t]) / 8760)
        * M.SegFracPerSeason[s]
        * 365
        * value(M.ProcessLifeFrac[r, p, t, v])
    )
    
    expr = M.V_StorageLevel[r, p, s, d, t, v] <= energy_capacity

    return expr


def StorageChargeRate_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""

    This constraint ensures that the charge rate of the storage unit is
    limited by the power capacity (typically GW) of the storage unit.

    .. math::
       :label: StorageChargeRate

          \sum_{I, O} \textbf{FIS}_{r, p, s, d, i, t, v, o} \cdot EFF_{r,i,t,v,o}
          \le
          \textbf{CAP}_{r,t,v} \cdot C2A_{r,t} \cdot SEG_{s,d}

          \\
          \forall \{r, p, s, d, t, v\} \in \Theta_{\text{StorageChargeRate}}

    """
    # Calculate energy charge in each time slice
    slice_charge = sum(
        M.V_FlowIn[r, p, s, d, S_i, t, v, S_o] * get_variable_efficiency(M, r, p, s, d, S_i, t, v, S_o)
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    # Maximum energy charge in each time slice
    max_charge = (
        M.V_Capacity[r, p, t, v]
        * value(M.CapacityToActivity[r, t])
        * value(M.SegFrac[s, d])
        * value(M.ProcessLifeFrac[r, p, t, v])
    )

    # Energy charge cannot exceed the power capacity of the storage unit
    expr = slice_charge <= max_charge

    return expr


def StorageDischargeRate_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""

    This constraint ensures that the discharge rate of the storage unit
    is limited by the power capacity (typically GW) of the storage unit.

    .. math::
       :label: StorageDischargeRate

          \sum_{I, O} \textbf{FO}_{r, p, s, d, i, t, v, o}
          \le
          \textbf{CAP}_{r,t,v} \cdot C2A_{r,t} \cdot SEG_{s,d}

          \\
          \forall \{r,p, s, d, t, v\} \in \Theta_{\text{StorageDischargeRate}}
    """
    # Calculate energy discharge in each time slice
    slice_discharge = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_o in M.processOutputs[r, p, t, v]
        for S_i in M.processInputsByOutput[r, p, t, v, S_o]
    )

    # Maximum energy discharge in each time slice
    max_discharge = (
        M.V_Capacity[r, p, t, v]
        * value(M.CapacityToActivity[r, t])
        * value(M.SegFrac[s, d])
        * value(M.ProcessLifeFrac[r, p, t, v])
    )

    # Energy discharge cannot exceed the capacity of the storage unit
    expr = slice_discharge <= max_discharge

    return expr


def StorageThroughput_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""

    It is not enough to only limit the charge and discharge rate separately. We also
    need to ensure that the maximum throughput (charge + discharge) does not exceed
    the capacity (typically GW) of the storage unit.

    .. math::
       :label: StorageThroughput

          \sum_{I, O} \textbf{FO}_{r, p, s, d, i, t, v, o}
          +
          \sum_{I, O} \textbf{FIS}_{r, p, s, d, i, t, v, o} \cdot EFF_{r,i,t,v,o}
          \le
          \textbf{CAP}_{r,t,v} \cdot C2A_{r,t} \cdot SEG_{s,d}

          \\
          \forall \{r, p, s, d, t, v\} \in \Theta_{\text{StorageThroughput}}
    """
    discharge = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_o in M.processOutputs[r, p, t, v]
        for S_i in M.processInputsByOutput[r, p, t, v, S_o]
    )

    charge = sum(
        M.V_FlowIn[r, p, s, d, S_i, t, v, S_o] * get_variable_efficiency(M, r, p, s, d, S_i, t, v, S_o)
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    throughput = charge + discharge
    max_throughput = (
        M.V_Capacity[r, p, t, v]
        * value(M.CapacityToActivity[r, t])
        * value(M.SegFrac[s, d])
        * value(M.ProcessLifeFrac[r, p, t, v])
    )
    expr = throughput <= max_throughput
    return expr


def StorageFraction_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""

    This constraint is used if the users wishes to force a specific storage charge level
    for certain storage technologies and vintages at a certain time slice.
    In this case, the value of the decision variable :math:`\textbf{SI}_{r,t,v}` is set by
    this constraint rather than being optimized. User-specified storage charge levels that are
    sufficiently different from the optimal :math:`\textbf{SI}_{r,t,v}` could impact the
    cost-effectiveness of storage. For example, if the optimal charge level happens to be
    50% of the full energy capacity, forced charge levels (specified by parameter
    :math:`SIF_{r,t,v}`) equal to 10% or 90% of the full energycapacity could lead to
    more expensive solutions.


    .. math::
       :label: StorageFraction

          \textbf{SF}_{r,p,s,d,t,v} \le
          \ SF_{r,p,s,d,t,v}
          \cdot
          \textbf{CAP}_{r,p,t,v} \cdot C2A_{r,t} \cdot \frac {SD_{r,t}}{8760 hrs/yr}
          \cdot \sum_{d} SEG_{s,d} \cdot 365 days/yr \cdot MPL_{r,p,t,v}

          \\
          \forall \{r, p, s, d, t, v\} \in \Theta_{\text{StorageFraction}}
    """

    energy_capacity = (
        M.V_Capacity[r, p, t, v]
        * value(M.CapacityToActivity[r, t])
        * (value(M.StorageDuration[r, t]) / 8760)
        * M.SegFracPerSeason[s]
        * 365
        * value(M.ProcessLifeFrac[r, p, t, v])
    )

    expr = M.V_StorageLevel[r, p, s, d, t, v] == energy_capacity * value(M.StorageFraction[r, p, s, d, t, v])

    return expr


def RampUp_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    # M.time_of_day is a sorted set, and M.time_of_day.first() returns the first
    # element in the set, similarly, M.time_of_day.last() returns the last element.
    # M.time_of_day.prev(d) function will return the previous element before s, and
    # M.time_of_day.next(d) function will return the next element after s.

    r"""

    The ramp rate constraint is utilized to limit the rate of electricity generation
    increase and decrease between two adjacent time slices in order to account for
    physical limits associated with thermal power plants. Note that this constraint
    only applies to technologies with ramp capability, which is defined in the set
    :math:`T^{m}`. We assume for simplicity the rate limits for both
    ramp up and down are equal and they do not vary with technology vintage. The
    ramp rate limits (:math:`r_t`) for technology :math:`t` should be expressed in
    percentage of its rated capacity.

    Note that when :math:`d_{nd}` is the last time-of-day, :math:`d_{nd + 1} \not \in
    \textbf{D}`, i.e., if one time slice is the last time-of-day in a season and the
    other time slice is the first time-of-day in the next season, the ramp rate
    limits between these two time slices can not be expressed by :code:`RampUpDay`.
    Therefore, the ramp rate constraints between two adjacent seasons are
    represented in :code:`RampUpSeason`.

    In the :code:`RampUpDay` and :code:`RampUpSeason` constraints, we assume
    :math:`\textbf{S} = \{s_i, i = 1, 2, \cdots, ns\}` and
    :math:`\textbf{D} = \{d_i, i = 1, 2, \cdots, nd\}`.

    .. math::
       :label: RampUpDay

          \frac{
              \sum_{I, O} \textbf{FO}_{r, p, s, d_{i + 1}, i, t, v, o}
              }{
              SEG_{s, d_{i + 1}} \cdot C2A_{r,t}
              }
          -
          \frac{
              \sum_{I, O} \textbf{FO}_{r, p, s, d_i, i, t, v, o}
              }{
              SEG_{s, d_i} \cdot C2A_{r,t}
              }
          \leq
          r_t \cdot \textbf{CAPAVL}_{r,p,t}
          \\
          \forall \{r, p, s, d, t, v\} \in \Theta_{\text{RampUpDay}}
    """

    s_next, d_next = M.time_next[s, d]

    activity_sd = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    ) / value(M.SegFrac[s, d])

    activity_sd_next = sum(
        M.V_FlowOut[r, p, s_next, d_next, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    ) / value(M.SegFrac[s_next, d_next])

    hours_elapsed = 8760 * ( value(M.SegFrac[s, d]) + value(M.SegFrac[s_next, d_next]) ) / 2
    hours_elapsed /= M.SegFracPerSeason[s] * 365 # adjust for how many days this season represents
    ramp_fraction = hours_elapsed * value(M.RampUp[r, t])

    if ramp_fraction >= 1:
        msg = (
            "Warning: Hourly ramp up rate ({}, {}) is too large to be constraining from ({}, {}) to ({}, {}). Constraint skipped."
        )
        logger.warning(msg.format(r, t, s, d, s_next, d_next))
        return Constraint.Skip

    activity_increase = activity_sd_next - activity_sd # opposite sign from rampdown
    rampable_activity = ramp_fraction * M.V_Capacity[r, p, t, v] * value(M.CapacityToActivity[r, t]) * value(M.ProcessLifeFrac[r, p, t, v])
    expr = activity_increase <= rampable_activity

    return expr


def RampDown_Constraint(M: 'TemoaModel', r, p, s, d, t, v):
    r"""

    Similar to the :code`RampUpDay` constraint, we use the :code:`RampDownDay`
    constraint to limit ramp down rates between any two adjacent time slices.

    .. math::
       :label: RampDownDay

          \frac{
              \sum_{I, O} \textbf{FO}_{r, p, s, d_{i + 1}, i, t, v, o}
              }{
              SEG_{s, d_{i + 1}} \cdot C2A_{r,t}
              }
          -
          \frac{
              \sum_{I, O} \textbf{FO}_{r, p, s, d_i, i, t, v, o}
              }{
              SEG_{s, d_i} \cdot C2A_{r,t}
              }
          \geq
          -r_t \cdot \textbf{CAPAVL}_{r,p,t}
          \\
          \forall \{r, p, s, d, t, v\} \in \Theta_{\text{RampDownDay}}
    """

    s_next, d_next = M.time_next[s, d]

    activity_sd = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    ) / value(M.SegFrac[s, d])

    activity_sd_next = sum(
        M.V_FlowOut[r, p, s_next, d_next, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    ) / value(M.SegFrac[s_next, d_next])

    hours_elapsed = 8760 * ( value(M.SegFrac[s, d]) + value(M.SegFrac[s_next, d_next]) ) / 2
    hours_elapsed /= M.SegFracPerSeason[s] * 365 # adjust for how many days this season represents
    ramp_fraction = hours_elapsed * value(M.RampDown[r, t])

    if ramp_fraction >= 1:
        msg = (
            "Warning: Hourly ramp down rate ({}, {}) is too large to be constraining from ({}, {}) to ({}, {}). Constraint skipped."
        )
        logger.warning(msg.format(r, t, s, d, s_next, d_next))
        return Constraint.Skip

    activity_decrease = activity_sd - activity_sd_next # opposite sign from rampup
    rampable_activity = ramp_fraction * M.V_Capacity[r, p, t, v] * value(M.CapacityToActivity[r, t]) * value(M.ProcessLifeFrac[r, p, t, v])
    expr = activity_decrease <= rampable_activity

    return expr


def ReserveMargin_Constraint(M: 'TemoaModel', r, p, s, d):
    r"""

    During each period :math:`p`, the sum of the available capacity of all reserve
    technologies :math:`\sum_{t \in T^{e}} \textbf{CAPAVL}_{r,p,t}`, which are
    defined in the set :math:`\textbf{T}^{r,e}`, should exceed the peak load by
    :math:`PRM`, the regional reserve margin. Note that the reserve
    margin is expressed in percentage of the peak load. Generally speaking, in
    a database we may not know the peak demand before running the model, therefore,
    we write this equation for all the time-slices defined in the database in each region.

    .. math::
        :label: reserve_margin

            &\sum_{t \in T^{res} \setminus T^{e}} {CC_{t,r} \cdot \textbf{CAPAVL}_{p,t} \cdot SEG_{s^*,d^*} \cdot C2A_{r,t} }\\
            &+ \sum_{t \in T^{res} \cap T^{e}} {CC_{t,r_i-r} \cdot \textbf{CAPAVL}_{p,t} \cdot SEG_{s^*,d^*} \cdot C2A_{r_i-r,t} }\\
            &- \sum_{t \in T^{res} \cap T^{e}} {CC_{t,r-r_i} \cdot \textbf{CAPAVL}_{p,t} \cdot SEG_{s^*,d^*} \cdot C2A_{r_i-r,t} }\\
            &\geq \left [ \sum_{ t \in T^{res} \setminus T^{e},V,I,O } \textbf{FO}_{r, p, s, d, i, t, v, o}\right.\\
            &+ \sum_{ t \in T^{res} \cap T^{e},V,I,O } \textbf{FO}_{r_i-r, p, s, d, i, t, v, o}\\
            &- \sum_{ t \in T^{res} \cap T^{e},V,I,O } \textbf{FI}_{r-r_i, p, s, d, i, t, v, o}\\
            &- \left.\sum_{ t \in T^{res} \cap T^{s},V,I,O } \textbf{FI}_{r, p, s, d, i, t, v, o}  \right]  \cdot (1 + PRM_r)\\
            &\qquad \qquad \forall \{r, p, s, d\} \in \Theta_{\text{ReserveMargin}} \text{and} \forall r_i \in R
    """
    if (not M.tech_reserve) or (
        (r, p) not in M.processReservePeriods.keys()
    ):  # If reserve set empty or if r,p not in M.processReservePeriod.keys(), skip the constraint
        return Constraint.Skip

    cap_avail = sum(
        value(M.CapacityCredit[r, p, t, v])
        * value(M.ProcessLifeFrac[r, p, t, v])
        * M.V_Capacity[r, p, t, v]
        * value(M.CapacityToActivity[r, t])
        * value(M.SegFrac[s, d])
        for t in M.tech_reserve
        if (r, p, t) in M.processVintages.keys()
        for v in M.processVintages[r, p, t]
        # Make sure (r,p,t,v) combinations are defined
        if (r, p, t, v) in M.activeCapacityAvailable_rptv
    )

    # The above code does not consider exchange techs, e.g. electricity
    # transmission between two distinct regions.
    # We take exchange takes into account below.
    # Note that a single exchange tech linking regions Ri and Rj is twice
    # defined: once for region "Ri-Rj" and once for region "Rj-Ri".

    # First, determine the amount of firm capacity each exchange tech
    # contributes.
    for r1r2 in M.regionalIndices:
        if '-' not in r1r2:
            continue
        r1, r2 = r1r2.split('-')

        # Only consider the capacity of technologies that import to
        # the region in question -- i.e. for cases where r2 == r.
        if r2 != r:
            continue

        # add the available capacity of the exchange tech.
        cap_avail += sum(
            value(M.CapacityCredit[r1r2, p, t, v])
            * value(M.ProcessLifeFrac[r1r2, p, t, v])
            * M.V_Capacity[r1r2, p, t, v]
            * value(M.CapacityToActivity[r1r2, t])
            * value(M.SegFrac[s, d])
            for t in M.tech_reserve
            if (r1r2, p, t) in M.processVintages.keys()
            for v in M.processVintages[r1r2, p, t]
            # Make sure (r,p,t,v) combinations are defined
            if (r1r2, p, t, v) in M.activeCapacityAvailable_rptv
        )

    # In most Temoa input databases, demand is endogenous, so we use electricity
    # generation instead as a proxy for electricity demand.
    total_generation = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, S_v, S_o]
        for (t, S_v) in M.processReservePeriods[r, p]
        for S_i in M.processInputs[r, p, t, S_v]
        for S_o in M.processOutputsByInput[r, p, t, S_v, S_i]
    )

    # We must take into account flows into storage technologies.
    # Flows into storage technologies need to be subtracted from the
    # load calculation.
    total_generation -= sum(
        M.V_FlowIn[r, p, s, d, S_i, t, S_v, S_o]
        for (t, S_v) in M.processReservePeriods[r, p]
        if t in M.tech_storage
        for S_i in M.processInputs[r, p, t, S_v]
        for S_o in M.processOutputsByInput[r, p, t, S_v, S_i]
    )

    # Electricity imports and exports via exchange techs are accounted
    # for below:
    for r1r2 in M.regionalIndices:  # ensure the region is of the form r1-r2
        if '-' not in r1r2:
            continue
        if (r1r2, p) not in M.processReservePeriods:  # ensure the technology in question exists
            continue
        r1, r2 = r1r2.split('-')
        # First, determine the exports, and subtract this value from the
        # total generation.
        if r1 == r:
            total_generation -= sum(
                M.V_FlowOut[r1r2, p, s, d, S_i, t, S_v, S_o]
                / get_variable_efficiency(M, r1r2, p, s, d, S_i, t, S_v, S_o)
                for (t, S_v) in M.processReservePeriods[r1r2, p]
                for S_i in M.processInputs[r1r2, p, t, S_v]
                for S_o in M.processOutputsByInput[r1r2, p, t, S_v, S_i]
            )
        # Second, determine the imports, and add this value from the
        # total generation.
        elif r2 == r:
            total_generation += sum(
                M.V_FlowOut[r1r2, p, s, d, S_i, t, S_v, S_o]
                for (t, S_v) in M.processReservePeriods[r1r2, p]
                for S_i in M.processInputs[r1r2, p, t, S_v]
                for S_o in M.processOutputsByInput[r1r2, p, t, S_v, S_i]
                if (t, S_v) in M.processReservePeriods[r1r2, p]
            )

    cap_target = total_generation * (1 + value(M.PlanningReserveMargin[r]))
    return cap_avail >= cap_target


def EmissionLimit_Constraint(M: 'TemoaModel', r, p, e):
    r"""

    A modeler can track emissions through use of the :code:`commodity_emissions`
    set and :code:`EmissionActivity` parameter.  The :math:`EAC` parameter is
    analogous to the efficiency table, tying emissions to a unit of activity.  The
    EmissionLimit constraint allows the modeler to assign an upper bound per period
    to each emission commodity. Note that this constraint sums emissions from
    technologies with output varying at the time slice and those with constant annual
    output in separate terms.

    .. math::
       :label: EmissionLimit

           \sum_{S,D,I,T,V,O|{r,e,i,t,v,o} \in EAC} \left (
           EAC_{r, e, i, t, v, o} \cdot \textbf{FO}_{r, p, s, d, i, t, v, o}
           \right ) & \\
           +
           \sum_{I,T,V,O|{r,e,i,t \in T^{a},v,o} \in EAC} (
           EAC_{r, e, i, t, v, o} \cdot & \textbf{FOA}_{r, p, i, t \in T^{a}, v, o}
            )
           \le
           ELM_{r, p, e}

           \\
           & \forall \{r, p, e\} \in \Theta_{\text{EmissionLimit}}

    """
    emission_limit = value(M.EmissionLimit[r, p, e])

    # r can be an individual region (r='US'), or a combination of regions separated by a + (r='Mexico+US+Canada'),
    # or 'global'.  Note that regions!=M.regions. We iterate over regions to find actual_emissions
    # and actual_emissions_annual.

    # if r == 'global', the constraint is system-wide

    regions = gather_group_regions(M, r)

    # ================= Emissions and Flex and Curtailment =================
    # Flex flows are deducted from V_FlowOut, so it is NOT NEEDED to tax them again.  (See commodity balance constr)
    # Curtailment does not draw any inputs, so it seems logical that curtailed flows not be taxed either

    process_emissions = sum(
        M.V_FlowOut[reg, p, S_s, S_d, S_i, S_t, S_v, S_o]
        * value(M.EmissionActivity[reg, e, S_i, S_t, S_v, S_o])
        for reg in regions
        for tmp_r, tmp_e, S_i, S_t, S_v, S_o in M.EmissionActivity.sparse_iterkeys()
        if tmp_e == e and tmp_r == reg and S_t not in M.tech_annual
        # EmissionsActivity not indexed by p, so make sure (r,p,t,v) combos valid
        if (reg, p, S_t, S_v) in M.processInputs.keys()
        for S_s in M.time_season
        for S_d in M.time_of_day
    )

    process_emissions_annual = sum(
        M.V_FlowOutAnnual[reg, p, S_i, S_t, S_v, S_o]
        * value(M.EmissionActivity[reg, e, S_i, S_t, S_v, S_o])
        for reg in regions
        for tmp_r, tmp_e, S_i, S_t, S_v, S_o in M.EmissionActivity.sparse_iterkeys()
        if tmp_e == e and tmp_r == reg and S_t in M.tech_annual
        # EmissionsActivity not indexed by p, so make sure (r,p,t,v) combos valid
        if (reg, p, S_t, S_v) in M.processInputs.keys()
    )

    embodied_emissions = sum(
        M.V_NewCapacity[reg, t, v]
        * value(M.EmissionEmbodied[reg, e, t, v])
        for reg in regions
        for (S_r, S_e, t, v) in M.EmissionEmbodied.sparse_iterkeys()
        if v == p and S_r == reg and S_e == e
    )

    expr = (
        process_emissions + process_emissions_annual + embodied_emissions
        # + emissions_flex # NO! flex is subtracted from flowout, already accounted by flowout
        # + emissions_curtail # NO! curtailed flows are not actual flows, just an accounting tool
        # + emissions_flex_annual # NO! flexannual is subtracted from flowoutannual, already accounted
        <= emission_limit
    )

    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        msg = (
            "Warning: No technology produces emission '%s', though limit was " 'specified as %s.\n'
        )
        logger.warning(msg, (e, emission_limit))
        SE.write(msg % (e, emission_limit))
        return Constraint.Skip
    
    return expr


def GrowthRateMaxConstraint_rule(M: 'TemoaModel', r, p, t):
    r"""

    This constraint sets an upper bound growth rate on technology-specific capacity.

    .. math::
       :label: GrowthRate

       CAPAVL_{r, p_{i},t} \le GRM \cdot CAPAVL_{r,p_{i-1},t} + GRS

       \\
       \forall \{r, p, t\} \in \Theta_{\text{GrowthRate}}

    where :math:`GRM` is the maximum growth rate, and should be specified as
    :math:`(1+r)` and :math:`GRS` is the growth rate seed, which has units of
    capacity. Without the seed, any technology with zero capacity in the first time
    period would be restricted to zero capacity for the remainder of the time
    horizon.
    """

    regions = gather_group_regions(M, r)

    GRS = value(M.GrowthRateSeed[r, t])
    GRM = value(M.GrowthRateMax[r, t])
    CapPT = M.V_CapacityAvailableByPeriodAndTech

    # periods the technology can have capacity in this region (sorted)
    periods = sorted(set(_p for _r, _p, _t in CapPT if _t == t and _r in regions))

    if p not in periods:
        # cant have capacity in this period
        return Constraint.Skip
    
    capacity = sum(CapPT[_r, p, t] for _r in regions)

    if p == periods[0]:
        # first period it can have capacity
        # plant a seed and grow it
        expr = capacity <= GRS * GRM
    else:
        # can have capacity in previous period
        # plant a seed and grow last period's capacity
        # note: we plant a seed every period to survive zero-outs
        p_prev = periods[periods.index(p) - 1] # previous period
        capacity_prev = sum(CapPT[_r, p_prev, t] for _r in regions)
        expr = capacity <= GRS + GRM * capacity_prev
        
    return expr


def MaxActivity_Constraint(M: 'TemoaModel', r, p, t):
    r"""

    The MaxActivity sets an upper bound on the activity from a specific technology.
    Note that the indices for these constraints are region, period and tech, not tech
    and vintage. The first version of the constraint pertains to technologies with
    variable output at the time slice level, and the second version pertains to
    technologies with constant annual output belonging to the :code:`tech_annual`
    set.

    .. math::
       :label: MaxActivity

       \sum_{S,D,I,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o}  \le MAA_{r, p, t}

       \forall \{r, p, t\} \in \Theta_{\text{MaxActivity}}

       \sum_{I,V,O} \textbf{FOA}_{r, p, i, t \in T^{a}, v, o}  \le MAA_{r, p, t}

       \forall \{r, p, t \in T^{a}\} \in \Theta_{\text{MaxActivity}}
    """
    # r can be an individual region (r='US'), or a combination of regions separated by
    # a + (r='Mexico+US+Canada'), or 'global'.
    # if r == 'global', the constraint is system-wide
    regions = gather_group_regions(M=M, region=r)

    if t not in M.tech_annual:
        activity_rpt = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, t, S_v, S_o) in M.V_FlowOut
        )
    else:
        activity_rpt = sum(
            M.V_FlowOutAnnual[_r, p, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            if (_r, p, S_i, t, S_v, S_o) in M.V_FlowOutAnnual
        )

    max_act = value(M.MaxActivity[r, p, t])
    expr = activity_rpt <= max_act
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        return Constraint.Skip
    return expr


def MaxSeasonalActivity_Constraint(M: 'TemoaModel', r, p, s, t):

    r"""
    The MaxSeasonalActivity sets an upper bound on the activity from a specific technology.
    Note that the indices for these constraints are region, period, season, and tech.
    The first component of the constraint pertains to technologies with
    variable output at the time slice level, and the second component pertains to
    technologies with constant annual output belonging to the :code:`tech_annual`
    set.
    .. math::
        :label: MaxSeasonalActivity
        \sum_{S,D,I,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o}  \le MAXSSNACT_{r, p, s, t}
        \forall \{r, p, s, t\} \in \Theta_{\text{MaxSeasonalActivity}}
        \sum_{I,V,O} \textbf{FOA}_{r, p, i, t, v, o}  \le MAXSSNACT_{r, p, s, t}
        \forall \{r, p, s, t \in T^{a}\} \in \Theta_{\text{MaxSeasonalActivity}}
    """

    # Notice that this constraint follows the implementation of the
    # MaxActivity_Constraint(). The difference is that this function is defined
    # over each representative day, or "season", as opposed to the entire
    # year, or "period".

    # The V_FlowOut variable is scaled by the weights of each representative day.
    # In order to determine the daily, or "seasonal", flow, the V_FLowOut variable
    # must be converted back to its un-scaled value. We do this by dividing the
    # V_FlowOut value by M.SegFrac[s, d]*365*24.

    regions = gather_group_regions(M, r)

    try:
        activity_rpst = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, S_o] / (value(M.SegFrac[s, d])*365*24)
            for _r in regions
            for S_v in M.processVintages[_r, p, t]
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            for d in M.time_of_day
        )
    except:
        msg = (
        "\nWarning: MaxSeasonalActivity constraint can not be defined for "
        "technologies in \"tech_annual\". Continuing by ignoring the constraint "
        "for '%s'.\n "
        )
        SE.write(msg % (t))
        return Constraint.Skip
    
    max_act = value(M.MaxSeasonalActivity[r, p, s, t])
    expr = activity_rpst <= max_act

    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        return Constraint.Skip
    
    return expr


def MinActivity_Constraint(M: 'TemoaModel', r, p, t):
    r"""

    The MinActivity sets a lower bound on the activity from a specific technology.
    Note that the indices for these constraints are region, period and tech, not tech and
    vintage. The first version of the constraint pertains to technologies with
    variable output at the time slice level, and the second version pertains to
    technologies with constant annual output belonging to the :code:`tech_annual`
    set.

    .. math::
       :label: MinActivity

       \sum_{S,D,I,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o} \ge MIA_{r, p, t}

       \forall \{r, p, t\} \in \Theta_{\text{MinActivity}}

       \sum_{I,V,O} \textbf{FOA}_{r, p, i, t, v, o} \ge MIA_{r, p, t}

       \forall \{r, p, t \in T^{a}\} \in \Theta_{\text{MinActivity}}
    """
    # r can be an individual region (r='US'), or a combination of regions separated by
    # a + (r='Mexico+US+Canada'), or 'global'.
    # if r == 'global', the constraint is system-wide
    regions = gather_group_regions(M, r)

    if t not in M.tech_annual:
        activity_rpt = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, t, S_v, S_o) in M.V_FlowOut
        )
    else:
        activity_rpt = sum(
            M.V_FlowOutAnnual[_r, p, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            if (_r, p, S_i, t, S_v, S_o) in M.V_FlowOutAnnual
        )

    min_act = value(M.MinActivity[r, p, t])
    expr = activity_rpt >= min_act
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        logger.error(
            'No elements available to support min-activity: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            t,
        )
        return Constraint.Skip
    return expr


def MinSeasonalActivity_Constraint(M: 'TemoaModel', r, p, s, t):

    r"""
    The MinSeasonalActivity sets a lower bound on the activity from a specific technology
    over a specific season. Note that the indices for these constraints are region,
    period, season and tech, not tech and vintage. The first version of the constraint
    pertains to technologies with variable output at the time slice level, and the
    second version pertains to technologies with constant annual output belonging to
    the :code:`tech_annual` set.
    .. math::
        :label: MinSeasonalActivity
        \sum_{S,D,I,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o} \ge MINSSNACT_{r, p, t}
        \forall \{r, p, s, t\} \in \Theta_{\text{MinSeasonalActivity}}
        \sum_{I,V,O} \textbf{FOA}_{r, p, s, i, t, v, o} \ge MINSSNACT_{r, p, s, t}
        \forall \{r, p, s, t \in T^{a}\} \in \Theta_{\text{MinSeasonalActivity}}
    """

    # Notice that this constraint follows the implementation of the
    # MinActivity_Constraint(). The difference is that this function is defined
    # over each representative day, or "season", as opposed to the entire
    # year, or "period".

    # The V_FlowOut variable is scaled by the weights of each representative day.
    # In order to determine the daily, or "seasonal", flow, the V_FLowOut variable
    # must be converted back to its un-scaled value. We do this using the
    # weighting_factor below:

    regions = gather_group_regions(M, r)

    try:
        activity_rpst = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, S_o] / (value(M.SegFrac[s, d])*365*24)
            for _r in regions
            for S_v in M.processVintages[_r, p, t]
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            for d in M.time_of_day
        )
    except:
        msg = (
        "\nWarning: MinSeasonalActivity constraint can not be defined for "
        "technologies in \"tech_annual\". Continuing by ignoring the constraint "
        "for '%s'.\n "
        )
        SE.write(msg % (t))
        return Constraint.Skip

    min_act = value(M.MinSeasonalActivity[r, p, s, t])
    expr = activity_rpst >= min_act

    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        return Constraint.Skip
    
    return expr


def MinActivityGroup_Constraint(M: 'TemoaModel', r, p, g):
    r"""

    The MinActivityGroup constraint sets a minimum activity limit for a user-defined
    technology group.

    .. math::
       :label: MinActivityGroup

           \sum_{R,S,D,I,T,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o} + \sum_{I,T,V,O}
           \textbf{FOA}_{r, p, i, t, v, o}
           \ge MnAG_{r, p, g}
           \forall \{r, p, g\} \in \Theta_{\text{MinActivityGroup}}

    where :math:`g` represents the assigned technology group and :math:`MnAG`
    refers to the :code:`MinActivityGroup` parameter."""

    regions = gather_group_regions(M, r)

    activity_p = 0
    activity_p_annual = 0
    for _r in regions:
        activity_p += sum(
            M.V_FlowOut[_r, p, s, d, S_i, S_t, S_v, S_o]
            for S_t in M.tech_group_members[g]
            if (_r, p, S_t) in M.processVintages and S_t not in M.tech_annual
            for S_v in M.processVintages[_r, p, S_t]
            for S_i in M.processInputs[_r, p, S_t, S_v]
            for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, S_t, S_v, S_o) in M.V_FlowOut
        )

        activity_p_annual += sum(
            M.V_FlowOutAnnual[_r, p, S_i, S_t, S_v, S_o]
            for S_t in M.tech_group_members[g]
            if (_r, p, S_t) in M.processVintages and S_t in M.tech_annual
            for S_v in M.processVintages[_r, p, S_t]
            for S_i in M.processInputs[_r, p, S_t, S_v]
            for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
            if (_r, p, S_i, S_t, S_v, S_o) in M.V_FlowOutAnnual
        )
    min_act = value(M.MinActivityGroup[r, p, g])
    expr = activity_p + activity_p_annual >= min_act
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        logger.error(
            'No elements available to support min-activity group: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            g,
        )
        return Constraint.Skip
    return expr


def MaxActivityGroup_Constraint(M: 'TemoaModel', r, p, g):
    r"""
    The MaxActivityGroup constraint sets a maximum activity limit for a user-defined
    technology group.
    .. math::
       :label: MaxActivityGroup
           \sum_{R,S,D,I,T,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o} + \sum_{I,T,V,O}
           \textbf{FOA}_{r, p, i, t, v, o}
           \le MxAG_{r, p, g}
           \forall \{r, p, g\} \in \Theta_{\text{MaxActivityGroup}}
    where :math:`g` represents the assigned technology group and :math:`MxAG`
    refers to the :code:`MaxActivityGroup` parameter."""

    regions = gather_group_regions(M, r)

    activity_p = 0
    activity_p_annual = 0
    for _r in regions:
        activity_p += sum(
            M.V_FlowOut[_r, p, s, d, S_i, S_t, S_v, S_o]
            for S_t in M.tech_group_members[g]
            if (_r, p, S_t) in M.processVintages and S_t not in M.tech_annual
            for S_v in M.processVintages[_r, p, S_t]
            for S_i in M.processInputs[_r, p, S_t, S_v]
            for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, S_t, S_v, S_o) in M.V_FlowOut
        )
        activity_p_annual += sum(
            M.V_FlowOutAnnual[_r, p, S_i, S_t, S_v, S_o]
            for S_t in M.tech_group_members[g]
            if (_r, p, S_t) in M.processVintages and S_t in M.tech_annual
            for S_v in M.processVintages[_r, p, S_t]
            for S_i in M.processInputs[_r, p, S_t, S_v]
            for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
            if (_r, p, S_i, S_t, S_v, S_o) in M.V_FlowOutAnnual
        )

    max_act = value(M.MaxActivityGroup[r, p, g])
    expr = activity_p + activity_p_annual <= max_act
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        return Constraint.Skip
    return expr


def MaxNewCapacity_Constraint(M: 'TemoaModel', r, p, t):
    r"""
    The MaxNewCapacity constraint sets a limit on the maximum newly installed capacity of a
    given technology in a given year. Note that the indices for these constraints are region,
    period and tech.
    .. math::
       :label: MaxNewCapacity
       \textbf{CAP}_{r, t, p} \le MAX_{r, p, t}"""
    regions = gather_group_regions(M, r)
    max_cap = value(M.MaxNewCapacity[r, p, t])
    new_cap = sum(
        M.V_NewCapacity[_r, t, p]
        for _r in regions
    )
    expr = new_cap <= max_cap
    return expr


def MaxCapacity_Constraint(M: 'TemoaModel', r, p, t):
    r"""

    The MaxCapacity constraint sets a limit on the maximum available capacity of a
    given technology. Note that the indices for these constraints are region, period and
    tech, not tech and vintage.

    .. math::
       :label: MaxCapacity

       \textbf{CAPAVL}_{r, p, t} \le MAC_{r, p, t}

       \forall \{r, p, t\} \in \Theta_{\text{MaxCapacity}}"""
    regions = gather_group_regions(M, r)
    max_cap = value(M.MaxCapacity[r, p, t])
    capacity = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, t]
        for _r in regions
    )
    expr = capacity <= max_cap
    return expr


def MaxResource_Constraint(M: 'TemoaModel', r, t):
    r"""

    The MaxResource constraint sets a limit on the maximum available resource of a
    given technology across all model time periods. Note that the indices for these
    constraints are region and tech.

    .. math::
       :label: MaxResource

       \sum_{P} \textbf{CAPAVL}_{r, p, t} \le MAR_{r, t}

       \forall \{r, t\} \in \Theta_{\text{MaxCapacity}}"""
    # logger.warning(
    #     'The MaxResource constraint is not currently supported in the model, pending review.  Recommend '
    #     'removing data from the MaxResource Table'
    # )
    # dev note:  this constraint is a misnomer.  It is actually a "global activity constraint on a tech"
    #            regardless of whatever "resources" are consumed.
    # dev note:  this would generally be applied to a "dummy import" technology to restrict something like
    #            oil/mineral extraction across all model periods. Looks fine to me.

    regions = gather_group_regions(M, r)

    if t in M.tech_annual:
        activity_rt = sum(
            M.V_FlowOutAnnual[_r, p, S_i, t, S_v, S_o]
            for p in M.time_optimize
            for _r in regions
            if (_r, p, t) in M.processVintages.keys()
            for S_v in M.processVintages[_r, p, t]
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
        )
    else:
        activity_rt = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, S_o]
            for p in M.time_optimize
            for _r in regions
            if (_r, p, t) in M.processVintages.keys()
            for S_v in M.processVintages[_r, p, t]
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            for s in M.time_season
            for d in M.time_of_day
        )
    
    max_resource = value(M.MaxResource[r, t])
    expr = activity_rt <= max_resource
    return expr


def MaxCapacityGroup_Constraint(M: 'TemoaModel', r, p, g):
    r"""
    Similar to the :code:`MaxCapacity` constraint, but works on a group of technologies.
    """
    regions = gather_group_regions(M, r)

    max_capgroup = value(M.MaxCapacityGroup[r, p, g])

    cap = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, t]
        for t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )

    expr = cap <= max_capgroup
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool): # an empty list was generated
        logger.error(
            'No elements available to support max-capacity group: %s.'
            ' Check data/log for available/suppressed techs. Constraint ignored.',
            (r, p, g)
        )
        return Constraint.Skip
    return expr


def MinNewCapacity_Constraint(M: 'TemoaModel', r, p, t):
    r"""
    The MinNewCapacity constraint sets a limit on the minimum newly installed capacity of a
    given technology in a given year. Note that the indices for these constraints are region,
    period, and tech.
    .. math::
       :label: MaxMinCapacity
       \textbf{CAP}_{r, t, p} \ge MIN_{r, p, t}"""
    regions = gather_group_regions(M, r)
    min_cap = value(M.MinNewCapacity[r, p, t])
    new_cap = sum(
        M.V_NewCapacity[_r, t, p]
        for _r in regions
    )
    expr = new_cap >= min_cap
    return expr


def MinCapacity_Constraint(M: 'TemoaModel', r, p, t):
    r"""

    The MinCapacity constraint sets a limit on the minimum available capacity of a
    given technology. Note that the indices for these constraints are region, period and
    tech, not tech and vintage.

    .. math::
       :label: MinCapacityCapacityAvailableByPeriodAndTech

       \textbf{CAPAVL}_{r, p, t} \ge MIC_{r, p, t}

       \forall \{r, p, t\} \in \Theta_{\text{MinCapacity}}"""
    regions = gather_group_regions(M, r)
    min_cap = value(M.MinCapacity[r, p, t])
    capacity = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, t]
        for _r in regions
    )
    expr = capacity >= min_cap
    return expr


def MinCapacityGroup_Constraint(M: 'TemoaModel', r, p, g):
    r"""
    Similar to the :code:`MinCapacity` constraint, but works on a group of technologies.
    """
    regions = gather_group_regions(M, r)

    min_capgroup = value(M.MinCapacityGroup[r, p, g])

    cap = sum(
        M.V_CapacityAvailableByPeriodAndTech[r_i, p, t]
        for t in M.tech_group_members[g]
        for r_i in regions
        if (r_i, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )

    expr = cap >= min_capgroup
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        logger.error(
            'No elements available to support min-capacity group: %s.'
            ' Check data/log for available/suppressed techs. Constraint ignored.',
            (r, p, g)
        )
        return Constraint.Skip
    return expr


def MinNewCapacityGroup_Constraint(M: 'TemoaModel', r, p, g):
    r"""
    Similar to the :code:`MinNewCapacity` constraint, but works on a group of technologies."""

    regions = gather_group_regions(M, r)

    min_new_cap = value(M.MinNewCapacityGroup[r, p, g])
    agg_new_cap = sum(
        M.V_NewCapacity[_r, t, p]
        for t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )
    expr = agg_new_cap >= min_new_cap
    if isinstance(expr, bool):
        logger.error(
            'No elements available to support min new capacity group: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            g,
        )
        return Constraint.Skip
    return expr


def MaxNewCapacityGroup_Constraint(M: 'TemoaModel', r, p, g):
    r"""
    Similar to the :code:`MinNewCapacity` constraint, but works on a group of technologies."""

    regions = gather_group_regions(M, r)

    max_new_cap = value(M.MaxNewCapacityGroup[r, p, g])
    agg_new_cap = sum(
        M.V_NewCapacity[_r, t, p]
        for t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )
    expr = max_new_cap >= agg_new_cap
    if isinstance(expr, bool):
        logger.error(
            'No elements available to support max new capacity group: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            g,
        )
        return Constraint.Skip
    return expr


def MinActivityShare_Constraint(M: 'TemoaModel', r, p, t, g):
    r"""
    The MinActivityShare constraint sets a minimum capacity share for a given
    technology within a technology groups to which it belongs.
    For instance, you might define a tech_group of light-duty vehicles, whose
    members are different types for LDVs. This constraint could be used to enforce
    that no less than 10% of LDVs must be of a certain type."""

    regions = gather_group_regions(M, r)

    if t not in M.tech_annual:
        activity_tech = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, t, S_v, S_o) in M.V_FlowOut
        )
    else:
        activity_tech = sum(
            M.V_FlowOutAnnual[_r, p, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            if (_r, p, S_i, t, S_v, S_o) in M.V_FlowOutAnnual
        )

    activity_group = sum(
        M.V_FlowOut[_r, p, s, d, S_i, S_t, S_v, S_o]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, S_t) in M.processVintages and S_t not in M.tech_annual
        for S_v in M.processVintages[_r, p, S_t]
        for S_i in M.processInputs[_r, p, S_t, S_v]
        for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
        for s in M.time_season
        for d in M.time_of_day
        if (_r, p, s, d, S_i, S_t, S_v, S_o) in M.V_FlowOut
    )
    activity_group_annual = sum(
        M.V_FlowOutAnnual[_r, p, S_i, S_t, S_v, S_o]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, S_t) in M.processVintages and S_t in M.tech_annual
        for S_v in M.processVintages[_r, p, S_t]
        for S_i in M.processInputs[_r, p, S_t, S_v]
        for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
        if (_r, p, S_i, S_t, S_v, S_o) in M.V_FlowOutAnnual
    )
    activity_group = activity_group + activity_group_annual

    min_activity_share = value(M.MinActivityShare[r, p, t, g])
    expr = activity_tech >= min_activity_share * activity_group
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        logger.error(
            'No elements available to support min-activity share group: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            g,
        )
        return Constraint.Skip
    return expr


def MaxActivityShare_Constraint(M: 'TemoaModel', r, p, t, g):
    r"""
    The MaxActivityShare constraint sets a maximum Activity share for a given
    technology within a technology groups to which it belongs.
    For instance, you might define a tech_group of light-duty vehicles, whose
    members are different types for LDVs. This constraint could be used to enforce
    that no more than 10% of LDVs must be of a certain type."""

    regions = gather_group_regions(M, r)

    if t not in M.tech_annual:
        activity_tech = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, t, S_v, S_o) in M.V_FlowOut
        )
    else:
        activity_tech = sum(
            M.V_FlowOutAnnual[_r, p, S_i, t, S_v, S_o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for S_o in M.processOutputsByInput[_r, p, t, S_v, S_i]
            if (_r, p, S_i, t, S_v, S_o) in M.V_FlowOutAnnual
        )

    activity_group = sum(
        M.V_FlowOut[_r, p, s, d, S_i, S_t, S_v, S_o]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, S_t) in M.processVintages and S_t not in M.tech_annual
        for S_v in M.processVintages[_r, p, S_t]
        for S_i in M.processInputs[_r, p, S_t, S_v]
        for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
        for s in M.time_season
        for d in M.time_of_day
        if (_r, p, s, d, S_i, S_t, S_v, S_o) in M.V_FlowOut
    )
    activity_group_annual = sum(
        M.V_FlowOutAnnual[_r, p, S_i, S_t, S_v, S_o]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, S_t) in M.processVintages and S_t in M.tech_annual
        for S_v in M.processVintages[_r, p, S_t]
        for S_i in M.processInputs[_r, p, S_t, S_v]
        for S_o in M.processOutputsByInput[_r, p, S_t, S_v, S_i]
        if (_r, p, S_i, S_t, S_v, S_o) in M.V_FlowOutAnnual
    )
    activity_group = activity_group + activity_group_annual

    max_activity_share = value(M.MaxActivityShare[r, p, t, g])
    expr = activity_tech <= max_activity_share * activity_group
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        return Constraint.Skip
    logger.debug(
        'created max activity constraint for (%s, %d, %s, %s) of %0.2f',
        (r, p, t, g, max_activity_share),
    )
    return expr


def MinCapacityShare_Constraint(M: 'TemoaModel', r, p, t, g):
    r"""
    The MinCapacityShare constraint sets a minimum capacity share for a given
    technology within a technology groups to which it belongs.
    For instance, you might define a tech_group of light-duty vehicles, whose
    members are different types for LDVs. This constraint could be used to enforce
    that no less than 10% of LDVs must be of a certain type."""

    regions = gather_group_regions(M, r)

    capacity_t = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, t]
        for _r in regions
    )
    capacity_group = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, S_t]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, S_t) in M.processVintages.keys()
    )
    min_cap_share = value(M.MinCapacityShare[r, p, t, g])

    expr = capacity_t >= min_cap_share * capacity_group
    if isinstance(expr, bool):
        logger.error(
            'No elements available to support min-capacity share: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            g,
        )
        return Constraint.Skip
    return expr


def MaxCapacityShare_Constraint(M: 'TemoaModel', r, p, t, g):
    r"""
    The MaxCapacityShare constraint sets a maximum capacity share for a given
    technology within a technology groups to which it belongs.
    For instance, you might define a tech_group of light-duty vehicles, whose
    members are different types for LDVs. This constraint could be used to enforce
    that no more than 10% of LDVs must be of a certain type."""

    regions = gather_group_regions(M, r)

    capacity_t = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, t]
        for _r in regions
    )
    capacity_group = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, S_t]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, p, S_t) in M.processVintages.keys()
    )
    max_cap_share = value(M.MaxCapacityShare[r, p, t, g])

    expr = capacity_t <= max_cap_share * capacity_group
    if isinstance(expr, bool):
        return Constraint.Skip
    return expr


def MinNewCapacityShare_Constraint(M: 'TemoaModel', r, p, t, g):
    r"""
    The MinNewCapacityShare constraint sets a minimum new capacity share for a given
    technology within a technology groups to which it belongs.
    For instance, you might define a tech_group of light-duty vehicles, whose
    members are different types for LDVs. This constraint could be used to enforce
    that no less than 10% of new LDV purchases in a given year must be of a certain type."""

    regions = gather_group_regions(M, r)

    capacity_t = sum(
        M.V_NewCapacity[_r, t, p]
        for _r in regions
    )
    capacity_group = sum(
        M.V_NewCapacity[_r, S_t, p]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, S_t, p) in M.V_NewCapacity.keys()
    )
    min_cap_share = value(M.MinNewCapacityShare[r, p, t, g])

    expr = capacity_t >= min_cap_share * capacity_group
    if isinstance(expr, bool):
        logger.error(
            'No elements available to support min-new capacity share: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            g,
        )
        return Constraint.Skip
    return expr


def MaxNewCapacityShare_Constraint(M: 'TemoaModel', r, p, t, g):
    r"""
    The MaxCapacityShare constraint sets a maximum new capacity share for a given
    technology within a technology groups to which it belongs.
    For instance, you might define a tech_group of light-duty vehicles, whose
    members are different types for LDVs. This constraint could be used to enforce
    that no more than 10% of LDV purchases in a given year must be of a certain type."""

    regions = gather_group_regions(M, r)

    capacity_t = sum(
        M.V_NewCapacity[_r, t, p]
        for _r in regions
    )
    capacity_group = sum(
        M.V_NewCapacity[_r, S_t, p]
        for S_t in M.tech_group_members[g]
        for _r in regions
        if (_r, S_t, p) in M.V_NewCapacity.keys()
    )
    max_cap_share = value(M.MaxNewCapacityShare[r, p, t, g])

    expr = capacity_t <= max_cap_share * capacity_group
    if isinstance(expr, bool):
        return Constraint.Skip
    return expr


def MinNewCapacityGroupShare_Constraint(M: 'TemoaModel', r, p, g1, g2):
    r"""
    Sets the minimum aggregate capacity of one group of technologies as a share of 
    another group of technologies.
    """

    regions = gather_group_regions(M, r)

    min_share = value(M.MinNewCapacityGroupShare[r, p, g1, g2])
    agg_new_cap_g1 = sum(
        M.V_NewCapacity[_r, t, p]
        for t in M.tech_group_members[g1]
        for _r in regions
        if (_r, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )
    agg_new_cap_g2 = sum(
        M.V_NewCapacity[_r, t, p]
        for t in M.tech_group_members[g2]
        for _r in regions
        if (_r, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )
    expr = agg_new_cap_g1 >= agg_new_cap_g2 * min_share

    if isinstance(expr, bool): # one side of expression was empty
        logger.error(
            'Missing group techs to support min new capacity group share constraint: %s.'
            '  Check data/log for available/suppressed techs. Constraint ignored.',
            (r, p, g1, g2)
        )
        return Constraint.Skip
    
    return expr


def MaxNewCapacityGroupShare_Constraint(M: 'TemoaModel', r, p, g1, g2):
    r"""
    Sets the maximum aggregate capacity of one group of technologies as a share of 
    another group of technologies.
    """

    regions = gather_group_regions(M, r)

    max_share = value(M.MaxNewCapacityGroupShare[r, p, g1, g2])
    agg_new_cap_g1 = sum(
        M.V_NewCapacity[_r, t, p]
        for t in M.tech_group_members[g1]
        for _r in regions
        if (_r, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )
    agg_new_cap_g2 = sum(
        M.V_NewCapacity[_r, t, p]
        for t in M.tech_group_members[g2]
        for _r in regions
        if (_r, p, t) in M.V_CapacityAvailableByPeriodAndTech
    )
    expr = agg_new_cap_g1 <= agg_new_cap_g2 * max_share

    if isinstance(expr, bool): # one side of expression was empty
        logger.error(
            'Missing group techs to support max new capacity group share constraint: %s.'
            '  Check data/log for available/suppressed techs. Constraint ignored.',
            (r, p, g1, g2)
        )
        return Constraint.Skip

    return expr


def MinAnnualCapacityFactor_Constraint(M: 'TemoaModel', r, p, t, o):
    r"""
    The MinAnnualCapacityFactor sets a lower bound on the annual capacity factor
    from a specific technology. The first portion of the constraint pertains to
    technologies with variable output at the time slice level, and the second portion
    pertains to technologies with constant annual output belonging to the
    :code:`tech_annual` set.
    .. math::
       :label: MinAnnualCapacityFactor
       \sum_{S,D,I,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o} \ge MINCF_{r, p, t} * \textbf{CAPAVL}_{r, p, t} * \text{C2A}_{r, t}
       \forall \{r, p, t, o\} \in \Theta_{\text{MinAnnualCapacityFactor}}
       \sum_{I,V,O} \textbf{FOA}_{r, p, i, t, v, o} \ge MINCF_{r, p, t} * \textbf{CAPAVL}_{r, p, t} * \text{C2A}_{r, t}
       \forall \{r, p, t, o \in T^{a}\} \in \Theta_{\text{MinAnnualCapacityFactor}}"""
    # r can be an individual region (r='US'), or a combination of regions separated by plus (r='Mexico+US+Canada'), or 'global'.
    # if r == 'global', the constraint is system-wide
    regions = gather_group_regions(M, r)
    # we need to screen here because it is possible that the restriction extends beyond the
    # lifetime of any vintage of the tech...
    if all(
        (_r, p, t) not in M.V_CapacityAvailableByPeriodAndTech
        for _r in regions
    ):
        return Constraint.Skip

    if t not in M.tech_annual:
        activity_rpt = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, t, S_v, o) in M.V_FlowOut
        )
    else:
        activity_rpt = sum(
            M.V_FlowOutAnnual[_r, p, S_i, t, S_v, o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            if (_r, p, S_i, t, S_v, o) in M.V_FlowOutAnnual
        )

    max_possible_activity_rpt = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, t] * value(M.CapacityToActivity[_r, t])
        for _r in regions
    )
    min_annual_cf = value(M.MinAnnualCapacityFactor[r, p, t, o])
    expr = activity_rpt >= min_annual_cf * max_possible_activity_rpt
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        logger.error(
            'No elements available to support min-annual capacity factor: (%s, %d, %s).'
            '  Check data/log for available/suppressed techs.  Requirement IGNORED.',
            r,
            p,
            t,
        )
        return Constraint.Skip
    return expr


def MaxAnnualCapacityFactor_Constraint(M: 'TemoaModel', r, p, t, o):
    r"""
    The MaxAnnualCapacityFactor sets an upper bound on the annual capacity factor
    from a specific technology. The first portion of the constraint pertains to
    technologies with variable output at the time slice level, and the second portion
    pertains to technologies with constant annual output belonging to the
    :code:`tech_annual` set.
    .. math::
       :label: MaxAnnualCapacityFactor
       \sum_{S,D,I,V,O} \textbf{FO}_{r, p, s, d, i, t, v, o} \le MAXCF_{r, p, t} * \textbf{CAPAVL}_{r, p, t} * \text{C2A}_{r, t}
       \forall \{r, p, t, o\} \in \Theta_{\text{MaxAnnualCapacityFactor}}
       \sum_{I,V,O} \textbf{FOA}_{r, p, i, t, v, o} \ge MAXCF_{r, p, t} * \textbf{CAPAVL}_{r, p, t} * \text{C2A}_{r, t}
       \forall \{r, p, t, o \in T^{a}\} \in \Theta_{\text{MaxAnnualCapacityFactor}}"""
    # r can be an individual region (r='US'), or a combination of regions separated by plus (r='Mexico+US+Canada'), or 'global'.
    # if r == 'global', the constraint is system-wide
    regions = gather_group_regions(M, r)
    # we need to screen here because it is possible that the restriction extends beyond the
    # lifetime of any vintage of the tech...
    if all(
        (_r, p, t) not in M.V_CapacityAvailableByPeriodAndTech
        for _r in regions
    ):
        return Constraint.Skip

    if t not in M.tech_annual:
        activity_rpt = sum(
            M.V_FlowOut[_r, p, s, d, S_i, t, S_v, o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            for s in M.time_season
            for d in M.time_of_day
            if (_r, p, s, d, S_i, t, S_v, o) in M.V_FlowOut
        )
    else:
        activity_rpt = sum(
            M.V_FlowOutAnnual[_r, p, S_i, t, S_v, o]
            for _r in regions
            for S_v in M.processVintages.get((_r, p, t), [])
            for S_i in M.processInputs[_r, p, t, S_v]
            if (_r, p, S_i, t, S_v, o) in M.V_FlowOutAnnual
        )

    max_possible_activity_rpt = sum(
        M.V_CapacityAvailableByPeriodAndTech[_r, p, t] * value(M.CapacityToActivity[_r, t])
        for _r in regions
    )
    max_annual_cf = value(M.MaxAnnualCapacityFactor[r, p, t, o])
    expr = activity_rpt <= max_annual_cf * max_possible_activity_rpt
    # in the case that there is nothing to sum, skip
    if isinstance(expr, bool):  # an empty list was generated
        return Constraint.Skip
    return expr


def MinTechInputSplit_Constraint(M: 'TemoaModel', r, p, s, d, i, t, v):
    r"""
    Allows users to specify fixed or minimum shares of commodity inputs to a process
    producing a single output. These shares can vary by model time period. See
    MinTechOutputSplit_Constraint for an analogous explanation. Under this constraint,
    only the technologies with variable output at the timeslice level (i.e.,
    NOT in the :code:`tech_annual` set) are considered."""
    inp = sum(
        M.V_FlowOut[r, p, s, d, i, t, v, S_o] / get_variable_efficiency(M, r, p, s, d, i, t, v, S_o)
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    total_inp = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o] / get_variable_efficiency(M, r, p, s, d, S_i, t, v, S_o)
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = inp >= value(M.MinTechInputSplit[r, p, i, t]) * total_inp
    return expr


def MinTechInputSplitAnnual_Constraint(M: 'TemoaModel', r, p, i, t, v):
    r"""
    Allows users to specify fixed or minimum shares of commodity inputs to a process
    producing a single output. These shares can vary by model time period. See
    MinTechOutputSplitAnnual_Constraint for an analogous explanation. Under this
    function, only the technologies with constant annual output (i.e., members
    of the :math:`tech_annual` set) are considered."""
    inp = sum(
        M.V_FlowOutAnnual[r, p, i, t, v, S_o] / value(M.Efficiency[r, i, t, v, S_o])
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    total_inp = sum(
        M.V_FlowOutAnnual[r, p, S_i, t, v, S_o] / value(M.Efficiency[r, S_i, t, v, S_o])
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = inp >= value(M.MinTechInputSplitAnnual[r, p, i, t]) * total_inp
    return expr


def MinTechInputSplitAverage_Constraint(M: 'TemoaModel', r, p, i, t, v):
    r"""
    Allows users to specify fixed or minimum shares of commodity inputs to a process
    producing a single output. Under this constraint, only the technologies with variable
    output at the timeslice level (i.e., NOT in the :code:`tech_annual` set) are considered.
    This constraint differs from MinTechInputSplit as it specifies shares on an annual basis,
    so even though it applies to technologies with variable output at the timeslice level,
    the constraint only fixes the input shares over the course of a year."""

    inp = sum(
        M.V_FlowOut[r, p, S_s, S_d, i, t, v, S_o] / get_variable_efficiency(M, r, p, S_s, S_d, i, t, v, S_o)
        for S_s in M.time_season
        for S_d in M.time_of_day
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    total_inp = sum(
        M.V_FlowOut[r, p, S_s, S_d, S_i, t, v, S_o] / get_variable_efficiency(M, r, p, S_s, S_d, i, t, v, S_o)
        for S_s in M.time_season
        for S_d in M.time_of_day
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    expr = inp >= value(M.MinTechInputSplitAnnual[r, p, i, t]) * total_inp
    return expr


def MinTechOutputSplit_Constraint(M: 'TemoaModel', r, p, s, d, t, v, o):
    r"""

    Some processes take a single input and make multiple outputs, and the user would like to
    specify either a constant or time-varying ratio of outputs per unit input.  The most
    canonical example is an oil refinery.  Crude oil is used to produce many different refined
    products. In many cases, the modeler would like to specify a minimum share of each refined
    product produced by the refinery.

    For example, a hypothetical (and highly simplified) refinery might have a crude oil input
    that produces 4 parts diesel, 3 parts gasoline, and 2 parts kerosene.  The relative
    ratios to the output then are:

    .. math::

       d = \tfrac{4}{9} \cdot \text{total output}, \qquad
       g = \tfrac{3}{9} \cdot \text{total output}, \qquad
       k = \tfrac{2}{9} \cdot \text{total output}

    Note that it is possible to specify output shares that sum to less than unity. In such
    cases, the model optimizes the remaining share. In addition, it is possible to change the
    specified shares by model time period. Under this constraint, only the
    technologies with variable output at the timeslice level (i.e., NOT in the
    :code:`tech_annual` set) are considered.

    The constraint is formulated as follows:

    .. math::
       :label: MinTechOutputSplit

         \sum_{I, t \not \in T^{a}} \textbf{FO}_{r, p, s, d, i, t, v, o}
       \geq
         TOS_{r, p, t, o} \cdot \sum_{I, O, t \not \in T^{a}} \textbf{FO}_{r, p, s, d, i, t, v, o}

       \forall \{r, p, s, d, t, v, o\} \in \Theta_{\text{MinTechOutputSplit}}"""
    out = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, o]
        for S_i in M.processInputsByOutput[r, p, t, v, o]
    )

    total_out = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = out >= value(M.MinTechOutputSplit[r, p, t, o]) * total_out
    return expr


def MinTechOutputSplitAnnual_Constraint(M: 'TemoaModel', r, p, t, v, o):
    r"""
    This constraint operates similarly to MinTechOutputSplit_Constraint.
    However, under this function, only the technologies with constant annual
    output (i.e., members of the :math:`tech_annual` set) are considered.

    .. math::
       :label: MinTechOutputSplitAnnual

         \sum_{I, T^{a}} \textbf{FOA}_{r, p, i, t \in T^{a}, v, o}

       \geq

         TOS_{r, p, t, o} \cdot \sum_{I, O, T^{a}} \textbf{FOA}_{r, p, s, d, i, t \in T^{a}, v, o}

       \forall \{r, p, t \in T^{a}, v, o\} \in \Theta_{\text{MinTechOutputSplitAnnual}}"""
    out = sum(
        M.V_FlowOutAnnual[r, p, S_i, t, v, o]
        for S_i in M.processInputsByOutput[r, p, t, v, o]
    )

    total_out = sum(
        M.V_FlowOutAnnual[r, p, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = out >= value(M.MinTechOutputSplitAnnual[r, p, t, o]) * total_out
    return expr


def MinTechOutputSplitAverage_Constraint(M: 'TemoaModel', r, p, t, v, o):
    r"""
    Allows users to specify fixed or minimum shares of commodity outputs from a process.
    Under this constraint, only the technologies with variable
    output at the timeslice level (i.e., NOT in the :code:`tech_annual` set) are considered.
    This constraint differs from MinTechOutputSplit as it specifies shares on an annual basis,
    so even though it applies to technologies with variable output at the timeslice level,
    the constraint only fixes the output shares over the course of a year."""

    out = sum(
        M.V_FlowOut[r, p, S_s, S_d, S_i, t, v, o]
        for S_i in M.processInputsByOutput[r, p, t, v, o]
        for S_s in M.time_season
        for S_d in M.time_of_day
    )

    total_out = sum(
        M.V_FlowOut[r, p, S_s, S_d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
        for S_s in M.time_season
        for S_d in M.time_of_day
    )

    expr = out >= value(M.MinTechOutputSplitAnnual[r, p, t, o]) * total_out
    return expr


def MaxTechInputSplit_Constraint(M: 'TemoaModel', r, p, s, d, i, t, v):
    r"""
    Allows users to specify fixed or minimum shares of commodity inputs to a process
    producing a single output. These shares can vary by model time period. See
    MaxTechOutputSplit_Constraint for an analogous explanation. Under this constraint,
    only the technologies with variable output at the timeslice level (i.e.,
    NOT in the :code:`tech_annual` set) are considered."""
    inp = sum(
        M.V_FlowOut[r, p, s, d, i, t, v, S_o] / get_variable_efficiency(M, r, p, s, d, i, t, v, S_o)
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    total_inp = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o] / get_variable_efficiency(M, r, p, s, d, S_i, t, v, S_o)
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = inp <= value(M.MaxTechInputSplit[r, p, i, t]) * total_inp
    return expr


def MaxTechInputSplitAnnual_Constraint(M: 'TemoaModel', r, p, i, t, v):
    r"""
    Allows users to specify fixed or minimum shares of commodity inputs to a process
    producing a single output. These shares can vary by model time period. See
    MaxTechOutputSplitAnnual_Constraint for an analogous explanation. Under this
    function, only the technologies with constant annual output (i.e., members
    of the :math:`tech_annual` set) are considered."""
    inp = sum(
        M.V_FlowOutAnnual[r, p, i, t, v, S_o] / value(M.Efficiency[r, i, t, v, S_o])
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    total_inp = sum(
        M.V_FlowOutAnnual[r, p, S_i, t, v, S_o] / value(M.Efficiency[r, S_i, t, v, S_o])
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = inp <= value(M.MaxTechInputSplitAnnual[r, p, i, t]) * total_inp
    return expr


def MaxTechInputSplitAverage_Constraint(M: 'TemoaModel', r, p, i, t, v):
    r"""
    Allows users to specify fixed or minimum shares of commodity inputs to a process
    producing a single output. Under this constraint, only the technologies with variable
    output at the timeslice level (i.e., NOT in the :code:`tech_annual` set) are considered.
    This constraint differs from MaxTechInputSplit as it specifies shares on an annual basis,
    so even though it applies to technologies with variable output at the timeslice level,
    the constraint only fixes the input shares over the course of a year."""

    inp = sum(
        M.V_FlowOut[r, p, S_s, S_d, i, t, v, S_o] / get_variable_efficiency(M, r, p, S_s, S_d, i, t, v, S_o)
        for S_s in M.time_season
        for S_d in M.time_of_day
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    total_inp = sum(
        M.V_FlowOut[r, p, S_s, S_d, S_i, t, v, S_o] / get_variable_efficiency(M, r, p, S_s, S_d, i, t, v, S_o)
        for S_s in M.time_season
        for S_d in M.time_of_day
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, i]
    )

    expr = inp <= value(M.MaxTechInputSplitAnnual[r, p, i, t]) * total_inp
    return expr


def MaxTechOutputSplit_Constraint(M: 'TemoaModel', r, p, s, d, t, v, o):
    r"""

    Some processes take a single input and make multiple outputs, and the user would like to
    specify either a constant or time-varying ratio of outputs per unit input.  The most
    canonical example is an oil refinery.  Crude oil is used to produce many different refined
    products. In many cases, the modeler would like to specify a minimum share of each refined
    product produced by the refinery.

    For example, a hypothetical (and highly simplified) refinery might have a crude oil input
    that produces 4 parts diesel, 3 parts gasoline, and 2 parts kerosene.  The relative
    ratios to the output then are:

    .. math::

       d = \tfrac{4}{9} \cdot \text{total output}, \qquad
       g = \tfrac{3}{9} \cdot \text{total output}, \qquad
       k = \tfrac{2}{9} \cdot \text{total output}

    Note that it is possible to specify output shares that sum to less than unity. In such
    cases, the model optimizes the remaining share. In addition, it is possible to change the
    specified shares by model time period. Under this constraint, only the
    technologies with variable output at the timeslice level (i.e., NOT in the
    :code:`tech_annual` set) are considered.

    The constraint is formulated as follows:

    .. math::
       :label: MaxTechOutputSplit

         \sum_{I, t \not \in T^{a}} \textbf{FO}_{r, p, s, d, i, t, v, o}
       \geq
         TOS_{r, p, t, o} \cdot \sum_{I, O, t \not \in T^{a}} \textbf{FO}_{r, p, s, d, i, t, v, o}

       \forall \{r, p, s, d, t, v, o\} \in \Theta_{\text{MaxTechOutputSplit}}"""
    out = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, o]
        for S_i in M.processInputsByOutput[r, p, t, v, o]
    )

    total_out = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = out <= value(M.MaxTechOutputSplit[r, p, t, o]) * total_out
    return expr


def MaxTechOutputSplitAnnual_Constraint(M: 'TemoaModel', r, p, t, v, o):
    r"""
    This constraint operates similarly to MaxTechOutputSplit_Constraint.
    However, under this function, only the technologies with constant annual
    output (i.e., members of the :math:`tech_annual` set) are considered.

    .. math::
       :label: MaxTechOutputSplitAnnual

         \sum_{I, T^{a}} \textbf{FOA}_{r, p, i, t \in T^{a}, v, o}

       \geq

         TOS_{r, p, t, o} \cdot \sum_{I, O, T^{a}} \textbf{FOA}_{r, p, s, d, i, t \in T^{a}, v, o}

       \forall \{r, p, t \in T^{a}, v, o\} \in \Theta_{\text{MaxTechOutputSplitAnnual}}"""
    out = sum(
        M.V_FlowOutAnnual[r, p, S_i, t, v, o]
        for S_i in M.processInputsByOutput[r, p, t, v, o]
    )

    total_out = sum(
        M.V_FlowOutAnnual[r, p, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = out <= value(M.MaxTechOutputSplitAnnual[r, p, t, o]) * total_out
    return expr


def MaxTechOutputSplitAverage_Constraint(M: 'TemoaModel', r, p, t, v, o):
    r"""
    Allows users to specify fixed or minimum shares of commodity outputs from a process.
    Under this constraint, only the technologies with variable
    output at the timeslice level (i.e., NOT in the :code:`tech_annual` set) are considered.
    This constraint differs from MaxTechOutputSplit as it specifies shares on an annual basis,
    so even though it applies to technologies with variable output at the timeslice level,
    the constraint only fixes the output shares over the course of a year."""

    out = sum(
        M.V_FlowOut[r, p, S_s, S_d, S_i, t, v, o]
        for S_i in M.processInputsByOutput[r, p, t, v, o]
        for S_s in M.time_season
        for S_d in M.time_of_day
    )

    total_out = sum(
        M.V_FlowOut[r, p, S_s, S_d, S_i, t, v, S_o]
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
        for S_s in M.time_season
        for S_d in M.time_of_day
    )

    expr = out <= value(M.MaxTechOutputSplitAnnual[r, p, t, o]) * total_out
    return expr


def RenewablePortfolioStandard_Constraint(M: 'TemoaModel', r, p, g):
    r"""
    Allows users to specify the share of electricity generation in a region
    coming from RPS-eligible technologies."""

    inp = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for t in M.tech_group_members[g]
        for (_t, v) in M.processReservePeriods[r, p]
        if _t == t
        for s in M.time_season
        for d in M.time_of_day
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    total_inp = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o]
        for (t, v) in M.processReservePeriods[r, p]
        for s in M.time_season
        for d in M.time_of_day
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    expr = inp >= (value(M.RenewablePortfolioStandard[r, p, g]) * total_inp)
    return expr


# ---------------------------------------------------------------
# Define rule-based parameters
# ---------------------------------------------------------------
def ParamModelProcessLife_rule(M: 'TemoaModel', r, p, t, v):
    life_length = value(M.LifetimeProcess[r, t, v])
    tpl = min(v + life_length - p, value(M.PeriodLength[p]))

    return tpl


def ParamPeriodLength(M: 'TemoaModel', p):
    # This specifically does not use time_optimize because this function is
    # called /over/ time_optimize.
    periods = sorted(M.time_future)

    i = periods.index(p)

    # The +1 won't fail, because this rule is called over time_optimize, which
    # lacks the last period in time_future.
    length = periods[i + 1] - periods[i]

    return length


def ParamProcessLifeFraction_rule(M: 'TemoaModel', r, p, t, v):
    r"""

    Calculate the fraction of period p that process :math:`<t, v>` operates.

    For most processes and periods, this will likely be one, but for any process
    that will cease operation (rust out, be decommissioned, etc.) between periods,
    calculate the fraction of the period that the technology is able to
    create useful output.
    """
    eol_year = v + value(M.LifetimeProcess[r, t, v])
    frac = eol_year - p
    period_length = value(M.PeriodLength[p])
    if frac >= period_length:
        # try to avoid floating point round-off errors for the common case.
        return 1

        # number of years into final period loan is complete

    frac /= float(period_length)
    return frac


def loan_annualization_rate(loan_rate: float | None, loan_life: int | float) -> float:
    """
    This calculation is broken out specifically so that it can be used for param creation
    and separately to calculate loan costs rather than rely on fully-built model parameters
    :param loan_rate:
    :param loan_life:

    """
    if not loan_rate:
        # dev note:  this should not be needed as the LoanRate param has a default (see the definition)
        return 1.0 / loan_life
    annualized_rate = loan_rate / (1.0 - (1.0 + loan_rate) ** (-loan_life))
    return annualized_rate


def ParamLoanAnnualize_rule(M: 'TemoaModel', r, t, v):
    dr = value(M.LoanRate[r, t, v])
    lln = value(M.LoanLifetimeProcess[r, t, v])
    annualized_rate = loan_annualization_rate(dr, lln)
    return annualized_rate


def SegFracPerSeason_rule(M: 'TemoaModel', s):
    return sum(value(M.SegFrac[s, S_d]) for S_d in M.time_of_day)


def LinkedEmissionsTech_Constraint(M: 'TemoaModel', r, p, s, d, t, v, e):
    r"""
    This constraint is necessary for carbon capture technologies that produce
    CO2 as an emissions commodity, but the CO2 also serves as a physical
    input commodity to a downstream process, such as synthetic fuel production.
    To accomplish this, a dummy technology is linked to the CO2-producing
    technology, converting the emissions activity into a physical commodity
    amount as follows:

    .. math::
       :label: LinkedEmissionsTech

         - \sum_{I, O} \textbf{FO}_{r, p, s, d, i, t, v, o} \cdot EAC_{r, e, i, t, v, o}
         = \sum_{I, O} \textbf{FO}_{r, p, s, d, i, t, v, o}

        \forall \{r, p, s, d, t, v, e\} \in \Theta_{\text{LinkedTechs}}

    The relationship between the primary and linked technologies is given
    in the :code:`LinkedTechs` table. Note that the primary and linked
    technologies cannot be part of the :code:`tech_annual` set. It is implicit that
    the primary region corresponds to the linked technology as well. The lifetimes
    of the primary and linked technologies should be specified and identical.
    """
    linked_t = M.LinkedTechs[r, t, e]

    primary_flow = sum(
        M.V_FlowOut[r, p, s, d, S_i, t, v, S_o] * value(M.EmissionActivity[r, e, S_i, t, v, S_o])
        for S_i in M.processInputs[r, p, t, v]
        for S_o in M.processOutputsByInput[r, p, t, v, S_i]
    )

    linked_flow = sum(
        M.V_FlowOut[r, p, s, d, S_i, linked_t, v, S_o]
        for S_i in M.processInputs[r, p, linked_t, v]
        for S_o in M.processOutputsByInput[r, p, linked_t, v, S_i]
    )

    return -primary_flow == linked_flow


# To avoid building big many-indexed parameters when they aren't needed - saves memory
# Much faster to build a dictionary and check that than check the parameter
# indices directly every time - saves build time
def get_demand_distribution(M: 'TemoaModel', r, p, s, d, dem):
    if M.demandPeriodDistributions[(r, p, dem)]:
        return value(M.DemandPeriodDistribution[r, p, s, d, dem])
    else:
        return value(M.DemandSpecificDistribution[r, s, d, dem])

def get_variable_efficiency(M: 'TemoaModel', r, p, s, d, i, t, v, o):
    if M.variableEfficiencies[(r, p, s, d, i, t, v, o)]:
        return value(M.Efficiency[r, i, t, v, o]) * value(M.EfficiencyVariable[r, p, s, d, i, t, v, o])
    else:
        return value(M.Efficiency[r, i, t, v, o])