import math
from typing import Callable, Optional

from colossalai.utils import get_current_device
from torch import dtype, nn

from ... import init as init
from ..parallel_1d import *
from ..parallel_2d import *
from ..parallel_2p5d import *
from ..parallel_3d import *
from ..utils import get_tensor_parallel_mode
from ..vanilla import *

_parallel_embedding = {'1d': Embedding1D, '2d': Embedding2D, '2.5d': Embedding2p5D, '3d': Embedding3D}

_parallel_patchembedding = {
    'None': VanillaPatchEmbedding,
    '1d': VanillaPatchEmbedding,
    '2d': PatchEmbedding2D,
    '2.5d': PatchEmbedding2p5D,
    '3d': PatchEmbedding3D
}


class Embedding(nn.Module):
    def __init__(self,
                 num_embeddings: int,
                 embedding_dim: int,
                 padding_idx: int = None,
                 dtype: dtype = None,
                 weight_initializer: Callable = init.normal_(),
                 *args,
                 **kwargs) -> None:
        super().__init__()
        tensor_parallel = get_tensor_parallel_mode()
        if tensor_parallel == 'None':
            self.embed = nn.Embedding(num_embeddings,
                                      embedding_dim,
                                      padding_idx=padding_idx,
                                      device=get_current_device(),
                                      dtype=dtype,
                                      *args,
                                      **kwargs)
            weight_initializer(self.embed.weight, fan_in=num_embeddings, fan_out=embedding_dim)
        else:
            self.embed = _parallel_embedding[tensor_parallel](
                num_embeddings,
                embedding_dim,
                padding_idx=padding_idx,
                dtype=dtype,
                weight_initializer=weight_initializer,
                *args,
                **kwargs,
            )

    @property
    def weight(self):
        return self.embed.weight

    def forward(self, *args):
        return self.embed(*args)


class PatchEmbedding(nn.Module):
    def __init__(self,
                 img_size: int,
                 patch_size: int,
                 in_chans: int,
                 embed_size: int,
                 dtype: dtype = None,
                 flatten: bool = True,
                 weight_initializer: Callable = init.kaiming_uniform_(a=math.sqrt(5)),
                 bias_initializer: Callable = init.xavier_uniform_(a=1, scale=1),
                 position_embed_initializer: Callable = init.zeros_()) -> None:
        super().__init__()
        tensor_parallel = get_tensor_parallel_mode()
        self.embed = _parallel_patchembedding[tensor_parallel](
            img_size,
            patch_size,
            in_chans,
            embed_size,
            dtype=dtype,
            flatten=flatten,
            weight_initializer=weight_initializer,
            bias_initializer=bias_initializer,
            position_embed_initializer=position_embed_initializer,
        )

    @property
    def weight(self):
        return self.embed.weight

    @property
    def bias(self):
        return self.embed.bias

    @property
    def pos_embed(self):
        return self.embed.pos_embed

    @property
    def cls_token(self):
        return self.embed.cls_token

    def forward(self, *args):
        return self.embed(*args)