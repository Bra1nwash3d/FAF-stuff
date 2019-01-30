from modules.types import PointType
import random


a = {
    'a': 70,
    'b': 20,
    'c': 10
}
drawn = {
    'a': 0,
    'b': 0,
    'c': 0,
}

for i in range(10000):
    x = random.choices(list(a.keys()), list(a.values()))
    drawn[x[0]] += 1

print(drawn)
