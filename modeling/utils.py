import logging
import multiprocessing
import time
from functools import partial

import numpy as np
import optuna
import pandas as pd
from tqdm import tqdm

logging.basicConfig(format='%(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)

NUMBER = int, float


def laida_bound(data):
    ''' 拉以达边界
        data: 单指标向量'''
    std = np.std(data)
    mean = np.mean(data)
    return mean - std * 3, mean + std * 3


def comentropy(origin):
    ''' 熵权法
        proba: 概率
        info: 信息量 -ln(proba)
        entropy: 信息熵 (Σ proba * info) / ln(n)
        redu: 冗余度 1 - entropy'''
    proba = origin / origin.sum(axis=0, keepdims=True)
    info = - np.log(proba, where=proba > 0)
    redu = 1 - (proba * info).sum(axis=0) / np.log(origin.shape[0])
    return redu / redu.sum()


def solve_weight(array):
    ''' 求解特征方程
        return: w, CI'''
    array, n, wlist = array.copy(), array.shape[0], []
    # 算术平均法
    w = (array / array.sum(axis=0)).mean(axis=1, keepdims=True)
    wlist.append(w)
    # 几何平均法
    w = np.prod(array, axis=1, keepdims=True) ** (1 / n)
    wlist.append(w / w.sum())
    # 特征值法
    solution, ws = np.linalg.eig(array)
    index = solution.argmax()
    lambda_ = solution[index].real
    w = ws[:, index].real
    wlist.append((w / w.sum())[:, None])
    # 输出对比结果
    w = np.concatenate(wlist, axis=1)
    LOGGER.info(pd.DataFrame(w, columns=['算术平均', '几何平均', '特征值']))
    LOGGER.info('')
    w = w.mean(axis=1)
    # 计算 CI
    return w, (lambda_ - n) / (n - 1)


def cal_RI(n, epochs=1000, decimals=4):
    if n <= 15:
        return {3: 0.52, 4: 0.89, 5: 1.12, 6: 1.26, 7: 1.36, 8: 1.41, 9: 1.46,
                10: 1.49, 11: 1.52, 12: 1.54, 13: 1.56, 14: 1.58, 15: 1.59}[n]
    else:
        mark = time.time()
        LOGGER.info(f'Calulating RI: dim = {n}, epochs={epochs}, decimals={decimals}')
        lambda_sum = 0
        for i in range(epochs):
            array = np.eye(n)
            # 随机构造成对比较矩阵
            for c in range(n):
                for r in range(c):
                    array[c][r] = np.random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9,
                                                    1 / 2, 1 / 3, 1 / 4, 1 / 5,
                                                    1 / 6, 1 / 7, 1 / 8, 1 / 9])
                    array[r][c] = 1 / array[c][r]
            # 求取最大特征值
            solution, weights = np.linalg.eig(array)
            lambda_sum += solution.max().real
        # 最大特征值的均值
        lambda_ = lambda_sum / 1000
        RI = round((lambda_ - n) / (n - 1), decimals)
        LOGGER.info(f'RI = {RI}, time = {round(time.time() - mark, 2)}s')
        return RI


class solvex:
    ''' fx: 关于 x 的函数 f(x), 优化目标为 f(x) = 0
        xlow,xhigh: x 的上下限'''

    def __new__(cls, fx, xlow, xhigh, timeout=.2, dtype='float', log=False):
        self = object.__new__(cls)
        self.fx = fx
        self.xcfg = dict(low=xlow, high=xhigh, log=log)
        self.dtype = dtype
        # 使用 optuna 求解自变量 x
        logging.disable(logging.INFO)
        study = optuna.create_study(direction='minimize')
        study.optimize(self.ferror, timeout=timeout)
        logging.disable(logging.NOTSET)
        # xs = sorted(set(trial.params['x'] for trial in study.trials))
        return study.best_params['x']

    def ferror(self, trial: optuna.Trial):
        x = getattr(trial, f'suggest_{self.dtype}')('x', **self.xcfg)
        return self.fx(x) ** 2

    @classmethod
    def _sym_map_handler(cls, f, sym_tar, **kwargs):
        fx = lambda x: f.subs({sym_tar: x})
        return cls(fx, **kwargs)

    @classmethod
    def sym_map(cls, f, sym_tar, sym_dict, workers=8, **kwargs):
        sym_list = [[k, v.flatten().tolist()] for k, v in sym_dict.items()]
        shape = sym_dict.copy().popitem()[1].shape
        n = np.prod(shape)
        # 生成阻塞多进程
        x = tqdm(multiprocessing.Pool(workers).imap(
            partial(cls._sym_map_handler, sym_tar=sym_tar, **kwargs),
            [f.subs({k: v[i] for k, v in sym_list}) for i in range(n)]
        ), total=n, desc='Sym Map')
        return np.array(list(x)).reshape(shape)


if __name__ == '__main__':
    import sympy as sp

    x, y = sp.symbols('x, y')
    f = x + y
    print(solvex.sym_map(f, y, {x: np.arange(15).reshape(5, 3)}, xlow=-20, xhigh=20))
