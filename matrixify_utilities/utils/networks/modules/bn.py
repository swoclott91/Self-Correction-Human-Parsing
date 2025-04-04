import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

from .functions import inplace_abn, inplace_abn_sync

# Add activation constants
ACT_RELU = "relu"
ACT_LEAKY_RELU = "leaky_relu"
ACT_ELU = "elu"
ACT_NONE = "none"

class ABN(nn.BatchNorm2d):
    """Activated Batch Normalization"""
    def __init__(self, num_features, eps=1e-5, momentum=0.1, affine=True, activation=ACT_LEAKY_RELU, slope=0.01):
        super(ABN, self).__init__(num_features, eps=eps, momentum=momentum, affine=affine)
        self.activation = activation
        self.slope = slope

    def forward(self, x):
        return inplace_abn(
            x, self.weight, self.bias,
            self.running_mean, self.running_var,
            self.training, self.momentum, self.eps,
            self.activation, self.slope
        )[0]


class BatchNorm2d(nn.BatchNorm2d):
    """BatchNorm2d without debug output"""
    def __init__(self, num_features, eps=1e-5, momentum=0.1, affine=True):
        super(BatchNorm2d, self).__init__(num_features, eps=eps, momentum=momentum, affine=affine)

    def forward(self, x):
        return super(BatchNorm2d, self).forward(x)


class InPlaceABN(ABN):
    """InPlace Activated Batch Normalization"""

    def __init__(self, num_features, eps=1e-5, momentum=0.1, affine=True, activation=ACT_LEAKY_RELU, slope=0.01):
        """Creates an InPlace Activated Batch Normalization module

        Parameters
        ----------
        num_features : int
            Number of feature channels in the input and output.
        eps : float
            Small constant to prevent numerical issues.
        momentum : float
            Momentum factor applied to compute running statistics as.
        affine : bool
            If `True` apply learned scale and shift transformation after normalization.
        activation : str
            Name of the activation functions, one of: `leaky_relu`, `elu` or `none`.
        slope : float
            Negative slope for the `leaky_relu` activation.
        """
        super(InPlaceABN, self).__init__(num_features, eps, momentum, affine, activation, slope)
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.constant_(self.running_mean, 0)
        nn.init.constant_(self.running_var, 1)
        if self.affine:
            nn.init.constant_(self.weight, 1)
            nn.init.constant_(self.bias, 0)

    def forward(self, x):
        return inplace_abn(
            x, self.weight, self.bias,
            self.running_mean, self.running_var,
            self.training, self.momentum, self.eps,
            self.activation, self.slope
        )[0]


class InPlaceABNSync(ABN):
    """InPlace Activated Batch Normalization with cross-GPU synchronization
    This assumes that it will be replicated across GPUs using the same mechanism as in `nn.DistributedDataParallel`.
    """

    def forward(self, x):
        return inplace_abn_sync(
            x, self.weight, self.bias,
            self.running_mean, self.running_var,
            self.training, self.momentum, self.eps,
            self.activation, self.slope
        )[0]

    def __repr__(self):
        rep = '{name}({num_features}, eps={eps}, momentum={momentum},' \
              ' affine={affine}, activation={activation}'
        if self.activation == "leaky_relu":
            rep += ', slope={slope})'
        else:
            rep += ')'
        return rep.format(name=self.__class__.__name__, **self.__dict__)


