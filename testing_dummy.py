"""testing dummy"""
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
from matplotlib import pyplot as pp

df = pd.read_csv('hull_points.csv', index_col=0)
points = df.to_numpy()

pp.plot(points)
pp.show()