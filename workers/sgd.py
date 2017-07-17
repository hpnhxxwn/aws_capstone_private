import pandas as pd
import numpy as np
from sklearn.cross_validation import train_test_split
from sklearn.metrics import confusion_matrix
from sklearn import metrics
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import SGDClassifier
import pickle


vector = pd.read_csv('vector.txt', sep=" ", header = None)
width = len(vector.columns)
length = len(vector)

feature = vector.drop(width-1, 1)
label = vector[width-1]
feature_matrix = feature.as_matrix()
label_matrix = label.as_matrix()

for i in range(length):
    if label_matrix[i] > 0.02:
        label_matrix[i] = 1
    elif label_matrix[i] < -0.02:
        label_matrix[i] = -1
    else:
        label_matrix[i] = 0

train_data, test_data, train_label, test_label = \
train_test_split(
    feature_matrix, 
    label_matrix, 
    test_size=0.0, 
    random_state=1
)

lr = SGDClassifier(loss = 'log', penalty = 'l1')
lr.fit(train_data, train_label)

accuracy = lr.score(test_data, test_label)

# lr.save("sgd_model")
with open('sgd.pkl', 'wb') as f:
    pickle.dump(lr, f)





