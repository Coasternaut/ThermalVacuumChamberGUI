import pandas as pd
import numpy as np
import datetime, random

size = 1000000

startTime = datetime.datetime.now()

dates = pd.date_range(start=startTime, periods=size, freq='s')

elapsedTime = range(0, size)

randomSet1 = 100 * np.random.random(size)

data = pd.DataFrame({'elapsedTime': elapsedTime, 'temp1': randomSet1}, index=dates)

data.to_csv(f"testData_{size}.csv")