import torch
import torch.nn as nn
import torch.nn.functional as F

class InPlaceABNSync(nn.Module):
    def __init__(self, num_features, eps=1e-5, momentum=0.1, affine=True, activation="leaky_relu", slope=0.01):
        super(InPlaceABNSync, self).__init__()
        self.num_features = num_features
        self.affine = affine
        self.eps = eps
        self.momentum = momentum
        self.activation = activation
        self.slope = slope
        
        if self.affine:
            self.weight = nn.Parameter(torch.ones(num_features))
            self.bias = nn.Parameter(torch.zeros(num_features))
        else:
            self.register_parameter('weight', None)
            self.register_parameter('bias', None)
            
        self.register_buffer('running_mean', torch.zeros(num_features))
        self.register_buffer('running_var', torch.ones(num_features))
        
    def forward(self, x):
        x = F.batch_norm(x, self.running_mean, self.running_var, 
                        self.weight, self.bias, self.training, 
                        self.momentum, self.eps)
        
        if self.activation == "leaky_relu":
            return F.leaky_relu(x, self.slope)
        elif self.activation == "elu":
            return F.elu(x)
        return x 