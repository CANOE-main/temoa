"""testing dummy"""

import temoa.temoa_model.temoa_rules as rules

years = [
    2021,
    2025,
    2030,
    2035,
    2040,
    2045,
    2050,
    2055,
]

f = dict()

for year in years[0:-1]:
    ann = 0.05 / (1.0 - (1.0 + 0.05) ** (-10))

    f[year] = rules.loan_cost(
        capacity=1,
        invest_cost=1,
        loan_annualize=ann,
        lifetime_loan_process=10,
        P_0=min(years),
        P_e=max(years),
        GDR=0.05,
        vintage=year,
    )

print(f)
