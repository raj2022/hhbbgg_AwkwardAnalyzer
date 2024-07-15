## following the instructions from https://betatim.github.io/posts/sklearn-for-TMVA-users/
## https://matplotlib.org/tutorials/introductory/usage.html#sphx-glr-tutorials-introductory-usage-py
## https://machinelearningmastery.com/adaboost-ensemble-in-python/


import numpy as np
import matplotlib as mpl

# import matplotlib
mpl.use("pdf")
import matplotlib.pyplot as plt

import matplotlib.pyplot as plt

from sklearn import datasets
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.metrics import classification_report, roc_auc_score
import pandas.core.common as com
from pandas.core.index import Index

from pandas.tools import plotting
from pandas.tools.plotting import scatter_matrix

from sklearn.cross_validation import train_test_split

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.utils import shuffle
from glob import glob
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.model_selection import GridSearchCV


def OptimizeHyperparmeters(X, y):
    print("optimizing hyper parameters\n")
    # DEFINE THE MODEL WITH DEFAULT HYPERMETERS
    dt = DecisionTreeClassifier(max_depth=3, min_samples_leaf=0.03)
    model = AdaBoostClassifier()
    # DEFINE THE GRID OF VALUES TO SEARCH
    grid = dict()
    grid["n_estimators"] = [50, 100, 300, 500, 700, 1000]
    grid["learning_rate"] = [0.001, 0.005, 0.01, 0.05, 0.1]
    # DEFINE THE EVALUATION PROCEDURE
    cv = RepeatedStratifiedKFold(n_splits=10, n_repeats=3, random_state=1)
    # DEFINE THE GRID SEARCH PROCEDURE
    # grid_search = GridSearchCV(estimator=model, param_grid=grid, n_jobs=-1, cv=cv, scoring='accuracy')
    grid_search = GridSearchCV(
        estimator=model, param_grid=grid, n_jobs=-1, cv=cv, scoring="roc_auc"
    )
    # EXECUTE THE GRID SEARCH
    grid_result = grid_search.fit(X, y)
    # SUMMARIZE THE BEST SCORE AND CONFIGURATION
    print("Best: %f using %s" % (grid_result.best_score_, grid_result.best_params_))
    # SUMMARIZE ALL SCORES THAT WERE EVALUATED
    means = grid_result.cv_results_["mean_test_score"]
    stds = grid_result.cv_results_["std_test_score"]
    params = grid_result.cv_results_["params"]
    for mean, stdev, param in zip(means, stds, params):
        print("%f (%f) with: %r" % (mean, stdev, param))


def plotFeature(df1, df2, invars, sample, nbins):
    for var in invars:
        data1 = df1[var]
        data2 = df2[var]
        mini = min([min(data1), min(data2)])
        maxi = max([max(data1), max(data2)])

        x = data1
        y = data2

        bins = np.linspace(mini, maxi, nbins)
        fig = plt.figure()
        plt.hist(y, bins, alpha=0.5, label="B", density=True)
        plt.hist(x, bins, alpha=0.5, label="S", density=True)
        ax = fig.add_subplot(111)
        plt.text(0.1, 0.9, var, ha="center", va="center", transform=ax.transAxes)
        plt.legend(loc="upper right")
        plt.savefig("plots/feature_" + sample + "_" + var + ".pdf")
        plt.savefig("plots/feature_" + sample + "_" + var + ".png")

        plt.close(fig)


