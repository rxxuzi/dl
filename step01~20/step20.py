import weakref
import numpy as np


class Config:
    enable_backprop = True

class Var:
    def __init__(self, data, name = None):
        if data is not None:
            if not isinstance(data, np.ndarray):
                raise TypeError('{} is not supported'.format(type(data)))

        self.name = name    # 変数名
        self.data = data    # 数値
        self.grad = None    # 微分値
        self.creator = None # 生成者
        self.generation = 0 # 世代

    def __len__(self):      # 要素数を取得
        return len(self.data)

    def __add__(self, other):
        return add(self,other)
    def __mul__(self, other):# 演算子のオーバーロード
        return mul(self, other)

    def clean_grad(self):   # 微分値を消去
        self.grad = None

    @property
    def shape(self):        # 多次元配列の形状を取得
        return self.data.shape

    @property
    def ndim(self):         # 次元の数を取得
        return self.data.ndim

    @property
    def size(self):         # 要素の数
        return self.data.size

    @property
    def dtype(self):        # データの型を取得
        return self.data.dtype

    def set_creator(self, func):
        self.creator = func
        self.generation = func.generation + 1 # 世代をインクリメント

    def backward(self, retain_grad = False):
        if self.grad is None:
            self.grad = np.ones_like(self.data)

        funcs = []
        seen_set = set()

        def add_func(f):
            if f not in seen_set:
                funcs.append(f)
                seen_set.add(f)
                funcs.sort(key=lambda x: x.generation)

        add_func(self.creator)

        while funcs:
            f = funcs.pop()
            gys = [output().grad for output in f.outputs]  # output is weakref
            gxs = f.backward(*gys)
            if not isinstance(gxs, tuple):
                gxs = (gxs,)

            for x, gx in zip(f.inputs, gxs):
                if x.grad is None:
                    x.grad = gx
                else:
                    x.grad = x.grad + gx

                if x.creator is not None:
                    add_func(x.creator)

            if not retain_grad:
                for y in f.outputs:
                    y().grad = None  # y is weakref

    # toString
    def __repr__(self):
        if self.data is None:
            return 'Var(none)'
        p = str(self.data).replace('\n','\n' + ' ' * 9)
        return 'Var(' + p + ')'



def as_array(x):
    if np.isscalar(x):
        return np.array(x)
    return x


class Function:
    def __call__(self, *inputs):
        xs = [x.data for x in inputs]
        ys = self.forward(*xs)
        if not isinstance(ys, tuple):
            ys = (ys,)
        outputs = [Var(as_array(y)) for y in ys]

        if Config.enable_backprop:
            self.generation = max([x.generation for x in inputs])
            for output in outputs:
                output.set_creator(self)
            self.inputs = inputs
            self.outputs = [weakref.ref(output) for output in outputs]

        return outputs if len(outputs) > 1 else outputs[0]

    def forward(self, xs):
        raise NotImplementedError()

    def backward(self, gys):
        raise NotImplementedError()


class Add(Function):
    def forward(self, x0, x1):
        y = x0 + x1
        return y

    def backward(self, gy):
        return gy, gy


def add(x0, x1):
    return Add()(x0, x1)


class Mul(Function):
    def forward(self, x0, x1):
        y = x0 * x1
        return y

    def backward(self, gy):
        x0, x1 = self.inputs[0].data, self.inputs[1].data
        return gy * x1, gy * x0


def mul(x0, x1):
    return Mul()(x0, x1)


class Square(Function):
    def forward(self, x):
        return x ** 2

    def backward(self, gy):
        x = self.inputs[0].data
        return 2 * x * gy

def square(x):
    return Square()(x)


Var.__add__ = add
Var.__mul__ = mul


x = Var(np.array(
    [[1,2,3],
     [4,5,6],
     [7,8,9]]
))

r = Var(np.array(
    [[1,2,3],
     [4,5,6],
     [7,8,9]]
))

print(x * r)

n = Var(np.array([2,4,6]))

a = Var(np.array(3.0))
b = Var(np.array(2.0))
c = Var(np.array(5.0))

y = (a + b) * c
y.backward()

print(y.data)
print(a.grad)
print(b.grad)

#　行列x * スカラ a
v1 = x * a
print(y.data)

v2 = x * n
print(y.data)