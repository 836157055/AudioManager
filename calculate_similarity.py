from scipy.spatial.distance import euclidean

def calculate_similarity(mfcc1, mfcc2):
    dist = euclidean(mfcc1.flatten(), mfcc2.flatten())
    return dist
