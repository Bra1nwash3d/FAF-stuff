from modules.types import PointType


print(PointType.CHATTIP.value)
for x in PointType:
    print(x)

print([None, 1].count(None))

a = {'a': False, 'b': True}
a.pop('b')
print('a' in a)
print('b' in a)
