
import torch
from pathlib import Path
from torchvision import transforms

from video_work.models.menet_classifier import MENetClassifier


DEFAULT_MODEL_PATH = str(Path(__file__).resolve().parent / "menet-backbone.pth.tar")

# TODO: 分类模型待改为 efficientnet
class Classify:
    _instance: "Classify | None" = None

    def __new__(cls, model_path: str = DEFAULT_MODEL_PATH) -> "Classify":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.model_path = model_path or DEFAULT_MODEL_PATH
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device = device
        self.model = MENetClassifier(num_classes=2, weight_path=self.model_path)
        self.model.to(device)
        self.model.eval()
        self.transform = transforms.Compose(
            [
                transforms.Resize((384, 384)),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        self._initialized = True

    
    def predict_images(self, frame_tensors, batch: int = 6) -> tuple[list[int], list[float]]:
        if frame_tensors is None:
            raise ValueError("frame_tensors is None")
        processed_tensors = []
        for tensor in frame_tensors:
            if tensor is None:
                raise ValueError("tensor in frame_tensors is None")
            tensor = self.transform(tensor)
            processed_tensors.append(tensor)
        if not processed_tensors:
            return [], []
        if batch <= 0:
            raise ValueError("batch must be positive")
        all_preds: list[int] = []
        all_probs: list[float] = []
        for i in range(0, len(processed_tensors), batch):
            batch_tensors = processed_tensors[i : i + batch]
            batch_tensor = torch.stack(batch_tensors, dim=0)
            with torch.no_grad():
                logits = self.model(batch_tensor)
                probs = torch.softmax(logits, dim=1)[:, 1]
                preds = torch.argmax(logits, dim=1).tolist()
                prob_list = probs.tolist()
            all_preds.extend(int(p) for p in preds)
            all_probs.extend(float(p) for p in prob_list)
        return all_preds, all_probs


    @staticmethod
    def fix_class_prob(class_list, prob_list, class_index):
        """
        功能：修正分类-概率序列
        """
        n = len(class_list)
        # 向前遍历，从 class_index-1 到 0
        for i in range(class_index - 1, -1, -1):
            if class_list[i] != 0:
                # 向前搜索最近的0的概率
                found_prob = 0.6
                for j in range(i - 1, -1, -1):
                    if class_list[j] == 0:
                        found_prob = prob_list[j]
                        break
                class_list[i] = 0
                prob_list[i] = found_prob
        
        # 向后遍历，从 class_index+1 到 n-1
        for i in range(class_index + 1, n):
            if class_list[i] != 1:
                # 向后搜索最近的1的概率
                found_prob = 0.6
                for j in range(i + 1, n):
                    if class_list[j] == 1:
                        found_prob = prob_list[j]
                        break
                class_list[i] = 1
                prob_list[i] = found_prob
        
        return class_list, prob_list

    @staticmethod
    def find_first_inserted_frame(class_list: list[int] = [], prob_list: list[float] = [], judge_wnd=20):
        """
        功能：根据分类-概率序列，找关键插入帧
        """
       
        ############# 找关键插入帧 START  #############
        required_count = 0.9 * judge_wnd
        
        # 阈值列表，从大到小排列
        thresholds = [0.9, 0.8, 0.7, 0.6]
        insert_frame_index = -1
        
        for i in range(len(prob_list) - judge_wnd + 1):
            wnd_probs = prob_list[i:i + judge_wnd]
            wnd_classes = class_list[i:i + judge_wnd]
            
            # 计算当前窗口内 `class=1` 的帧数
            count = sum(1 for j in range(judge_wnd) if wnd_classes[j] == 1)
            
            if count >= required_count:
                # 遍历各个阈值
                for threshold in thresholds:
                    # 寻找连续5帧 `class=1` 且概率 > 阈值
                    for k in range(judge_wnd - 4):
                        if all(wnd_classes[k + l] == 1 and wnd_probs[k + l] > threshold for l in range(5)):
                            insert_frame_index = i + k
                            break
                    if insert_frame_index != -1:
                        break
                if insert_frame_index != -1:
                    break
        if insert_frame_index == -1:
            insert_frame_index = 0
        ############# 找关键插入帧 END  #############
        
        # 分类序列修正 
        Classify.fix_class_prob(class_list, prob_list, insert_frame_index)
        
        return insert_frame_index
