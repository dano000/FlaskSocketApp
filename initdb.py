import math
import pickle
import random
from datetime import datetime, timedelta

import numpy as np
from sklearn.neighbors import LocalOutlierFactor

from app import Case, Crisis, db, commit_data
from constants import COUNTRIES_IN_CRISIS, NAMES, REQUIRED_ASSISTANCE_TYPES, COUNTRIES_OF_ORIGIN


# Clamp Function #
################################################################################
def clamp(x, min, max):
    if x < min:
        return min
    elif x > max:
        return max
    else:
        return x


# Initialise DB #
################################################################################
db.create_all()

for k, v in COUNTRIES_IN_CRISIS:
    crisis = Crisis(title=v, code=k)
    db.session.add(crisis)
    db.session.commit()

counter = 0

for name in NAMES:
    counter += 1
    age = random.normalvariate(30, 15)
    date_of_birth = datetime.today() - timedelta(days=round(365 * age))
    crisis = random.randrange(1, 7)
    country_of_origin = random.sample(list(map(lambda x: x[0], COUNTRIES_OF_ORIGIN)), 1)[0]

    if math.floor(counter / 20) == counter / 20:
        required_assistance_types = ",".join((list(map(lambda x: x[0], REQUIRED_ASSISTANCE_TYPES))))
        amount = round(random.normalvariate(5000, 1000), 2)
    else:
        required_assistance_types = ",".join(random.sample(list(map(lambda x: x[0], REQUIRED_ASSISTANCE_TYPES)),
                                                           clamp(round(random.normalvariate(3, 1)), 1, 5)))
        amount = round(random.normalvariate(150, 50), 2)

    data = {
        'FN': name.split(" ")[0],
        'LN': name.split(" ")[1],
        'DOB': date_of_birth.strftime('%Y-%m-%d'),
        'COO': country_of_origin,
        'CCC': str(crisis),
        'RAT': required_assistance_types,
        'AMO': str(amount)
    }

    commit_data(data)

# Initialise and Save Local Outlier Factor Predictor/Estimator#
################################################################################
cases = Case.query.all()
inliers = Case.query.filter(Case.amount <= 1000).all()
outliers = Case.query.filter(Case.amount >= 1000).all()

X_inliers = list(
    map(lambda c: [c.amount, (c.food + c.housing + c.equipment + c.water + c.sanitation + c.building)], inliers))
X_outliers = list(
    map(lambda c: [c.amount, (c.food + c.housing + c.equipment + c.water + c.sanitation + c.building)], outliers))

X = np.r_[X_inliers, X_outliers]

gt = np.ones(len(X), dtype=int)
gt[-len(X_outliers):] = -1

clf = LocalOutlierFactor(novelty=True, contamination=0.05)
clf.fit(X, gt)
pickle.dump(clf, open('clf.p', 'wb'))
