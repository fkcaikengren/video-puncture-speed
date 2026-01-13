import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models.resnet import BasicBlock


class _DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class _InConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = _DoubleConv(in_ch, out_ch)

    def forward(self, x):
        return self.conv(x)


class _DWConv(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dwconv = nn.Conv2d(dim, dim, 3, 1, 1, bias=True, groups=dim)

    def forward(self, x):
        return self.dwconv(x)


class _GRN_NHWC(nn.Module):
    def __init__(self, dim, use_bias=True):
        super().__init__()
        self.use_bias = use_bias
        self.gamma = nn.Parameter(torch.zeros(1, 1, 1, dim))
        if use_bias:
            self.beta = nn.Parameter(torch.zeros(1, 1, 1, dim))

    def forward(self, x):
        Gx = torch.norm(x, p=2, dim=(1, 2), keepdim=True)
        Nx = Gx / (Gx.mean(dim=-1, keepdim=True) + 1e-6)
        if self.use_bias:
            return (self.gamma * Nx + 1) * x + self.beta
        else:
            return (self.gamma * Nx + 1) * x


def _NCHW_to_NHWC(x):
    return x.permute(0, 2, 3, 1)


def _NHWC_to_NCHW(x):
    return x.permute(0, 3, 1, 2)


class _ECA(nn.Module):
    def __init__(self, channel, k_size=3):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.conv = nn.Conv1d(1, 1, kernel_size=k_size, padding=(k_size - 1) // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        y = self.avg_pool(x)
        y = self.conv(y.squeeze(-1).transpose(-1, -2)).transpose(-1, -2).unsqueeze(-1)
        y = self.sigmoid(y)
        return x * y.expand_as(x)


class _LKA(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.conv0 = nn.Conv2d(dim, dim, 5, padding=2, groups=dim)
        self.conv_path1 = nn.Conv2d(dim, dim, 7, stride=1, padding=15, groups=dim, dilation=5)
        self.conv_path2 = nn.Conv2d(dim, dim, 7, stride=1, padding=9, groups=dim, dilation=3)
        self.conv_path3 = nn.Conv2d(dim, dim, 7, stride=1, padding=3, groups=dim)
        self.conv_path4 = nn.Identity()
        self.fc1 = nn.Conv2d(dim, dim // 4, 1)
        self.fc2 = nn.Conv2d(dim, dim // 4, 1)
        self.fc3 = nn.Conv2d(dim, dim // 4, 1)
        self.fc4 = nn.Conv2d(dim, dim // 4, 1)
        self.select_attn = _ECA(dim)
        self.proj = nn.Conv2d(dim, dim, 1)

    def forward(self, x):
        u = x.clone()
        x = self.conv0(x)
        part_1 = self.fc1(self.conv_path1(x))
        part_2 = self.fc2(self.conv_path2(x))
        part_3 = self.fc3(self.conv_path3(x))
        part_4 = self.fc4(self.conv_path4(x))
        attn = torch.cat([part_1, part_2, part_3, part_4], dim=1)
        attn = self.select_attn(attn)
        attn = self.proj(attn)
        return u * attn


class _Attention(nn.Module):
    def __init__(self, d_model):
        super().__init__()
        self.proj_1 = nn.Conv2d(d_model, d_model, 1)
        self.activation = nn.GELU()
        self.grn = _GRN_NHWC(d_model)
        self.spatial_gate = _LKA(d_model)
        self.proj_2 = nn.Conv2d(d_model, d_model, 1)

    def forward(self, x):
        shorcut = x.clone()
        x = self.proj_1(x)
        x = _NCHW_to_NHWC(x)
        x = self.activation(x)
        x = self.grn(x)
        x = _NHWC_to_NCHW(x)
        x = self.spatial_gate(x)
        x = self.proj_2(x)
        x = x + shorcut
        return x


class _Mlp(nn.Module):
    def __init__(self, in_features, hidden_features=None, out_features=None, act_layer=nn.GELU, drop=0.):
        super().__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        self.fc1 = nn.Conv2d(in_features, hidden_features, 1)
        self.dwconv = _DWConv(hidden_features)
        self.act = act_layer()
        self.grn = _GRN_NHWC(hidden_features)
        self.fc2 = nn.Conv2d(hidden_features, out_features, 1)
        self.drop = nn.Dropout(drop)

    def forward(self, x):
        x = self.fc1(x)
        x = self.dwconv(x)
        x = _NCHW_to_NHWC(x)
        x = self.act(x)
        x = self.grn(x)
        x = _NHWC_to_NCHW(x)
        x = self.drop(x)
        x = self.fc2(x)
        return x


class _MABlock(nn.Module):
    def __init__(self, dim, out_ch, mlp_ratio=4., drop=0.):
        super().__init__()
        self.norm1 = nn.BatchNorm2d(dim)
        self.attn = _Attention(dim)
        self.norm2 = nn.BatchNorm2d(dim)
        mlp_hidden_dim = int(dim * mlp_ratio)
        self.mlp = _Mlp(in_features=dim, hidden_features=mlp_hidden_dim, act_layer=nn.GELU, drop=drop)
        self.linear = nn.Conv2d(dim, out_ch, kernel_size=1)

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        x = x + self.mlp(self.norm2(x))
        return self.linear(x)


class _MultiScaleDown(nn.Module):
    def __init__(self, in_ch, out_ch, drop=0.):
        super().__init__()
        self.mpconv = nn.Sequential(
            nn.MaxPool2d(2),
            _MABlock(in_ch, out_ch, drop=drop)
        )

    def forward(self, x):
        return self.mpconv(x)


class _GatedSpatialConv2d(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self._gate_conv = nn.Sequential(
            nn.BatchNorm2d(in_channels + 4),
            _ECA(in_channels + 4),
            nn.Conv2d(in_channels + 4, 1, 1),
        )
        self.weight = nn.Parameter(torch.empty(out_channels, in_channels, 1, 1))
        self.bias = None
        nn.init.xavier_normal_(self.weight)

    def forward(self, input_features, gating_features):
        alphas = self._gate_conv(torch.cat([input_features, gating_features], dim=1))
        input_features = input_features * (alphas + 1)
        return F.conv2d(input_features, self.weight, self.bias, stride=1, padding=0)


class _BranchBlock(nn.Module):
    def __init__(self, in_ch, out_ch, gating_feature_ch):
        super().__init__()
        self.squeeze1 = nn.Conv2d(gating_feature_ch, 1, 1)
        self.squeeze2 = nn.Conv2d(gating_feature_ch, 1, 3, padding=1)
        self.main_block = BasicBlock(in_ch, in_ch, stride=1, downsample=None)
        self.down_proj = nn.Conv2d(in_ch, out_ch, 1)
        self.gate = _GatedSpatialConv2d(out_ch, out_ch)

    def forward(self, x, gating_features):
        g1 = self.squeeze1(gating_features)
        g2 = self.squeeze2(gating_features)
        g3, _ = torch.max(gating_features, dim=1, keepdim=True)
        g4 = torch.mean(gating_features, dim=1, keepdim=True)
        gf = F.interpolate(torch.cat([g1, g2, g3, g4], dim=1), x.shape[2:], mode='bilinear', align_corners=True)
        x = self.main_block(x)
        x = self.down_proj(x)
        x = self.gate(x, gf)
        return x


class MENetBackbone(nn.Module):
    def __init__(self,
                 in_channels=3,
                 base_channels=32,
                 drop_path=0.1,
                 encode_stages=(1, 1, 1, 1),
                 out_indices=(0, 1, 2, 3, 4),
                 norm_eval=False,
                 init_cfg=None):
        super().__init__()
     

        self.filters = [base_channels, base_channels * 2, base_channels * 4, base_channels * 8, base_channels * 16]
        factor = 2

        self.inc = _InConv(in_channels, self.filters[0])

        dp_rates = [drop_path * i / 3 for i in range(4)]
        blocks1 = [ _MultiScaleDown(self.filters[0], self.filters[1], drop=dp_rates[0]) ]
        for _ in range(int(encode_stages[0]) - 1):
            blocks1.append(_MABlock(self.filters[1], self.filters[1], drop=dp_rates[0]))
        self.down1 = nn.Sequential(*blocks1)
        blocks2 = [ _MultiScaleDown(self.filters[1], self.filters[2], drop=dp_rates[1]) ]
        for _ in range(int(encode_stages[1]) - 1):
            blocks2.append(_MABlock(self.filters[2], self.filters[2], drop=dp_rates[1]))
        self.down2 = nn.Sequential(*blocks2)
        blocks3 = [ _MultiScaleDown(self.filters[2], self.filters[3], drop=dp_rates[2]) ]
        for _ in range(int(encode_stages[2]) - 1):
            blocks3.append(_MABlock(self.filters[3], self.filters[3], drop=dp_rates[2]))
        self.down3 = nn.Sequential(*blocks3)
        stage4_out = self.filters[4] // factor
        blocks4 = [ _MultiScaleDown(self.filters[3], stage4_out, drop=dp_rates[3]) ]
        for _ in range(int(encode_stages[3]) - 1):
            blocks4.append(_MABlock(stage4_out, stage4_out, drop=dp_rates[3]))
        self.down4 = nn.Sequential(*blocks4)

        self.bb1 = _BranchBlock(self.filters[0], self.filters[0], self.filters[1])
        self.bb2 = _BranchBlock(self.filters[0], self.filters[0], self.filters[2])
        self.bb3 = _BranchBlock(self.filters[0], self.filters[0], self.filters[3])
        self.bb4 = _BranchBlock(self.filters[0], self.filters[0], self.filters[4] // factor)
        self.bb_out = nn.Conv2d(self.filters[0], base_channels // 2, 1)

        self.out_indices = out_indices
        self.norm_eval = norm_eval

        self.init_weights()

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        y = self.bb1(x1, x2)
        y = self.bb2(y, x3)
        y = self.bb3(y, x4)
        y = self.bb4(y, x5)
        edge_out = self.bb_out(y)
        # x5用于分类，提取低层特征
        outs = [edge_out, x1, x2, x3, x4, x5]
        return tuple(outs[i] for i in self.out_indices)

    def train(self, mode=True):
        super().train(mode)
        if mode and self.norm_eval:
            for m in self.modules():
                if isinstance(m, nn.BatchNorm2d):
                    m.eval()

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, (nn.BatchNorm2d, nn.GroupNorm)):
                nn.init.constant_(m.weight, 1)
                nn.init.zeros_(m.bias)

