import pandas as pd
import numpy as np
import pickle


def read_model():
	with open('sgd.pkl', 'rb') as f:
		return pickle.load(f)

# vector should be an array. ie [0.8, 0.6, -1.5]
def sentiment(vector, sgd_model):
    model = read_model()
    pred = model.predict(vector)
    return pred[0]

# txt = 'feature_vector.txt'
# returns an array
def sentiment_batch(txt, sgd_model):
	model = read_model()
	feature_vector = pd.read_csv(txt, sep=" ", header = None)
	feature_matrix = feature.as_matrix()
	pred = model.predict(feature_matrix)
	return pred



