import random


def gen_matrix(rows:int, cols:int):
    return [random.randint(0, 0xFF) for _ in range(rows*cols)]
