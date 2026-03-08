from datetime import datetime, timedelta
from typing import List, Tuple

class FSRSScheduler:
    def __init__(self):
        self.initial_stability = 0.5
        # 标准 FSRS 难度调整 (4:Easy, 3:Good, 2:Hard, 1:Again)
        self.d_adj = {4: -0.5, 3: -0.2, 2: 0.4, 1: 1.0}

    def calc_next_review(self, current_s: float, current_d: float, rating: int) -> Tuple[float, float, datetime]:
        """计算下一次复习的参数与日期"""
        new_d = max(1.0, min(10.0, current_d + self.d_adj.get(rating, 0.0)))
        weights = {4: 1.0, 3: 0.8, 2: 0.0, 1: 0.0}
        w = weights.get(rating, 0.0)

        if rating >= 3:
            new_s = current_s * (1 + ((11 - new_d) / 5) * w)
        else:
            new_s = self.initial_stability

        new_s = max(self.initial_stability, new_s)
        interval = max(1, round(new_s))
        next_date = datetime.now() + timedelta(days=interval)
        
        return new_s, new_d, next_date

    def check_mastery(self, history: List[int]) -> bool:
        """
        判定掌握度：【更新】弹性机制
        逻辑：最近 5 次复习中，没有 1(Again) 或 2(Hard)，且 4(Easy) 的次数 >= 4
        """
        if len(history) < 5:
            return False
            
        recent = history[-5:]
        
        # 1. 确保最近 5 次都没有出现错误或困难 (不能有 1 或 2)
        if any(r <= 2 for r in recent):
            return False
            
        # 2. 统计 Easy (4) 的数量
        easy_count = recent.count(4)
        
        # 3. 如果 Easy 数量达到 4 个或以上，视为掌握
        # 这意味着允许 [4, 4, 3, 4, 4] 这样的组合通过
        return easy_count >= 4