import numpy as np
import scipy

costSet1 = np.array(
    [[np.inf, 1, np.inf],
    [np.inf, 3, np.inf],
    [2, np.inf, 3]])


costSet2 = np.array(
    [[np.nan, 1, np.nan],
    [np.nan, 3, np.nan],
    [2, np.nan, 3]])


print(f'costSet1: \n {costSet1}')
print("")
print(f'costSet2: \n {costSet2}')