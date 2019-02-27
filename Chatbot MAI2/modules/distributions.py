import numpy as np


def sample(fun, config):
    return {
        Exponential.__name__: Exponential,
    }.get(fun).sample(**config)


class Exponential:
    """ exponential distribution, averages at mult * 1/lambda """

    @staticmethod
    def sample(min_, max_, mean_):
        return min([min_ + np.random.exponential(mean_), max_])


if __name__ == '__main__':
    cfg = {
        'mult': 3,
        'lambda_': 1,
    }
    s = 0
    n = 0
    for i in range(10000):
        s += sample('Exponential', cfg)
        n += 1
    print(s / n)
    print()
