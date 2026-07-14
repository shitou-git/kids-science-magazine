import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AI_API_BASE_URL = "https://api.chatlz.dpdns.org/v1"
AI_API_KEY = os.environ.get("AGENS_AI_API_KEY", "sk-chatlz-proxy")
AI_MODEL = "agnes-2.0-flash"

AI_IMAGE_BASE_URL = "https://image.chatlz.dpdns.org/v1"
AI_IMAGE_MODEL = "agnes-image-2.1-flash"

SCHEDULE_DAY = "friday"
SCHEDULE_TIME = "20:00"

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "archive")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

CATEGORIES = [
    {
        "id": "headline",
        "name": "头版头条",
        "icon": "🌟",
        "keywords": ["重大", "突破", "首次", "发现", "里程碑", "震惊", "重磅"]
    },
    {
        "id": "space",
        "name": "航天宇宙",
        "icon": "🚀",
        "keywords": ["太空", "航天", "火箭", "卫星", "火星", "月球", "行星", "恒星", "黑洞", "宇宙", "星系", "宇航员", "NASA", "神舟", "天宫", "嫦娥", "天问", "空间站", "航天员", "探测器", "登月"]
    },
    {
        "id": "physics",
        "name": "物理世界",
        "icon": "⚛️",
        "keywords": ["物理", "量子", "粒子", "原子", "电子", "能量", "力", "重力", "引力", "电磁", "光", "声音", "速度", "相对论", "牛顿", "爱因斯坦", "超导", "激光", "芯片"]
    },
    {
        "id": "chemistry",
        "name": "化学探秘",
        "icon": "🧪",
        "keywords": ["化学", "元素", "分子", "原子", "反应", "实验", "元素周期表", "材料", "纳米", "催化剂", "合成", "物质", "酸", "碱", "溶液", "晶体"]
    },
    {
        "id": "tech",
        "name": "前沿科技",
        "icon": "🤖",
        "keywords": ["人工智能", "AI", "机器人", "芯片", "5G", "6G", "元宇宙", "VR", "AR", "技术", "发明", "创新", "计算机", "编程", "算法", "3D打印"]
    },
    {
        "id": "life",
        "name": "生命科学",
        "icon": "🧬",
        "keywords": ["基因", "DNA", "细胞", "生物", "医学", "健康", "病毒", "细菌", "进化", "物种", "人体", "大脑", "恐龙", "动物", "植物", "昆虫", "海洋生物"]
    },
    {
        "id": "earth",
        "name": "地球家园",
        "icon": "🌍",
        "keywords": ["环境", "气候", "全球变暖", "环保", "海洋", "地震", "火山", "天气", "极端天气", "生态", "可持续", "地质", "化石", "矿产", "能源"]
    },
    {
        "id": "fun",
        "name": "奇趣发现",
        "icon": "✨",
        "keywords": ["有趣", "神奇", "奇怪", "冷知识", "未解之谜", "新奇", "惊人", "不可思议", "最", "世界", "你知道吗", "秘密"]
    }
]

NEWS_SOURCES = [
    # 综合科普源（优先级最高）
    {
        "name": "科普中国",
        "url": "https://www.kepuchina.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 3
    },
    {
        "name": "科普中国-科技前沿",
        "url": "https://www.kepuchina.cn/kejqy/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    {
        "name": "科普中国-百科探秘",
        "url": "https://www.kepuchina.cn/kpcidian/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 科学网
    {
        "name": "科学网",
        "url": "https://www.sciencenet.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    {
        "name": "科学网-科普",
        "url": "https://news.sciencenet.cn/sciencenews.aspx?id=1",
        "type": "general",
        "encoding": "utf-8",
        "priority": 1
    },
    # 腾讯科普等大平台
    {
        "name": "科学普及出版社",
        "url": "https://www.kepuchina.cn/zongheng/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 1
    },
    {
        "name": "中国数字科技馆",
        "url": "https://www.cdstm.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 1
    },
]

# 少儿不适合内容过滤关键词（标题或内容含这些词则跳过）
INAPPROPRIATE_KEYWORDS = [
    "色情", "暴力", "赌博", "毒品", "自杀",
    "政治敏感", "负面", "灾难", "死亡",
    "股市", "基金", "理财", "投资", "房价",
    "网游", "充值", "会员", "广告", "推广",
    "婚恋", "出轨", "离婚",
    "手术", "癌症", "肿瘤",
]

# 少儿友好内容加分关键词
KID_FRIENDLY_KEYWORDS = [
    "动物", "植物", "恐龙", "宇宙", "星球", "太阳", "月亮", "星星",
    "海洋", "森林", "昆虫", "鸟类", "天气", "彩虹", "火山", "地震",
    "机器人", "太空", "火箭", "卫星", "宇航员", "飞船",
    "实验", "发明", "发现", "探索", "冒险",
    "趣味", "神奇", "奇妙", "为什么", "秘密",
    "大脑", "心脏", "骨骼", "五感", "视觉", "听觉",
    "基因", "DNA", "进化", "物种",
    "环保", "节能", "回收", "绿色",
    "极光", "北极", "南极", "冰川", "沙漠",
    "历史", "古文明", "化石", "考古",
]

# 文章最低少儿友好分（低于此分则跳过）
MIN_KID_FRIENDLY_SCORE = 1

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

ARTICLES_PER_CATEGORY = 1
MAX_ARTICLES_PER_SOURCE = 20
