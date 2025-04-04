from __future__ import absolute_import
from .AugmentCE2P import resnet101
from .context_encoding.aspp import ASPPModule as ASPP
from .context_encoding.ocnet import OCNet
from .context_encoding.psp import PSPModule

__factory = {
    'resnet101': resnet101,
}


def init_model(name, **kwargs):
    """Initialize model with verbose setting"""
    verbose = kwargs.pop('verbose', False)  # Get verbose setting
    model = get_model(name, **kwargs)
    
    # Set verbose for all modules
    for module in model.modules():
        if hasattr(module, 'verbose'):
            module.verbose = verbose
            
    return model

def get_model(name, *args, **kwargs):
    if name not in __factory.keys():
        raise KeyError("Unknown model arch: {}".format(name))
    return __factory[name](*args, **kwargs)