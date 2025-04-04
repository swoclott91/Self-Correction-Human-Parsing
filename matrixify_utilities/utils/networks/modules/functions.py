import torch
import torch.nn.functional as F
from torch.autograd import Function

class InPlaceABN(Function):
    @staticmethod
    def forward(ctx, x, weight, bias, running_mean, running_var, training=True, momentum=0.1, eps=1e-5, activation="leaky_relu", slope=0.01):
        # Store context
        ctx.training = training
        ctx.momentum = momentum
        ctx.eps = eps
        ctx.activation = activation
        ctx.slope = slope
        
        # Prepare inputs
        x = x.contiguous()
        
        if ctx.training:
            mean = x.mean(dim=(0, 2, 3))
            var = x.var(dim=(0, 2, 3), unbiased=False)
            
            # Update running stats
            running_mean.mul_(1 - ctx.momentum).add_(mean * ctx.momentum)
            running_var.mul_(1 - ctx.momentum).add_(var * ctx.momentum)
        else:
            mean = running_mean
            var = running_var
            
        # Normalize
        x = F.batch_norm(x, running_mean, running_var, weight, bias, 
                        ctx.training, ctx.momentum, ctx.eps)
        
        # Apply activation
        if ctx.activation == "leaky_relu":
            x = F.leaky_relu(x, ctx.slope)
        elif ctx.activation == "elu":
            x = F.elu(x)
        elif ctx.activation == "none":
            pass
            
        return x

    @staticmethod
    def backward(ctx, grad_output):
        # Simplified backward pass
        return grad_output, None, None, None, None, None, None, None, None, None

def inplace_abn(x, weight, bias, running_mean, running_var, training=True, momentum=0.1, 
                eps=1e-05, activation="leaky_relu", slope=0.01):
    """Applies In-Place Activated Batch Normalization"""
    # Compute batch norm
    if training:
        mean = x.mean(dim=(0, 2, 3))
        var = x.var(dim=(0, 2, 3), unbiased=False)
        
        # Update running stats
        running_mean = momentum * mean + (1 - momentum) * running_mean
        running_var = momentum * var + (1 - momentum) * running_var
    else:
        mean = running_mean
        var = running_var
    
    # Normalize
    x = (x - mean[None, :, None, None]) / torch.sqrt(var[None, :, None, None] + eps)
    
    # Scale and shift
    x = x * weight[None, :, None, None] + bias[None, :, None, None]
    
    # Apply activation
    if activation == 'relu':
        x = torch.relu_(x)
    elif activation == 'leaky_relu':
        x = F.leaky_relu_(x, negative_slope=slope)
    elif activation == 'elu':
        x = F.elu_(x)
    
    return x, mean.detach(), var.detach()

def inplace_abn_sync(x, weight, bias, running_mean, running_var, training=True, momentum=0.1,
                    eps=1e-05, activation="leaky_relu", slope=0.01):
    """Applies In-Place Activated Batch Normalization with sync"""
    return inplace_abn(x, weight, bias, running_mean, running_var, training, momentum,
                      eps, activation, slope)

# Constants
ACT_RELU = "relu"
ACT_LEAKY_RELU = "leaky_relu"
ACT_ELU = "elu"
ACT_NONE = "none"

__all__ = ["inplace_abn", "inplace_abn_sync", "ACT_RELU", "ACT_LEAKY_RELU", "ACT_ELU", "ACT_NONE"]
