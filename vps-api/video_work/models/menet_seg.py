import torch
import torch.nn as nn
import torch.nn.functional as F


from .menet_backbone import MENetBackbone


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



class _Up(nn.Module):
    def __init__(self, in_ch, out_ch, bilinear=True):
        super().__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        else:
            self.up = nn.ConvTranspose2d(in_ch, in_ch // 2, 2, stride=2)
        self.conv = _DoubleConv(in_ch, out_ch)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, (diffX // 2, diffX - diffX // 2,
                        diffY // 2, diffY - diffY // 2))
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


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



class MENet(nn.Module):
    def __init__(
        self,
        in_channels=3,
        base_channels=32,
        num_classes=2,
        drop_path=0.1,
        encode_stages=(1, 1, 1, 1),
        pretrained=None,
        init_cfg=None,
    ):
        super().__init__()
        self.filters = [base_channels, base_channels * 2, base_channels * 4, base_channels * 8, base_channels * 16]
        factor = 2
        self.encoder = MENetBackbone(
            in_channels=in_channels,
            base_channels=base_channels,
            drop_path=drop_path,
            encode_stages=encode_stages,
            out_indices=(0, 1, 2, 3, 4, 5),
        )


        self.up4 = _Up(self.filters[4], self.filters[3] // factor, bilinear=True)
        self.up3 = _Up(self.filters[3], self.filters[2] // factor, bilinear=True)
        self.up2 = _Up(self.filters[2], self.filters[1] // factor, bilinear=True)
        self.up1 = _Up(self.filters[1], self.filters[0], bilinear=True)
        self.num_classes = num_classes

    def forward(self, x):
        edge_out, x1, x2, x3, x4, x5 = self.encoder(x)
        u = self.up4(x5, x4)
        u = self.up3(u, x3)
        u = self.up2(u, x2)
        u = self.up1(u, x1)
        edge_out = F.interpolate(edge_out, u.shape[2:], mode='bilinear', align_corners=True)
        edge_out = torch.sigmoid(edge_out)
        feat = torch.cat([edge_out, u], dim=1)
        # 直接输出二分类, '直接输出二分类'的工作交给fcn_head
        # feat = self.fuse(feat) # TODO: 分割头

        # mmsegmentation中 num_class=2, x是输入图像（channel=3）, 所以feat的channel=1.5*base_channels
        return [x1, x2, x3, x4, feat]  




class FCNHead(nn.Module):
    """
        对应mmsegmentation的FCNHead
    """
    class _ConvBNReLU(nn.Module):
        def __init__(self, in_channels, out_channels, kernel_size):
            super().__init__()
            self.conv = nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size,
                padding=kernel_size // 2,
                bias=False,
            )
            self.bn = nn.BatchNorm2d(out_channels)
            self.relu = nn.ReLU(inplace=True)

        def forward(self, x):
            x = self.conv(x)
            x = self.bn(x)
            x = self.relu(x)
            return x

    def __init__(self,
                 in_channels,
                 channels,
                 num_classes,
                 num_convs=1,
                 kernel_size=3,
                 concat_input=False,
                 dropout_ratio=0.1):
        super().__init__()
        assert num_convs >= 0
        self.in_channels = in_channels
        self.channels = channels
        self.num_classes = num_classes
        self.concat_input = concat_input

        conv_blocks = []
        if num_convs > 0:
            conv_blocks.append(self._ConvBNReLU(in_channels, channels, kernel_size))
            for _ in range(num_convs - 1):
                conv_blocks.append(self._ConvBNReLU(channels, channels, kernel_size))
        self.convs = nn.Sequential(*conv_blocks) if conv_blocks else nn.Identity()

        if self.concat_input:
            self.conv_cat = nn.Sequential(
                nn.Conv2d(in_channels + channels, channels, kernel_size, padding=kernel_size // 2, bias=False),
                nn.BatchNorm2d(channels),
                nn.ReLU(inplace=True),
            )
        else:
            self.conv_cat = None

        self.dropout = nn.Dropout2d(dropout_ratio) if dropout_ratio > 0 else None
        self.conv_seg = nn.Conv2d(channels, num_classes, kernel_size=1)

    def forward(self, x):
        feats = self.convs(x)
        if self.concat_input:
            feats = self.conv_cat(torch.cat([x, feats], dim=1))
        if self.dropout is not None:
            feats = self.dropout(feats)
        logits = self.conv_seg(feats)
        return logits



class MENetSeg(nn.Module):
    """
    """
    def __init__(self,
                 in_channels=3,
                 base_channels=32,
                 num_classes=2,
                 drop_path=0.1,
                 encode_stages=(1, 1, 1, 1),
                 pretrained=None,
                 init_cfg=None,
                 fcn_channels=None,
                 fcn_num_convs=1,
                 fcn_concat_input=False,
                 fcn_dropout_ratio=0.1):
        super().__init__()
        self.backbone = MENet(
            in_channels=in_channels,
            base_channels=base_channels,
            num_classes=num_classes,
            drop_path=drop_path,
            encode_stages=encode_stages,
            pretrained=pretrained,
            init_cfg=None,
        )
        fcn_in_channels = base_channels + base_channels // 2
        if fcn_channels is None:
            fcn_channels = fcn_in_channels
        self.decode_head = FCNHead(
            in_channels=fcn_in_channels,
            channels=fcn_channels,
            num_classes=num_classes,
            num_convs=fcn_num_convs,
            kernel_size=3,
            concat_input=fcn_concat_input,
            dropout_ratio=fcn_dropout_ratio,
        )

    def forward(self, x):
        feats = self.backbone(x)
        feat = feats[-1]
        logits = self.decode_head(feat)
        return logits
