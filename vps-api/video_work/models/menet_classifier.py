from .menet_backbone import MENetBackbone
import torch
import torch.nn as nn

class MENetClassifier(nn.Module):
    def __init__(self,
                 weight_path : str | None = None,
                 num_classes=200,
                 in_channels=3,
                 base_channels=32,
                 drop_path=0.1,
                 encode_stages=(1, 1, 1, 1)):
        super().__init__()
        # 获取分类用的最高层特征 x5
        self.backbone = MENetBackbone(
            in_channels=in_channels,
            base_channels=base_channels,
            drop_path=drop_path,
            encode_stages=encode_stages,
            out_indices=(5,),
            norm_eval=False,
            init_cfg=None
        )
        classifier_in_ch = (base_channels * 16) // 2
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(classifier_in_ch, num_classes)
        )

        self.num_classes = num_classes

            # 加载自己预训练的模型权重
        if weight_path:
            ckpt = torch.load(weight_path, map_location="cpu")
            state_dict = ckpt.get("state_dict", ckpt)
            new_sd = {}
            for k, v in state_dict.items():
                nk = k
                if nk.startswith("module."):
                    nk = nk[len("module."):]
                if nk == "fc.weight":
                    nk = "head.2.weight"
                elif nk == "fc.bias":
                    nk = "head.2.bias"
                elif nk == "classifier.weight":
                    nk = "head.2.weight"
                elif nk == "classifier.bias":
                    nk = "head.2.bias"
                new_sd[nk] = v
            msd = self.state_dict()
            filtered_sd = {}
            for k, v in new_sd.items():
                if k in msd and msd[k].shape == v.shape:
                    filtered_sd[k] = v
            self.load_state_dict(filtered_sd, strict=False)


    def forward(self, x):
        x5 = self.backbone(x)[0]
        return self.head(x5)


def convnext_tiny(num_classes=200):
    return MENetClassifier(num_classes=num_classes)