def plot_ROC(bdt, X_train, y_train, type_="train"):
    import matplotlib.pyplot as plt

    from sklearn.metrics import roc_curve, auc

    decisions = bdt.decision_function(X_train)
    # Compute ROC curve and area under the curve
    fpr, tpr, thresholds = roc_curve(y_train, decisions)
    roc_auc = auc(fpr, tpr)
    fig = plt.figure()

    plt.plot(fpr, tpr, lw=1, label="ROC (area = %0.2f)" % (roc_auc))

    plt.plot([0, 1], [0, 1], "--", color=(0.6, 0.6, 0.6), label="Luck")
    plt.xlim([-0.05, 1.05])
    plt.ylim([-0.05, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Receiver operating characteristic")
    plt.legend(loc="lower right")
    plt.grid()
    # plt.show()
    plt.savefig("plots/antitop_roc_" + type_ + ".pdf")
    plt.savefig("plots/antitop_roc_" + type_ + ".png")
    plt.close(fig)


def compare_train_test(
    clf, X_train, y_train, X_test, y_test, postfix="_2b", bins=25
):  # bins=25
    import matplotlib.pyplot as plt

    decisions = []
    for X, y in ((X_train, y_train), (X_test, y_test)):
        d1 = clf.decision_function(X[y > 0.5]).ravel()
        d2 = clf.decision_function(X[y < 0.5]).ravel()
        decisions += [d1, d2]

    low = min(np.min(d) for d in decisions)
    high = max(np.max(d) for d in decisions)
    low_high = (low, high)

    plt.hist(
        decisions[0],
        color="r",
        alpha=0.5,
        range=low_high,
        bins=bins,
        histtype="stepfilled",
        normed=True,
        label="S (train)",
    )
    plt.hist(
        decisions[1],
        color="b",
        alpha=0.5,
        range=low_high,
        bins=bins,
        histtype="stepfilled",
        normed=True,
        label="B (train)",
    )

    hist, bins = np.histogram(decisions[2], bins=bins, range=low_high, normed=True)
    scale = len(decisions[2]) / sum(hist)
    err = np.sqrt(hist * scale) / scale

    width = bins[1] - bins[0]
    center = (bins[:-1] + bins[1:]) / 2
    plt.errorbar(center, hist, yerr=err, fmt="o", c="r", label="S (test)")

    hist, bins = np.histogram(decisions[3], bins=bins, range=low_high, normed=True)
    scale = len(decisions[2]) / sum(hist)
    err = np.sqrt(hist * scale) / scale

    plt.errorbar(center, hist, yerr=err, fmt="o", c="b", label="B (test)")

    plt.xlabel("BDT output")
    plt.ylabel("Arbitrary units")
    plt.legend(loc="best")

    plt.savefig("plots/antitop_bdt" + postfix + ".pdf")
    plt.savefig("plots/antitop_bdt" + postfix + ".png")


""" load data """
from root_pandas import read_root

# vars_to_load_ = ['MET', 'METPhi', 'pfMetCorrSig', 'Jet1Pt', 'Jet1Eta', 'Jet1Phi', 'Jet1deepCSV', 'Jet2Pt', 'Jet2Eta', 'Jet2Phi', 'Jet2deepCSV', 'dRJet12', 'dPhiJet12', 'dEtaJet12', 'M_Jet1Jet2', 'pT_Jet1Jet2', 'eta_Jet1Jet2', 'phi_Jet1Jet2', 'JetHT', 'rJet1PtMET', 'ratioPtJet21', 'dPhi_jetMET']
### taking top10 variables:
# vars_to_load_ = ['JetHT', 'Jet1deepCSV', 'dRJet12', 'dPhiJet12', 'Jet1Pt', 'Jet2deepCSV', 'Jet2Eta', 'Jet2Pt', 'eta_Jet1Jet2','dEtaJet12']

### taking top5 variables:
vars_to_load_ = ["JetHT", "Jet1deepCSV", "dRJet12", "dPhiJet12", "dEtaJet12"]

# signal_file_ = glob("/home/ptiwari/t3store3/CMSSW_10_3_0/src/v12-00-03/ExoPieProducer/ExoPieAnalyzer/CondorJobs_Analyser/BR_Outputs_v17_12-00-03_ZJets_2HDMaSIG/*bbDM_2HDMa*.root")
signal_file_ = glob(
    "/home/ptiwari/t3store3/CMSSW_10_3_0/src/v12-00-03/ExoPieProducer/ExoPieAnalyzer/CondorJobs_Analyser/BR_Outputs_v17_12-00-03_ZJets_DMSimpSIG/*bbDM_DMSimp*.root"
)
# bkg_file = glob('/home/ptiwari/t3store3/CMSSW_10_3_0/src/v12-00-03/ExoPieProducer/ExoPieAnalyzer/CondorJobs_Analyser/BR_Outputs_v17_12-00-03_ZJets_2HDMaSIG/*ZJetsToNuNu*.root')
bkg_file = glob(
    "/home/ptiwari/t3store3/CMSSW_10_3_0/src/v12-00-03/ExoPieProducer/ExoPieAnalyzer/CondorJobs_Analyser/BR_Outputs_v17_12-00-03_ZJets_DMSimpSIG/*ZJetsToNuNu*.root"
)

bkg_file = list(bkg_file)

bkg_file_ = [samp for samp in bkg_file if not ("HToBB" in samp)]
# SMHbkg_file_ = [samp for samp in bkg_file if ("HToBB" in samp)]
# print (SMHbkg_file_)

df_signal = read_root(signal_file_, "bbDM_SR_2b", columns=vars_to_load_)
df_bkg_ = read_root(bkg_file_, "bbDM_SR_2b", columns=vars_to_load_)

# df_SMHbkg      = read_root(SMHbkg_file_,         'bbDM_SR_2b', columns=vars_to_load_)


"""
df_bkgttsem = read_root(ttsembkg_file_,    'bbDM_SR_2b', columns=vars_to_load_)
df_bkgZnunu = read_root(Znunubkg_file_,    'bbDM_SR_2b', columns=vars_to_load_)
df_bkgWJets = read_root(WJetsbkg_file_,    'bbDM_SR_2b', columns=vars_to_load_)
"""
df_signal = df_signal[(df_signal.JetHT > 0)]
df_bkg_ = df_bkg_[(df_bkg_.JetHT > 0)]

# df_signal['pi'] = math.pi
# df_signal['del_minus'] = df_signal.dPhi_jetMET - df_signal.dPhiJet12
# df_signal['del_plus'] = abs(df_signal.dPhi_jetMET + df_signal.dPhiJet12 - np.pi)
df_signal["costheta_star"] = abs(np.tanh(df_signal.dEtaJet12.div(2)))

# df_bkg_['pi'] = math.pi
# df_bkg_['del_minus'] = df_bkg_.dPhi_jetMET - df_bkg_.dPhiJet12
# df_bkg_['del_plus'] = abs(df_bkg_.dPhi_jetMET + df_bkg_.dPhiJet12 - np.pi)
df_bkg_["costheta_star"] = abs(np.tanh(df_bkg_.dEtaJet12.div(2)))


# df_SMHbkg = df_SMHbkg[df_SMHbkg.Jet1Pt>0]


df_signal = shuffle(df_signal, random_state=0)
# df_SMHbkg = shuffle(df_SMHbkg,random_state=0)

# df_SMHbkg = df_SMHbkg[:2000]

# df_allbkg = np.concatenate((df_bkg_, df_SMHbkg))
# df_allbkg = shuffle(df_allbkg,random_state=0)
df_bkg = shuffle(df_bkg_, random_state=0)
""" skim the data """

""" ADD extra coulumns """

# df_signal["weight0"] = (df_signal["nJets"]==0).astype(int)
# df_signal["weight1"] = (df_signal["nJets"]==1).astype(int)
# df_signal["weight2"] = (df_signal["nJets"]==2).astype(int)

# df_bkg["weight0"] = (df_bkg["nJets"]==0).astype(int)
# df_bkg["weight1"] = (df_bkg["nJets"]==1).astype(int)
# df_bkg["weight2"] = (df_bkg["nJets"]==2).astype(int)

# print df_signal[:1]
# df_signal = df_signal.drop(["nJets"],axis = 1)
# df_bkg = df_bkg.drop(["nJets"],axis = 1)

print(df_signal[:1])
df_signal_skim = df_signal
df_bkg_skim = df_bkg
vars_to_load_ += ["costheta_star"]
plotFeature(df_signal_skim, df_bkg_skim, vars_to_load_, sample="fullbkg", nbins=20)
# plotFeature(df_signal_skim, df_bkgZnunu, vars_to_load_,sample="ZJetsToNuNu",nbins=20)
# plotFeature(df_signal_skim, df_bkgWJets, vars_to_load_,sample="WJetsToLNu_HT600To800",nbins=20)
# if len(df_signal)>20000:
print("original size of the dataset", len(df_signal_skim), len(df_bkg_skim))
df_signal_skim = df_signal_skim[:9000]
df_bkg_skim = df_bkg_skim[:9000]
print("size of the dataset", len(df_signal_skim), len(df_bkg_skim))
# print df_signal_skim
# print df_bkg_skim

# join signal and background sample into same dataset.
X = np.concatenate((df_signal_skim, df_bkg_skim))
# Xprime = np.concatenate((df_signal_skim, df_allbkg))
# print X

## create a column with length = sum of length of signal and background, signal is 1 and background is 0
y = np.concatenate((np.ones(df_signal_skim.shape[0]), np.zeros(df_bkg_skim.shape[0])))

# yprime=np.concatenate((np.ones(df_signal_skim.shape[0]),np.zeros(df_allbkg.shape[0])))


""" plot data 1d """


""" plot data 2d / scatter """

"""plot data correlation/covariance """

""" split samples for testing and training """


X_dev, X_eval, y_dev, y_eval = train_test_split(X, y, test_size=0.01, random_state=42)

# Xprime_dev,Xprime_eval, yprime_dev,yprime_eval = train_test_split(Xprime, yprime,
# test_size=0.01, random_state=42)

X_train, X_test, y_train, y_test = train_test_split(
    X_dev, y_dev, test_size=0.33, random_state=42
)

# Xprime_train,Xprime_test, yprime_train,yprime_test = train_test_split(Xprime_dev, yprime_dev,
# test_size=0.33, random_state=42)


""" define model """
dt = DecisionTreeClassifier(max_depth=3, min_samples_leaf=0.03)  # *len(X_train))

bdt = AdaBoostClassifier(dt, algorithm="SAMME", n_estimators=500, learning_rate=0.05)

"""
OPTIMIZE OptimizeHyperparmeters
"""
# OptimizeHyperparmeters(X_train, y_train)

""" perform training """
bdt.fit(X_train, y_train)

""" feasure importance"""
importances = bdt.feature_importances_
std = np.std([tree.feature_importances_ for tree in bdt.estimators_], axis=0)
indices = np.argsort(importances)[::-1]

# Print the feature ranking
# print "bdt.estimators_",bdt.estimators_
print("std", std)
print("Feature ranking:")
print("X,shape[1]", X.shape[1])
print("importances", importances)
print("indices", indices)
columns_ = [ij for ij in df_bkg_skim.columns]
print("features   :", columns_)
for f in range(X.shape[1]):
    print(
        "%d. feature %d  (%s)   (%f)"
        % (f + 1, indices[f], columns_[indices[f]], importances[indices[f]])
    )


print("training done ")
TestOnmix = False
if TestOnmix:
    X_eval = Xprime_eval
    y_eval = yprime_eval
    X_test = Xprime_test
    y_test = yprime_test

y_predicted = bdt.predict(X_test)
print(classification_report(y_test, y_predicted, target_names=["background", "signal"]))
print(
    "Area under ROC curve X_test: %.4f"
    % (roc_auc_score(y_test, bdt.decision_function(X_test)))
)


y_predicted = bdt.predict(X_train)
print(
    classification_report(y_train, y_predicted, target_names=["background", "signal"])
)
print(
    "Area under ROC curve X_train: %.4f"
    % (roc_auc_score(y_train, bdt.decision_function(X_train)))
)


y_predicted = bdt.predict(X_eval)
print(classification_report(y_eval, y_predicted, target_names=["background", "signal"]))
print(
    "Area under ROC curve X_eval: %.4f"
    % (roc_auc_score(y_eval, bdt.decision_function(X_eval)))
)

""" check the outcome """

""" check the performance / ROC """


""" overtraining check """

""" save trained model for future, i.e. applying to the analysis """

""" going further: deeper ? """
plot_ROC(bdt, X_train, y_train, "train_2b")
plot_ROC(bdt, X_test, y_test, "test_2b")
plot_ROC(bdt, X_eval, y_eval, "eval_2b")

compare_train_test(bdt, X_train, y_train, X_test, y_test, postfix="_2b")

from pickle import dump, load

dump(bdt, open("discriminator_2b.pickle", "wb"))
