
from sklearn.naive_bayes import MultinomialNB

mnb_model = MultinomialNB() 
# MultinomialNB(alpha=1.0, class_prior=None, fit_prior=True)

start = time.time()
mnb_model.fit(train_features, train_labels)
end = time.time()
print("Multinomial NB model trained in %f seconds" % (end-start))