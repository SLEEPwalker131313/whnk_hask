import random
from optimize import dist

def in_between(A, B, alpha):
    return (A[0] + alpha * abs(B[0] - A[0]), A[1] + alpha * abs(B[1] - A[1]))

def make_path(A, B, n, delta):

    A = (A[0] + random.uniform(-delta, delta), A[1] + random.uniform(-delta, delta))
    length = dist(A, B)
    A_rect = ((A[1] - B[1]) / length, (B[0] - A[0]) / length)


    alphas = [random.uniform(0, 1) for i in range(n)]
    alphas.sort()

    ab_points = [in_between(A, B, alpha) for alpha in alphas]

    deviations = [random.uniform(-delta, delta) for p in ab_points]

    return [A, *[(p[0] + d*A_rect[0], p[1] + d*A_rect[1])
            for p, d in zip(ab_points, deviations)], B]


if __name__ == '__main__':
    print(make_path((1,1), (8,8), 3, 4))


